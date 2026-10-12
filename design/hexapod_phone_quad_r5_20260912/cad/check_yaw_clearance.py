"""Measure the production coxa clearance at four discrete yaw positions."""
from __future__ import annotations

import math

import numpy as np
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

import build
import geom


ANGLES_DEG = (-25.0, -22.0, 22.0, 25.0)
INTERSECTION_THRESHOLD_MM3 = 0.01
GAP_WARNING_MM = 0.5
OPERATING_GAP_WARNING_MM = 1.0
MOVING_NAME = "FL_coxa_upper_and_hip_saddle"
FIXED_NAMES = ("FL_yaw_case_saddle", "FL_case_cap_yaw")


def _point_xyz(point):
    return [float(point.X()), float(point.Y()), float(point.Z())]


def run_yaw_clearance(cfg, parts, initial_poses) -> dict:
    """Return exact BRep distances and common volumes for the FL interface.

    Base parts already contain their mounting transformation. Only the coxa
    receives the mounting pose followed by the requested local yaw rotation.
    The supplied assembly and poses are left unchanged.
    """
    named = {part["name"]: part for part in parts}
    moving = named[MOVING_NAME]
    fixed = [named[name] for name in FIXED_NAMES]
    if moving["link"] != "coxa_FL" or any(p["link"] != "base" for p in fixed):
        raise ValueError("Yaw clearance expects the production coxa and base links")

    azimuth = float(cfg["leg_azimuth_deg"]["FL"])
    angle = math.radians(azimuth)
    mount = build.pose(
        [cfg["yaw_radius_mm"] * math.cos(angle),
         cfg["yaw_radius_mm"] * math.sin(angle), cfg["yaw_height_mm"]],
        [0, 0, azimuth],
    )
    if not np.allclose(initial_poses["coxa_FL"], mount, rtol=0, atol=1e-8):
        raise ValueError("Initial coxa pose must be the configured neutral mounting pose")
    base_pose = np.asarray(initial_poses["base"], dtype=float)
    if not np.allclose(base_pose, np.eye(4), rtol=0, atol=1e-8):
        raise ValueError("Yaw clearance expects assembly coordinates with an identity base pose")
    fixed_shapes = [build.shape_at(p["shape"], base_pose) for p in fixed]

    samples = []
    failures = []
    warnings = []
    minimum = None
    for yaw in ANGLES_DEG:
        coxa_pose = mount @ build.pose(rpy=[0, 0, yaw])
        moving_shape = build.shape_at(moving["shape"], coxa_pose)
        pairs = []
        for stationary, stationary_shape in zip(fixed, fixed_shapes):
            distance = BRepExtrema_DistShapeShape(moving_shape, stationary_shape)
            distance.Perform()
            if not distance.IsDone() or distance.NbSolution() < 1:
                raise RuntimeError(f"Distance computation failed for yaw {yaw}: {stationary['name']}")
            gap = float(distance.Value())
            if not math.isfinite(gap) or gap < 0:
                raise RuntimeError("Distance computation returned an invalid gap")
            volume = float(geom.common_volume(moving_shape, stationary_shape))
            hit = volume > INTERSECTION_THRESHOLD_MM3
            pair = dict(
                yaw_deg=yaw, a=MOVING_NAME, b=stationary["name"],
                link_a="coxa_FL", link_b="base", distance_mm=gap,
                intersection_mm3=volume,
                closest_point_a_mm=_point_xyz(distance.PointOnShape1(1)),
                closest_point_b_mm=_point_xyz(distance.PointOnShape2(1)),
                closest_solution_count=int(distance.NbSolution()),
                collision=hit,
            )
            pairs.append(pair)
            if minimum is None or gap < minimum["distance_mm"]:
                minimum = dict(pair)
            if hit:
                failures.append(dict(pair, reason="Common volume exceeds 0.01 mm3"))
            if gap < GAP_WARNING_MM:
                warnings.append(dict(pair, reason="Nominal gap is below 0.5 mm; verify printed clearance"))
        samples.append(dict(
            yaw_deg=yaw, coxa_FL_to_base_matrix_mm=coxa_pose.tolist(),
            distance_pair_count=len(pairs), common_volume_pair_count=len(pairs), pairs=pairs,
        ))

    return dict(
        status="fail" if failures else "pass",
        passed=not failures,
        scope="Production coxa upper assembly versus its stationary yaw saddle and cap",
        representative_leg="FL",
        equivalent_interfaces=["FL", "FR", "RL", "RR"],
        equivalence_basis=("All four interfaces instantiate the same production leg shapes. "
                           "Each moving and fixed pair differs only by one shared rigid mounting "
                           "transform, which preserves distance and intersection volume."),
        angles_deg=list(ANGLES_DEG), sample_count=len(samples),
        distance_pair_count=sum(s["distance_pair_count"] for s in samples),
        common_volume_pair_count=sum(s["common_volume_pair_count"] for s in samples),
        units=dict(distance="mm", closest_points="assembly mm", intersection="mm3"),
        initial_coxa_FL_to_base_matrix_mm=mount.tolist(),
        fixed_base_pose_matrix_mm=base_pose.tolist(),
        stationary_shape_coordinates="Already transformed to the assembly base frame by load_assembly",
        intersection_failure_threshold_mm3=INTERSECTION_THRESHOLD_MM3,
        gap_warning_threshold_mm=GAP_WARNING_MM,
        minimum_gap_mm=minimum["distance_mm"], minimum_pair=minimum,
        failures=failures, warnings=warnings, samples=samples,
        limitations=[
            "Only the four listed yaw positions and two listed stationary parts are checked.",
            "The result does not establish continuous motion clearance.",
            "Fastener heads, flexible cables, manufacturing tolerances and loaded deflection are excluded.",
            "A gap below 0.5 mm is a warning and does not by itself count as a collision.",
        ],
    )


