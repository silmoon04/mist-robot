"""Integrate Cura filament deposition in the supplied print-STL frame.

Linear moves use Marlin G90/G91 and M82/M83 mode semantics. Every G92 is a
coordinate reset, never a physical move. Support and adhesion stay separate.
"""
from __future__ import annotations
import collections
import math
import re
import numpy as np

PARAM = re.compile(r"([A-Z])([-+]?(?:\d+(?:\.\d*)?|\.\d+))")
MODEL_TYPES = {"WALL-INNER", "WALL-OUTER", "SKIN", "FILL", "IRONING", "BRIDGE", "TOP-SKIN", "BOTTOM-SKIN", "WALL-OVERHANG"}
ADHESION_TYPES = {"SKIRT", "BRIM", "RAFT", "PRIME-TOWER", "PRIME-BLOB"}


def category(kind):
    if kind in MODEL_TYPES:
        return "model"
    if kind.startswith("SUPPORT"):
        return "support"
    if kind in ADHESION_TYPES or kind.startswith("RAFT"):
        return "adhesion"
    return "unclassified"


def integrate_segments(segments, gcode_to_source, density_g_cm3=1.24,
                       diameter_mm=1.75, layer_height_mm=.2):
    """Rows contain XYZ start, XYZ end, fresh filament mm and feed mm/s."""
    if not segments:
        return dict(mass_kg=0., mass_g=0., deposited_volume_mm3=0., segment_count=0,
                    com_mm=None, inertia_line_about_com_kg_m2=None,
                    inertia_rectangular_bead_about_com_kg_m2=None,
                    deposited_path_time_without_acceleration_s=0.)
    v = np.asarray(segments, dtype=float)
    p, q = v[:, :3].copy(), v[:, 3:6].copy()
    # G-code Z is the top of a fixed-height layer. The bead centre is midway.
    p[:, 2] -= layer_height_mm / 2
    q[:, 2] -= layer_height_mm / 2
    inverse = np.asarray(gcode_to_source, dtype=float)
    rotation, shift = inverse[:3, :3], inverse[:3, 3]
    p, q = p @ rotation.T + shift, q @ rotation.T + shift
    delta, midpoint = q-p, (p+q)/2
    lengths = np.linalg.norm(delta, axis=1)
    volume = v[:, 6] * math.pi * (diameter_mm/2)**2
    mass = volume * density_g_cm3 * 1e-6
    total_mass = float(mass.sum())
    com = (mass[:, None]*midpoint).sum(axis=0)/total_mass
    centred = midpoint-com
    # Exact second central moment of a uniform line segment, then inertia.
    second = np.einsum("n,ni,nj->ij", mass, centred, centred)
    second += np.einsum("n,ni,nj->ij", mass/12, delta, delta)
    inertia = (np.eye(3)*np.trace(second)-second)*1e-6
    # Optional finite-section model uses a rectangular bead with the recorded
    # layer height and area inferred from filament volume per path length.
    # This is a sensitivity estimate, not a reconstructed physical cross-section.
    effective_width = volume / (lengths*layer_height_mm)
    tangents = delta/lengths[:, None]
    build_normal = rotation @ np.array([0., 0., 1.])
    side = np.cross(np.broadcast_to(build_normal, tangents.shape), tangents)
    side_norm = np.linalg.norm(side, axis=1)
    if np.any(side_norm < .999):
        raise ValueError("Extruding moves are not horizontal in the fixed-layer profile")
    side /= side_norm[:, None]
    section_second = np.einsum("n,ni,nj->ij", mass*effective_width**2/12, side, side)
    section_second += total_mass*layer_height_mm**2/12*np.outer(build_normal, build_normal)
    correction = (np.eye(3)*np.trace(section_second)-section_second)*1e-6
    time = np.divide(lengths, v[:, 7], out=np.zeros_like(lengths), where=v[:, 7] > 0)
    eig = np.linalg.eigvalsh(inertia)
    if eig.min() < -1e-12:
        raise ValueError("Integrated inertia is not positive semidefinite")
    max_relative_section = float(np.linalg.norm(correction, ord=2)/max(np.linalg.norm(inertia, ord=2), 1e-15))
    return dict(mass_kg=total_mass, mass_g=total_mass*1000,
                deposited_volume_mm3=float(volume.sum()), segment_count=len(v),
                com_mm=com.tolist(), inertia_line_about_com_kg_m2=inertia.tolist(),
                inertia_rectangular_bead_about_com_kg_m2=(inertia+correction).tolist(),
                rectangular_section_correction_kg_m2=correction.tolist(),
                rectangular_section_spectral_fraction=max_relative_section,
                line_inertia_eigenvalues_kg_m2=eig.tolist(),
                inferred_rectangular_bead_width_mm={"min":float(effective_width.min()),
                    "median":float(np.median(effective_width)), "p99":float(np.percentile(effective_width, 99)),
                    "max":float(effective_width.max())},
                deposited_centreline_bounds_mm=[np.minimum(p.min(axis=0), q.min(axis=0)).tolist(),
                                                np.maximum(p.max(axis=0), q.max(axis=0)).tolist()],
                deposited_path_time_without_acceleration_s=float(time.sum()),
                peak_nominal_deposition_flow_mm3_s=float(np.max(np.divide(volume, time, out=np.zeros_like(volume), where=time>0))))


