"""Distributed analytical hardware mass estimate for the landscape quadruped.

No CAD is changed. Local positions follow the R5 interfaces, with M3x35 case
clamps and external bridge nuts on full-thickness cheeks. The output
is a mass estimate, not a fastener fit or strength certificate.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import importlib.util
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
RHO_G_MM3 = 0.00785
MODES = ("low", "nominal", "high")


def interface_constants():
    """Read the canonical servo module and numeric leg contract without OCP."""
    path = ROOT / "cad" / "servo_contract.py"
    spec = importlib.util.spec_from_file_location("quad_mass_servo_contract", path)
    servo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(servo)
    tree = ast.parse((ROOT / "cad" / "leg.py").read_text(encoding="utf-8-sig"))
    value = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "CONSTANTS" for t in node.targets))

    class ServoNumbers(ast.NodeTransformer):
        def visit_Attribute(self, node):
            if isinstance(node.value, ast.Name) and node.value.id == "sc":
                number = getattr(servo, node.attr)
                if isinstance(number, (int, float)):
                    return ast.copy_location(ast.Constant(number), node)
            raise ValueError("The leg mass contract contains a nonnumeric attribute")

    return servo, ast.literal_eval(ServoNumbers().visit(value))


def rot(axis, degrees):
    x, y, z = np.asarray(axis, float)
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    cross = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    a = np.array([x, y, z])
    return np.eye(3) * c + (1-c) * np.outer(a, a) + s * cross


def tensor_dict(t):
    return {k: float(t[i, j]) for k, i, j in
            (("ixx", 0, 0), ("iyy", 1, 1), ("izz", 2, 2),
             ("ixy", 0, 1), ("ixz", 0, 2), ("iyz", 1, 2))}


def cylinder_inertia(mass_kg, radius_mm, length_mm, axis):
    axial = mass_kg * (radius_mm * .001)**2 / 2
    cross = mass_kg * ((radius_mm * .001)**2 / 4 + (length_mm * .001)**2 / 12)
    return cross * np.eye(3) + (axial-cross) * np.outer(axis, axis)


def combine(entries):
    mass = sum(e[0] for e in entries)
    center = sum(m*p for m, p, _ in entries) / mass
    inertia = np.zeros((3, 3))
    for m, p, t in entries:
        d = (p-center) * .001
        inertia += t + m * (np.dot(d, d)*np.eye(3) - np.outer(d, d))
    return mass, center, inertia


def hardware_properties(kind, length, outer, position, axis, mode):
    """Screw position is its under-head bearing plane; other positions are COM."""
    idx = MODES.index(mode)
    position, axis = np.asarray(position, float), np.asarray(axis, float)
    if kind in ("screw", "supplied_main_retainer", "supplied_aux_retainer"):
        effective_d = (2.60, 2.75, 3.0)[idx]
        if kind == "supplied_aux_retainer":
            effective_d = (2.30, 2.60, 3.0)[idx]
        head_d, head_h = ((5.6, 2.4), (5.5, 3.0), (5.5, 3.0))[idx]
        full_head = math.pi * head_d**2 / 4 * head_h
        # Low rounded pan head and drive recess are explicit assumptions.
        # Nominal socket uses the Accu dimensions, with 5% chamfer allowance.
        socket = math.sqrt(3) / 2 * 2.5**2 * 1.3
        head_v = ((full_head*.75 - 4), (full_head-socket)*.95, full_head)[idx]
        shaft_m = math.pi * effective_d**2 / 4 * length * RHO_G_MM3 / 1000
        head_m = head_v * RHO_G_MM3 / 1000
        shaft_p = position + axis * length / 2
        head_p = position - axis * head_h / 2
        return combine([(shaft_m, shaft_p, cylinder_inertia(shaft_m, effective_d/2, length, axis)),
                        (head_m, head_p, cylinder_inertia(head_m, head_d/2, head_h, axis))])
    if kind == "nut":
        bore = (3.0, 2.75, 2.5)[idx]
        v = (math.sqrt(3)/2*5.5**2 - math.pi*bore**2/4) * 2.4
        mass = v * (.90, .95, 1.0)[idx] * RHO_G_MM3 / 1000
        # Equal-area annular-cylinder approximation of the hexagon.
        radius = math.sqrt(math.sqrt(3)/2*5.5**2/math.pi)*.001
        inner = bore/2*.001
        axial = mass*(radius**2+inner**2)/2
        cross = mass*((radius**2+inner**2)/4 + .0024**2/12)
        inertia = cross*np.eye(3)+(axial-cross)*np.outer(axis, axis)
        return mass, position, inertia
    if kind == "washer":
        mass = math.pi*(outer**2-3.2**2)/4 * length * RHO_G_MM3 / 1000
        mass *= (.9, 1, 1.1)[idx]
        inner, radius = 1.6*.001, outer/2*.001
        axial = mass * (radius**2+inner**2) / 2
        cross = mass * ((radius**2+inner**2)/4 + (length*.001)**2/12)
        inertia = cross*np.eye(3)+(axial-cross)*np.outer(axis, axis)
        return mass, position, inertia
    raise ValueError(kind)


def build_fasteners(cfg=None):
    """Return every hardware piece with masses and local tensors for each mode."""
    cfg = cfg or json.loads((ROOT / "settings.json").read_text())
    servo_contract, leg = interface_constants()
    records = []

    def piece(group, link, kind, length, position, axis, outer=None, transform=None):
        p, a = np.asarray(position, float), np.asarray(axis, float)
        if transform is not None:
            r, o = transform
            p, a = r@p+o, r@a
        if kind == "washer":
            sku = f"washer_M3_OD{outer:g}_ID3.2_T{length:g}"
        elif kind == "nut":
            sku = "plain_nut_M3_AF5.5_T2.4"
        else:
            sku = ("PA3" if kind == "supplied_aux_retainer" else "M3") + f"x{length:g}"
        values = {}
        for mode in MODES:
            m, c, t = hardware_properties(kind, length, outer, p, a, mode)
            values[mode] = {"mass_kg": float(m), "com_mm": c.tolist(),
                            "inertia_kg_m2": tensor_dict(t)}
        records.append({"id": f"hardware_{len(records)+1:03}", "group": group,
                        "link": link, "category": kind, "sku": sku,
                        "supplied": kind.startswith("supplied_"),
                        "length_mm": length, "outer_diameter_mm": outer,
                        "axis_local": a.tolist(), "position_local_mm": p.tolist(),
                        "estimates": values})

    def screw(group, link, length, bearing, axis, **kw):
        piece(group, link, "screw", length, bearing, axis, **kw)

    def washer(group, link, center, axis, outer=7, thickness=.5, **kw):
        piece(group, link, "washer", thickness, center, axis, outer, **kw)

    def nut(group, link, center, axis, **kw):
        piece(group, link, "nut", 2.4, center, axis, **kw)

    def clamp(group, link, transform=None, bolt_xz=None):
        for x, z in servo_contract.CLAMP_BOLT_XZ if bolt_xz is None else bolt_xz:
            screw(group, link, 35, (x, 16.865, z), (0, -1, 0), transform=transform)
            washer(group, link, (x, 16.615, z), (0, 1, 0), transform=transform)
            nut(group, link, (x, -14.9, z), (0, 1, 0), transform=transform)

    pitch_in = rot((1, 0, 0), -90)
    yaw_aux_floor = leg["yaw_lower_plate_z"][0] + leg["yaw_auxiliary_counterbore_depth"]
    for label, azimuth in cfg["leg_azimuth_deg"].items():
        a = math.radians(azimuth)
        mount = (rot((0, 0, 1), azimuth), np.array([
            cfg["yaw_radius_mm"]*math.cos(a), cfg["yaw_radius_mm"]*math.sin(a), cfg["yaw_height_mm"]]))
        coxa, femur, tibia = (f"{s}_{label}" for s in ("coxa", "femur", "tibia"))
        clamp(f"{label}_yaw_clamp", "base", mount)
        clamp(f"{label}_hip_clamp", coxa, (pitch_in, np.array([cfg["coxa_mm"], 14.5, 0])),
              bolt_xz=leg["hip_clamp_bolt_xz"])
        clamp(f"{label}_knee_clamp", femur, (pitch_in, np.array([cfg["femur_mm"], 14.5, 0])))
        for x in (-29, 9):
            for y in (-20, 20):
                group = f"{label}_yaw_deck"
                screw(group, "base", 12, (x, y, -28.5), (0, 0, -1), transform=mount)
                washer(group, "base", (x, y, -28.75), (0, 0, 1), transform=mount)
                nut(group, "base", (x, y, -37.2), (0, 0, 1), transform=mount)
        for x, y in ((7, 0), (-7, 0), (0, 7), (0, -7)):
            screw(f"{label}_yaw_main_horn", coxa, 6, (x, y, 9), (0, 0, -1))
            washer(f"{label}_yaw_main_horn", coxa, (x, y, 8.75), (0, 0, 1), 6)
            screw(f"{label}_yaw_aux_horn", coxa, 20, (x, y, yaw_aux_floor-1), (0, 0, 1))
            for z in (yaw_aux_floor-.25, yaw_aux_floor-.75):
                washer(f"{label}_yaw_aux_horn", coxa, (x, y, z), (0, 0, 1), 6)
        for (x, y), nut_z_range in zip(leg["coxa_post_holes_xy"], leg["coxa_post_nut_z_ranges"], strict=True):
            group = f"{label}_coxa_bridge"
            screw(group, coxa, 20, (x, y, leg["yaw_lower_plate_z"][0]-.5), (0, 0, 1))
            washer(group, coxa, (x, y, leg["yaw_lower_plate_z"][0]-.25), (0, 0, 1))
            nut(group, coxa, (x, y, nut_z_range[0]+1.2), (0, 0, 1))
        for link, joint in ((femur, "hip"), (tibia, "knee")):
            for y, direction in ((23, -1), (-23, 1)):
                for x, z in ((7, 0), (-7, 0), (0, 7), (0, -7)):
                    group = f"{label}_{joint}_{'main' if y>0 else 'aux'}_horn"
                    screw_length, washer_count = (6, 1) if y > 0 else (8, 2)
                    screw(group, link, screw_length, (x, y-direction*.5*washer_count, z), (0, direction, 0))
                    for washer_index in range(washer_count):
                        washer(group, link, (x, y-direction*(.25+.5*washer_index), z), (0, 1, 0), 6)
            points = leg["femur_bridge_bolt_xz"] if link == femur else leg["tibia_bridge_bolt_xz"]
            for x, z in points:
                group = f"{label}_{joint}_bridge_external_nut"
                screw(group, link, 50, (x, -23.5, z), (0, 1, 0))
                washer(group, link, (x, -23.25, z), (0, 1, 0), 7)
                washer(group, link, (x, 23.25, z), (0, 1, 0), 7)
                nut(group, link, (x, 24.7, z), (0, 1, 0))
        piece(f"{label}_yaw_main_center", coxa, "supplied_main_retainer", 6, (0, 0, 4.5), (0, 0, -1))
        piece(f"{label}_yaw_aux_center", "base", "supplied_aux_retainer", 5,
              (0, 0, servo_contract.AUX_STUB_TIP_Z-.5), (0, 0, 1), transform=mount)
        washer(f"{label}_yaw_aux_center", "base", (0, 0, servo_contract.AUX_STUB_TIP_Z-.25),
               (0, 0, 1), 7, transform=mount)
        for owner, child, origin, joint in ((coxa, femur, cfg["coxa_mm"], "hip"),
                                            (femur, tibia, cfg["femur_mm"], "knee")):
            piece(f"{label}_{joint}_main_center", child, "supplied_main_retainer", 6, (0, 19, 0), (0, -1, 0))
            aux_stub_y = leg["pitch_main_face_y"]+servo_contract.AUX_STUB_TIP_Z
            piece(f"{label}_{joint}_aux_center", owner, "supplied_aux_retainer", 5,
                  (origin, aux_stub_y-.5, 0), (0, 1, 0))
            washer(f"{label}_{joint}_aux_center", owner, (origin, aux_stub_y-.25, 0), (0, 1, 0), 7)

    for x, y in ((78, 0), (-78, 0), (0, 90), (0, -90)):
        screw("body_cover", "base", 10, (x, y, -.5), (0, 0, 1))
        washer("body_cover", "base", (x, y, -.25), (0, 0, 1))
        nut("body_cover", "base", (x, y, 8.2), (0, 0, 1))
    for x in (-43, 43):
        for y in (-27, 27):
            screw("battery_tray", "base", 10, (x, y, 4.5), (0, 0, -1))
            washer("battery_tray", "base", (x, y, 4.25), (0, 0, 1))
            nut("battery_tray", "base", (x, y, -2.8), (0, 0, 1))
    for x, y in ((-39, -20), (-39, 20), (19, -20), (19, 20)):
        screw("pan_to_cover", "base", 16, (x, y, 70.5), (0, 0, -1))
        washer("pan_to_cover", "base", (x, y, 70.25), (0, 0, 1))
        nut("pan_to_cover", "base", (x, y, 58.2), (0, 0, 1))
    for x in (-25, 5):
        for y in (-19, 19):
            screw("pan_cap", "base", 10, (x, y, 90.8), (0, 0, -1))
            nut("pan_cap", "base", (x, y, 82.25), (0, 0, 1))
    for x, y in ((7, 0), (-7, 0), (0, 7), (0, -7)):
        screw("phone_hub_horn", "phone_pan", 6, (x, y, 8.5), (0, 0, -1))
        washer("phone_hub_horn", "phone_pan", (x, y, 8.25), (0, 0, 1), 6)
    piece("phone_main_center", "phone_pan", "supplied_main_retainer", 6, (0, 0, 4.5), (0, 0, -1))
    for x in (-16, 12):
        for y in (-24, 24):
            screw("phone_feet_hub", "phone_pan", 10, (x, y, 13.5), (0, 0, -1))
            nut("phone_feet_hub", "phone_pan", (x, y, 5.7), (0, 0, 1))
    for y in (-24, 24):
        for z in (24, 34):
            screw("phone_feet_frame", "phone_pan", 10, (-10.5, y, z), (1, 0, 0))
            nut("phone_feet_frame", "phone_pan", (-1.7, y, z), (1, 0, 0))
    for y in (-78.25, 78.25):
        for z in (25.5, 92.5):
            screw("phone_retention", "phone_pan", 16, (11, y, z), (-1, 0, 0))
            nut("phone_retention", "phone_pan", (-3.2, y, z), (1, 0, 0))
    return records


def export():
    records = build_fasteners()
    links = defaultdict(dict)
    for link in sorted({r["link"] for r in records}):
        for mode in MODES:
            entries = []
            for r in records:
                if r["link"] != link:
                    continue
                p = r["estimates"][mode]
                t = p["inertia_kg_m2"]
                matrix = np.array([[t["ixx"], t["ixy"], t["ixz"]],
                                   [t["ixy"], t["iyy"], t["iyz"]],
                                   [t["ixz"], t["iyz"], t["izz"]]])
                entries.append((p["mass_kg"], np.array(p["com_mm"]), matrix))
            mass, center, inertia = combine(entries)
            if np.linalg.eigvalsh(inertia).min() <= 0:
                raise ValueError(f"Invalid hardware inertia for {link}")
            links[link][mode] = {"mass_kg": mass, "com_mm": center.tolist(),
                                  "inertia_kg_m2": tensor_dict(inertia)}
    counts = Counter(r["category"] for r in records)
    expected = {"screw": 200, "nut": 100, "washer": 256,
                "supplied_main_retainer": 13, "supplied_aux_retainer": 12}
    if counts != expected:
        raise ValueError(f"Count audit differs from independent BOM: {counts}")
    by_category = {}
    for category, count in counts.items():
        by_category[category] = {"count": count, "mass_g": {
            mode: 1000*sum(r["estimates"][mode]["mass_kg"] for r in records if r["category"] == category)
            for mode in MODES}}
    mass_g = {mode: 1000*sum(r["estimates"][mode]["mass_kg"] for r in records) for mode in MODES}
    sources = ["settings.json", "cad/servo_contract.py", "cad/leg.py", "cad/phone.py", "cad/body.py", "printing/fastener_mass.py"]
    sources.extend(name for name in ("cad/hip_revision.py", "cad/tibia_revision.py") if (ROOT/name).is_file())
    report = {
        "status": "Analytical estimate. Weigh actual sorted hardware before loaded qualification.",
        "contract": "R5 inward hip and knee clamps with a straight tibia, canonical C018 shaft datum, M3x35 case clamps, external bridge nuts with OD7 washers, 1.1 mm auxiliary lands with M3x8 pitch screws and paired thin washers, and OD7 auxiliary-center retention washers.",
        "units": {"mass": "kg unless suffixed g", "positions": "mm in owning CAD link frame", "inertia": "kg m2"},
        "steel_density_g_cm3": 7.85,
        "source_hashes": {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
        "counts": dict(counts), "totals_g": mass_g, "categories": by_category,
        "reference_comparison": {
            "socket_M3x30_catalog_mass_g": 1.86,
            "model_nominal_M3x30_g": hardware_properties("screw", 30, None, (0, 0, 0), (0, 0, 1), "nominal")[0]*1000,
            "source": "https://www.accu.co.uk/api/product-datasheet?id=642041",
            "note": "A2 stainless catalog reference checks magnitude only. Owned fastener grade and head style remain unknown."},
        "assumptions": [
            "All counts exclude coupon-only hardware and spares. Thirteen main center screws and twelve auxiliary center screws are separate from fifty-two peripheral M3x6, thirty-two peripheral M3x8 and sixteen peripheral M3x20 screws.",
            "Low and high are geometry scenarios, not measured statistical bounds. Thread-effective diameters are 2.60, 2.75 and 3.0 mm; auxiliary self-tappers use 2.30, 2.60 and 3.0 mm.",
            "Low screw head is a 5.6 by 2.4 mm pan envelope with 75 percent shape fill minus 4 mm3 recess. Nominal socket head is 5.5 by 3 mm minus an AF2.5 by 1.3 mm socket, then 5 percent chamfer allowance. High retains a solid 5.5 by 3 mm head.",
            "Plain nuts are AF5.5 by 2.4 mm with bore 3.0, 2.75 and 2.5 mm, plus low and nominal chamfer factors 0.90 and 0.95. Washers have 3.2 mm bores and 0.5 mm thickness with 10 percent mass variation.",
            "Peripheral horn washers and the paired yaw auxiliary washers are OD6. External bridge and other planned washers are OD7. Tibia bridge holes have 8 mm centers, leaving 1 mm between OD7 washers.",
            "Each of the sixteen yaw auxiliary M3x20 screws uses two OD6 by 0.5 mm washers inside a 3.5 mm deep counterbore. The under-head plane is Z-50.5, giving a Z-30.5 tip and 1.9 mm nominal auxiliary flange engagement.",
            "Each of the thirty-two pitch auxiliary M3x8 screws uses two OD6 by 0.5 mm washers. The under-head plane is Y-24, giving a Y-16 tip and 1.9 mm engagement in the flange between Y-17.9 and Y-15.8. One washer would allow 0.3 mm rear projection and is excluded.",
            "Eight lower-arm to post screws are M3x20 with one OD7 by 0.5 mm washer. Their X/Y positions and staggered nut floors come from the canonical leg constants; loaded nut centers are 1.2 mm above their respective floors.",
            "Both pitch servo cases point inward. Hip and knee clamp screw axes therefore use the same rotation of -90 degrees about X, with screws entering along positive parent-link Z. The straight tibia bridge positions come from the final leg constants.",
            "The hip clamp has its own canonical bolt pattern; its relocated rear cap screw is not assumed to match the yaw and knee caps.",
            "Auxiliary center retainers are allocated to the servo housing parent link; their freely rotating discs remain in the child link.",
            "Each of the twelve supplied PA3x5 auxiliary-center retainers uses one added OD7, ID3.2, 0.5 mm washer against the fixed stub tip. Washer center is servo Z-33.35 and under-head Z-33.6; pitch equivalents are Y-18.85 and Y-19.1. The 7 mm washer spans the 6.05 mm disc bore, with 0.7 mm nominal axial gap to the disc face and 4.5 mm nominal screw entry beyond the washer. Actual thread engagement and driver/washer clearance require fit checks.",
            "The 55 g servo specification may or may not include supplied center hardware. If it does, subtract only the supplied-retainer category here; modeled metal horn masses are already separate in CAD and are not included here.",
            "Do not add this estimate on top of the old 50 g fastener allowance. Retain the separate 150 g wiring allowance only until actual wiring is weighed.",
            "Positions are analytical R5 attachment estimates read from the canonical servo contract and numeric leg constants. Nominal screw COM accounts for head and shaft mass; nut inertia approximates its hex section by a cylinder. This is not a screw-head collision model."],
        "links": dict(links), "pieces": records}
    (OUT/"fastener_mass.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    groups = defaultdict(list)
    for r in records:
        groups[(r["category"], r["sku"], r["link"], r["group"])].append(r)
    with (OUT/"fastener_mass.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "sku", "owning_link", "attachment", "quantity", "low_mass_g", "nominal_mass_g", "high_mass_g"])
        for key, items in sorted(groups.items()):
            w.writerow([*key, len(items), *[round(1000*sum(i["estimates"][mode]["mass_kg"] for i in items), 6) for mode in MODES]])
    lines = ["Fastener mass estimate", "", f"Counts: {dict(counts)}", "",
             "Mass totals in grams: " + ", ".join(f"{k}={v:.3f}" for k, v in mass_g.items()), "",
             "Replace the previous 50 g fastener allowance with this distributed estimate; do not add both.",
             "Use the high scenario for conservative mass screening until the actual hardware is weighed.", "",
             *report["assumptions"], "", "Reference: https://www.accu.co.uk/api/product-datasheet?id=642041", ""]
    (OUT/"fastener_mass.txt").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"counts": dict(counts), "totals_g": mass_g,
                      "per_link_nominal_g": {link: value["nominal"]["mass_kg"]*1000 for link, value in links.items()}}, indent=2))


if __name__ == "__main__":
    export()