def run_operating_yaw_clearance(cfg, parts, initial_poses) -> dict:
    """Check each production coxa against its clamp and the actual body deck.

    The deck is checked at every corner because its outline does not share
    the rotational symmetry of the four identical leg mounting interfaces.
    """
    limit = float(cfg["yaw_operating_limit_deg"])
    if not math.isfinite(limit) or not 0 < limit < 180:
        raise ValueError("Operating yaw limit must be finite and between 0 and 180 degrees")
    named = {part["name"]: part for part in parts}
    base_pose = np.asarray(initial_poses["base"], dtype=float)
    if not np.allclose(base_pose, np.eye(4), rtol=0, atol=1e-8):
        raise ValueError("Operating yaw clearance expects an identity base pose")
    if named["body_deck"]["link"] != "base":
        raise ValueError("Operating yaw clearance expects the deck on the base link")

    pairs = []
    samples = []
    failures = []
    warnings = []
    for label in ("FL", "FR", "RL", "RR"):
        link = "coxa_" + label
        moving = named[label + "_coxa_upper_and_hip_saddle"]
        fixed = [named[name] for name in (
            "body_deck", label + "_yaw_case_saddle", label + "_case_cap_yaw")]
        if moving["link"] != link or any(p["link"] != "base" for p in fixed):
            raise ValueError("Operating yaw clearance expects production coxa and base links")
        azimuth = float(cfg["leg_azimuth_deg"][label])
        angle = math.radians(azimuth)
        mount = build.pose(
            [cfg["yaw_radius_mm"] * math.cos(angle),
             cfg["yaw_radius_mm"] * math.sin(angle), cfg["yaw_height_mm"]],
            [0, 0, azimuth],
        )
        if not np.allclose(initial_poses[link], mount, rtol=0, atol=1e-8):
            raise ValueError(f"Initial {link} pose must be the configured neutral mounting pose")
        fixed_shapes = [build.shape_at(p["shape"], base_pose) for p in fixed]
        for yaw in (-limit, limit):
            coxa_pose = mount @ build.pose(rpy=[0, 0, yaw])
            moving_shape = build.shape_at(moving["shape"], coxa_pose)
            indices = []
            for stationary, stationary_shape in zip(fixed, fixed_shapes):
                distance = BRepExtrema_DistShapeShape(moving_shape, stationary_shape)
                distance.Perform()
                if not distance.IsDone() or distance.NbSolution() < 1:
                    raise RuntimeError(f"Distance computation failed for {link} yaw {yaw}: {stationary['name']}")
                gap = float(distance.Value())
                volume = float(geom.common_volume(moving_shape, stationary_shape))
                if not math.isfinite(gap) or gap < 0 or not math.isfinite(volume):
                    raise RuntimeError("Operating yaw check returned an invalid distance or volume")
                collision = volume > INTERSECTION_THRESHOLD_MM3
                pair = dict(
                    leg=label, yaw_deg=yaw, a=moving["name"], b=stationary["name"],
                    link_a=link, link_b="base", distance_mm=gap, intersection_mm3=volume,
                    closest_point_a_mm=_point_xyz(distance.PointOnShape1(1)),
                    closest_point_b_mm=_point_xyz(distance.PointOnShape2(1)),
                    closest_solution_count=int(distance.NbSolution()), collision=collision,
                )
                indices.append(len(pairs))
                pairs.append(pair)
                if collision:
                    failures.append(dict(pair, reason="Common volume exceeds 0.01 mm3"))
                if gap < OPERATING_GAP_WARNING_MM:
                    warnings.append(dict(pair, reason="Nominal operating gap is below 1 mm"))
            samples.append(dict(
                leg=label, yaw_deg=yaw, moving_link=link,
                link_to_base_matrix_mm=coxa_pose.tolist(), pair_indices=indices,
                distance_pair_count=len(indices), common_volume_pair_count=len(indices),
            ))

    minimum = min(pairs, key=lambda pair: pair["distance_mm"])
    return dict(
        status="fail" if failures else "pass", passed=not failures,
        scope="All four coxa upper assemblies at both configured operating yaw limits",
        operating_yaw_limit_deg=limit, angles_deg=[-limit, limit],
        checked_legs=["FL", "FR", "RL", "RR"],
        stationary_scope="Actual body deck and the moving leg's own stationary yaw saddle and cap",
        sample_count=len(samples), distance_pair_count=len(pairs), common_volume_pair_count=len(pairs),
        fixed_base_pose_matrix_mm=base_pose.tolist(),
        stationary_shape_coordinates="Already in the assembly base frame; no repeated leg mount transform",
        units=dict(distance="mm", closest_points="assembly mm", intersection="mm3"),
        intersection_failure_threshold_mm3=INTERSECTION_THRESHOLD_MM3,
        gap_warning_threshold_mm=OPERATING_GAP_WARNING_MM,
        minimum_gap_mm=minimum["distance_mm"], minimum_pair=dict(minimum),
        pairs=pairs, samples=samples, failures=failures, clearance_warnings=warnings,
        limitations=[
            "Only the two operating limit positions are checked for each leg.",
            "The result does not establish continuous motion clearance.",
            "Fastener heads, cables, manufacturing tolerances and loaded deflection are excluded.",
            "A gap below 1 mm raises a clearance warning without automatically failing collision status.",
        ],
    )