def parse_gcode(text, gcode_to_source=None, density_g_cm3=1.24, diameter_mm=1.75, layer_height_mm=.2):
    if gcode_to_source is None:
        gcode_to_source = np.eye(4)
    transform = np.asarray(gcode_to_source, dtype=float)
    if (transform.shape != (4, 4) or not np.isfinite(transform).all()
            or not np.allclose(transform[3], [0, 0, 0, 1], atol=1e-12)
            or not np.allclose(transform[:3,:3]@transform[:3,:3].T, np.eye(3), atol=1e-8)
            or not math.isclose(float(np.linalg.det(transform[:3,:3])), 1., abs_tol=1e-8)):
        raise ValueError("The G-code to STL transform must be rigid")
    xyz = [0., 0., 0.]
    logical_xyz = [0., 0., 0.]
    offset = [0., 0., 0.]
    absolute_xyz = absolute_e = True
    e, retract_debt, feed, kind = 0., 0., 0., "UNCLASSIFIED"
    by_type = collections.defaultdict(list)
    nondeposition_prime, repayment, retract_total = 0., 0., 0.
    deposited_e = 0.
    declared_time = None
    layers = set()
    flow_override = 1.
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(";TYPE:"):
            kind = stripped[6:].strip()
        if stripped.startswith(";TIME_ELAPSED:"):
            declared_time = float(stripped.partition(":")[2])
        if stripped.startswith(";LAYER:"):
            layers.add(int(stripped.partition(":")[2]))
        cmd = stripped.split(";", 1)[0].strip()
        if not cmd:
            continue
        cmd = re.sub(r"^N\d+\s*", "", cmd).split("*", 1)[0].strip()
        op_match = re.match(r"([GMT])([0-9]+(?:\.[0-9]+)?)", cmd)
        if not op_match:
            continue
        op = op_match.group(1)+op_match.group(2)
        values = {k:float(v) for k,v in PARAM.findall(cmd[op_match.end():])}
        if op == "G90":
            absolute_xyz = absolute_e = True
            continue
        if op == "G91":
            absolute_xyz = absolute_e = False
            continue
        if op == "M82":
            absolute_e = True
            continue
        if op == "M83":
            absolute_e = False
            continue
        if op == "G92":
            if "E" in values:
                e = values["E"]
            for i, axis in enumerate("XYZ"):
                if axis in values:
                    logical_xyz[i] = values[axis]
                    offset[i] = xyz[i]-logical_xyz[i]
            continue
        if op in ("G20", "G92.1", "G53", "G54", "G55", "G56", "G57", "G58", "G59", "G10", "G11"):
            raise ValueError(f"Unsupported coordinate or extrusion command {op} on line {line_number}")
        if op == "M200" and values.get("D", 0) != 0:
            raise ValueError("Volumetric E mode needs a different material conversion")
        if op == "M221":
            flow_override = values.get("S",100)/100
            if abs(flow_override-1)>1e-8:
                raise ValueError("Non-100 percent firmware flow would invalidate emitted E accounting")
        if op.startswith("T") and op != "T0":
            raise ValueError("The pipeline supports the single-extruder profile only")
        if op in ("G2", "G3", "G5"):
            raise ValueError(f"Nonlinear extrusion requires an arc integrator on line {line_number}")
        if op not in ("G0", "G1"):
            continue
        if "F" in values:
            feed = values["F"]/60
        new_logical = logical_xyz.copy()
        for i, axis in enumerate("XYZ"):
            if axis in values:
                new_logical[i] = values[axis] if absolute_xyz else new_logical[i]+values[axis]
        target = [new_logical[i]+offset[i] for i in range(3)]
        delta_e = 0.
        if "E" in values:
            new_e = values["E"] if absolute_e else e+values["E"]
            delta_e, e = new_e-e, new_e
        fresh = 0.
        fraction_repaid = 0.
        if delta_e < 0:
            retract_debt -= delta_e
            retract_total -= delta_e
        elif delta_e > 0:
            repaid = min(retract_debt, delta_e)
            retract_debt -= repaid
            repayment += repaid
            fresh = delta_e-repaid
            fraction_repaid = repaid/delta_e
        distance = math.dist(xyz, target)
        if fresh > 1e-10 and distance > 1e-7:
            if abs(target[2]-xyz[2]) > 1e-6:
                raise ValueError(f"Extruding Z motion outside fixed-layer assumptions on line {line_number}")
            # If recovery occurs during a move, only the tail deposits fresh
            # material under the simple no-pressure-storage model.
            start = [xyz[i]+fraction_repaid*(target[i]-xyz[i]) for i in range(3)]
            by_type[kind].append((*start, *target, fresh, feed))
            deposited_e += fresh
        elif fresh > 1e-10:
            nondeposition_prime += fresh
        xyz, logical_xyz = target, new_logical
    grouped = collections.defaultdict(list)
    feature_totals = {}
    for feature, segments in by_type.items():
        grouped[category(feature)].extend(segments)
        volume = sum(s[6] for s in segments)*math.pi*(diameter_mm/2)**2
        feature_totals[feature] = dict(category=category(feature), deposited_volume_mm3=volume,
                                      mass_g=volume*density_g_cm3/1000, segment_count=len(segments))
    properties = {group:integrate_segments(grouped[group], transform, density_g_cm3, diameter_mm, layer_height_mm)
                  for group in ("model", "support", "adhesion", "unclassified")}
    return dict(coordinate_frame="Exact supplied print STL coordinates in millimetres",
                density_g_cm3=density_g_cm3, filament_diameter_mm=diameter_mm,
                layer_height_mm=layer_height_mm, gcode_to_source_transform=transform.tolist(),
                properties=properties, features=feature_totals,
                total_deposited_volume_mm3=sum(p["deposited_volume_mm3"] for p in properties.values()),
                total_deposited_mass_g=sum(p["mass_g"] for p in properties.values()),
                estimated_total_print_time_s=declared_time, layer_count=len(layers),
                extrusion_accounting=dict(fresh_deposited_filament_mm=deposited_e,
                    retracted_filament_mm=retract_total, repaid_retraction_filament_mm=repayment,
                    outstanding_retraction_filament_mm=retract_debt,
                    nonmoving_fresh_prime_filament_mm=nondeposition_prime),
                unclassified_deposition_is_zero=properties["unclassified"]["mass_kg"]==0,
                limitations=["Filament E is commanded material; actual extrusion, density and shrinkage need a scale and coupons.",
                    "The primary inertia integrates uniform deposited line segments at the middle of each layer.",
                    "The optional rectangular section correction estimates sensitivity to finite bead width; it does not reconstruct pressure, corner overlap or real cross-sections.",
                    "Retraction recovery is excluded. A moving recovery deposits fresh material only along the remaining tail under a simple no-pressure-storage model.",
                    "Per-category path times omit acceleration, travel, cooling and other delays. Only Cura total time estimates the complete slice.",
                    "Support and adhesion mass are excluded from robot-part mass, COM and inertia.",
                    "These deposition properties do not establish strength or replace the full-solid comparison scenario."])