if __name__ == "__main__":
    config, assembly_parts, assembly_poses, _ = build.load_assembly()
    report = run_yaw_clearance(config, assembly_parts, assembly_poses)
    for sample in report["samples"]:
        for pair in sample["pairs"]:
            print(f"yaw={sample['yaw_deg']:+.0f} {pair['b']} "
                  f"gap={pair['distance_mm']:.9f} mm "
                  f"common={pair['intersection_mm3']:.9f} mm3", flush=True)
            print("  closest points", pair["closest_point_a_mm"], pair["closest_point_b_mm"], flush=True)
    print(f"{report['status'].upper()}: {report['distance_pair_count']} distance pairs, "
          f"minimum gap {report['minimum_gap_mm']:.9f} mm, "
          f"{len(report['failures'])} collisions, {len(report['warnings'])} warnings", flush=True)
    operating_report = run_operating_yaw_clearance(config, assembly_parts, assembly_poses)
    for pair in operating_report["pairs"]:
        print(f"operating {pair['leg']} yaw={pair['yaw_deg']:+.0f} {pair['b']} "
              f"gap={pair['distance_mm']:.9f} mm common={pair['intersection_mm3']:.9f} mm3",
              flush=True)
    print(f"Operating {operating_report['status'].upper()}: "
          f"{operating_report['distance_pair_count']} distance pairs, "
          f"minimum gap {operating_report['minimum_gap_mm']:.9f} mm, "
          f"{len(operating_report['failures'])} collisions, "
          f"{len(operating_report['clearance_warnings'])} warnings", flush=True)
    raise SystemExit(0 if report["passed"] and operating_report["passed"] else 1)
