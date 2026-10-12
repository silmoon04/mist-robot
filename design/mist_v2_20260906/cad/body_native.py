"""MIST body geometry, shared by native Fusion and offline solid-model exports.

Dimensions are millimetres. Parts are defined above body-bottom z=0; the final
assembly occurrence is translated to the simulator's hip-plane origin.
This is an engineering candidate. Hardware interfaces remain measurement gates.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


COLORS = {
    "white": (235, 234, 225, 255), "grey": (93, 100, 109, 255),
    "black": (22, 29, 34, 255), "cyan": (0, 235, 228, 255),
    "structure": (66, 77, 86, 255), "battery": (53, 110, 148, 255),
    "reference": (154, 125, 93, 150), "foam": (46, 48, 49, 255),
}


def body_spec(params):
    """Return the dimensional recipe; no Fusion import or filesystem side effects."""
    g = params["geometry"]
    diameter = g["body_diameter_m"] * 1000
    overall_h = g.get("overall_body_lid_handle_height_m", g["body_height_m"]) * 1000
    if abs(diameter - 180) > 0.01 or abs(overall_h - 260) > 0.01:
        raise ValueError("Body packaging is audited only for diameter180/overall260mm; rerun packaging before resizing")
    parts = []

    def part(name, color, category="print", note=""):
        entry = dict(name=name, color=color, category=category, note=note, ops=[])
        parts.append(entry)
        return entry["ops"]

    def box(o, center, size, mode="add"):
        o.append(dict(kind="box", center=center, size=size, mode=mode))

    def cyl(o, start, end, radius, inner=0, mode="add"):
        o.append(dict(kind="annulus" if inner else "cylinder", start=start,
                      end=end, radius=radius, inner=inner, mode=mode))

    def radial_box(o, az, r, z, radial, tangential, height, mode="add"):
        o.append(dict(kind="radial_box", az=az, radius=r, z=z,
                      radial=radial, tangential=tangential, height=height, mode=mode))

    def polygon(o, points, thickness, origin, normal, x_axis, mode="add"):
        o.append(dict(kind="polygon", points=points, thickness=thickness,
                      origin=origin, normal=normal, x_axis=x_axis, mode=mode))

    o = part("B01_structural_lower_deck", "structure", note="PETG flat on bed; four M4 anchors per root at radial78/98mm and tangential+/-22mm; extended tabs require full assembly and fastener-access check")
    cyl(o, (0, 0, 0), (0, 0, 5), 84)
    for y in (-51, 51):
        box(o, (0, y, 2.5), (70, 21, 9), "cut")
    for az in g["mount_azimuths_deg"]:
        radial_box(o, az, 94.5, 2.5, 47, 52, 5)
        for r in (78, 98):
            a = math.radians(az)
            for tangent in (-22, 22):
                x = r * math.cos(a) - tangent * math.sin(a)
                y = r * math.sin(a) + tangent * math.cos(a)
                cyl(o, (x, y, -1), (x, y, 6), 2.2, mode="cut")
    for x in (-48, 48):
        for y in (-60, 60):
            cyl(o, (x, y, -1), (x, y, 6), 1.7, mode="cut")

    for side in (-1, 1):
        o = part(f"B02_battery_rail_{'L' if side > 0 else 'R'}", "structure",
                 note="Pads and strap dimensions need actual pack, tie roll and coupon measurements")
        box(o, (-25, side * 22, 6.625), (112, 10, 3.25))
        box(o, (-25, side * 25.5, 11), (112, 3, 12))
        for x in (-58, 8):
            box(o, (x, side * 22, 6.5), (15.5, 3, 8), "cut")
        for x in (-72, 22):
            cyl(o, (x, side * 21, 3), (x, side * 21, 10), 1.7, mode="cut")

    o = part("H01_battery_HOOVO_3S_REFERENCE", "battery", "hardware_reference",
             "104x34.5x24.5mm,174g repository placeholder; measure the real pack including wires")
    box(o, (-25, 0, 20.5), (104, 34.5, 24.5))

    for x in (-48, 48):
        for y in (-60, 60):
            for stage, z0, z1 in (("lower", 5, 61), ("upper", 64, 104)):
                o = part(f"B03_core_post_{'F' if x > 0 else 'R'}{'L' if y > 0 else 'R'}_{stage}", "structure",
                         note="10mmOD compression spacer; continuous M3 tie rod clamps both decks; rod/nut stock not yet confirmed")
                cyl(o, (x, y, z0), (x, y, z1), 5, 1.7)

    o = part("B04_phone_and_electronics_deck", "structure", note="Horizontal PETG deck; remove before reaching battery from above")
    cyl(o, (0, 0, 61), (0, 0, 64), 83)
    for y in (-52, 52):
        box(o, (0, y, 62), (70, 14, 8), "cut")
    for x in (-48, 48):
        for y in (-60, 60):
            cyl(o, (x, y, 59), (x, y, 65), 1.7, mode="cut")
    # Three pads locate an unknown brain phone without imposing a measured size.
    for x in (-39, 39):
        box(o, (x, 0, 66), (2.4, 138, 4))
    for y in (-64, 64):
        for x in (-33, 33):
            box(o, (x, y, 62), (3, 12, 8), "cut")
    box(o, (76, 0, 62), (24, 79, 8), "cut")

    o = part("H02_brain_phone_ENVELOPE", "reference", "hardware_reference",
             "155x75x10mm provisional envelope; device model and actual mass remain unknown")
    box(o, (0, 0, 69), (75, 155, 10))

    o = part("B05_upper_core_ring", "structure")
    cyl(o, (0, 0, 104), (0, 0, 108), 86.6, 74)
    # Front cassette crosses this level; leave its interior path open.
    box(o, (79, 0, 106), (32, 79, 10), "cut")
    for x in (-48, 48):
        for y in (-60, 60):
            cyl(o, (x, y, 102), (x, y, 110), 1.7, mode="cut")
    for az in (90, 180, 270):
        radial_box(o, az, 82, 114, 7, 13, 16)
        a = math.radians(az)
        cyl(o, (75 * math.cos(a), 75 * math.sin(a), 114),
            (92 * math.cos(a), 92 * math.sin(a), 114), 1.7, mode="cut")

    # Two service halves retain the grey drum between hip openings.
    for front in (True, False):
        o = part("B06_lower_shell_" + ("front" if front else "rear"), "grey",
                 note="2.4mm cosmetic wall; hip-window size awaits moving pod interference audit")
        cyl(o, (0, 0, 82 if front else 6), (0, 0, 106), 90, 87.6)
        box(o, ((-101 if front else 101), 0, 56), (202, 210, 110), "cut")
        for az in g["mount_azimuths_deg"]:
            if not front and math.cos(math.radians(az)) < 0:
                radial_box(o, az, 99, 44, 54, 88, 76, "cut")
        if front:
            box(o, (87, 0, 78), (30, 60, 30), "cut")
            box(o, (88, 0, 139), (36, 95, 86), "cut")
        else:
            box(o, (-87, 0, 33), (30, 44, 32), "cut")
        # Horizontal seam screws into shell blocks are deliberately not finalized.

    for front in (True, False):
        o = part("B07_upper_shell_" + ("front" if front else "rear"), "white",
                 note="112mm tall cosmetic clamshell; rim and core carry alignment, seam attachment awaits coupon")
        cyl(o, (0, 0, 108), (0, 0, 220), 90, 87.6)
        box(o, ((-101 if front else 101), 0, 164), (202, 210, 120), "cut")
        if front:
            box(o, (88, 0, 139), (36, 95, 86), "cut")
        for az in ((90, 270) if front else (90, 180, 270)):
            a = math.radians(az)
            cyl(o, (75 * math.cos(a), 75 * math.sin(a), 114),
                (94 * math.cos(a), 94 * math.sin(a), 114), 1.7, mode="cut")

    o = part("B08_lower_white_trim", "white")
    cyl(o, (0, 0, 101), (0, 0, 107.5), 92, 90.25)
    box(o, (89, 0, 104), (34, 95, 12), "cut")

    o = part("B09_dark_waist_band", "black")
    cyl(o, (0, 0, 96), (0, 0, 101), 92, 90.25)
    box(o, (89, 0, 99), (34, 95, 12), "cut")

    o = part("B10_lid_twin_rim", "white", note="Print flat; two raised circumferential bands preserve the reference silhouette")
    cyl(o, (0, 0, 216), (0, 0, 224), 87.25, 84.8)
    cyl(o, (0, 0, 220), (0, 0, 222.6), 92, 84.8)
    cyl(o, (0, 0, 222.6), (0, 0, 229.2), 90.1, 87.1)
    cyl(o, (0, 0, 229.2), (0, 0, 232), 92, 87.1)

    o = part("B11_shallow_lid", "white", note="Native revolved section; print rim down; bridge handle removes lid only")
    o.append(dict(kind="revolve", mode="add", points=[(90.1, 232), (84, 234.8),
                  (68, 239.2), (0, 242), (0, 239.5), (67.6, 236.7),
                  (82.6, 232.4), (84.5, 230.5), (87, 230.5), (87, 232)]))
    for x in (-6, 6):
        for y in (-42, 42):
            cyl(o, (x, y, 235), (x, y, 245), 1.7, mode="cut")

    o = part("B12_lid_bridge_handle", "white", note="Print broad side on bed; four screw feet; do not lift the robot by this cosmetic lid handle")
    polygon(o, [(-50, 237), (-48, 248), (-35, 257), (-18, 260), (18, 260),
                (35, 257), (48, 248), (50, 237), (36, 237), (34, 244),
                (24, 248), (0, 251), (-24, 248), (-34, 244), (-36, 237)],
            24, (-12, 0, 0), (1, 0, 0), (0, 1, 0))
    o.append(dict(kind="revolve", mode="cut", points=[(0, 200), (90.1, 200),
                  (90.1, 232), (84, 234.8), (68, 239.2), (0, 242)]))
    for x in (-6, 6):
        for y in (-42, 42):
            cyl(o, (x, y, 235), (x, y, 256), 1.7, mode="cut")

    # The cassette is mostly within the cylindrical shell. The white barrel
    # masks unused phone pixels above and below a central square aperture.
    o = part("B13_face_phone_cassette", "black", note="Portrait Mi9SE,0.4mm pocket clearance per side; removable from open lid after unplugging")
    box(o, (72.575, 0, 140), (11.35, 76.1, 151))
    box(o, (73.775, 0, 140.3), (9.75, 71.3, 148.3), "cut")
    # Open front and top, preserve edge rails and three rear support ribs.
    box(o, (80.2, 0, 140), (15, 65, 149), "cut")
    box(o, (74.2, 0, 217), (16, 71.3, 8), "cut")
    box(o, (74.2, 0, 63.5), (18, 17, 10), "cut")
    for z in (111, 177):
        box(o, (67.5, 0, z), (8, 60, 42), "cut")
    for z in (100, 170):
        cyl(o, (66, -34.5, z), (84, -34.5, z), 1.7, mode="cut")
        cyl(o, (66, 34.5, z), (84, 34.5, z), 1.7, mode="cut")

    o = part("H03_face_phone_Mi9SE_REFERENCE", "reference", "hardware_reference",
             "147.5x70.5x7.45mm repository placeholder; screen active area/buttons/case/USB need measurement")
    box(o, (73.775, 0, 140), (7.45, 70.5, 147.5))

    o = part("B14_square_face_bezel", "black", note="94x86mm outline masks a64x68mm phone view; 17mm recess constrains off-axis viewing")
    box(o, (91.5, 0, 139), (15, 94, 86))
    box(o, (92, 0, 139), (20, 66, 70), "cut")
    # Flared front mouth leaves only a short narrow optical tunnel.
    box(o, (94, 0, 139), (14, 83, 77), "cut")
    for y in (-35.5, 35.5):
        for z in (100, 178):
            cyl(o, (81, y, z), (102, y, z), 1.7, mode="cut")

    o = part("H04_face_display_ACTIVE_AREA_GUIDE", "black", "visual_reference",
             "Display guide only; the app must render eyes on a black background in the measured window")
    box(o, (77.55, 0, 139), (0.1, 64, 68))
    for side in (-1, 1):
        o = part("H05_eye_" + ("L" if side > 0 else "R"), "cyan", "visual_reference")
        cyl(o, (77.7, side * 16, 145), (77.8, side * 16, 145), 7, 5.5)
    o = part("H06_mouth", "cyan", "visual_reference")
    box(o, (77.75, 0, 127), (0.1, 10, 2))

    o = part("B15_secondary_dark_panel", "black", note="Reference-like lower fascia; frontToF opening and cable relief need hardware confirmation")
    box(o, (92, 0, 78), (10, 58, 29))
    box(o, (88, 0, 78), (8, 52, 23), "cut")
    box(o, (96, 17, 78), (8, 10, 8), "cut")
    box(o, (92, -28, 72), (12, 8, 9), "cut")

    o = part("B16_rear_connector_guard", "grey", note="Open rear power-disconnect reach; connector mounting hole pattern remains measured-part work")
    box(o, (-94, 0, 32), (8, 49, 36))
    box(o, (-94, 0, 32), (14, 39, 27), "cut")

    return dict(schema_version=1, units="mm", local_origin="body bottom",
                assembly_z_offset=-g["hip_mount_height_above_body_bottom_m"] * 1000,
                envelope=dict(body_diameter=180, main_barrel_height=220, overall_height=260,
                              bezel_front_x=99, bezel_width=94, face_visible_width=64,
                              face_visible_height=68),
                com_bodybottom_mm=dict(battery=[-25, 0, 20.5], brain_phone=[0, 0, 69],
                                       face_phone=[73.775, 0, 140]),
                assumptions=dict(shell_wall=2.4, radial_lid_clearance=0.35,
                                 phone_pocket_clearance_per_side=0.4,
                                 petg_density_g_cm3=1.27,
                                 brain_phone_envelope=[155, 75, 10]), parts=parts)


def _native_revolve(component, name, points):
    import adsk.core
    import adsk.fusion
    sketch = component.sketches.add(component.xZConstructionPlane)
    sketch.name = name + "_section"
    pts = [sketch.modelToSketchSpace(adsk.core.Point3D.create(r / 10, 0, z / 10)) for r, z in points]
    for i, a in enumerate(pts):
        sketch.sketchCurves.sketchLines.addByTwoPoints(a, pts[(i + 1) % len(pts)])
    sketch.isVisible = False
    feature_input = component.features.revolveFeatures.createInput(
        sketch.profiles.item(0), component.zConstructionAxis,
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    feature_input.setAngleExtent(False, adsk.core.ValueInput.createByReal(2 * math.pi))
    feature = component.features.revolveFeatures.add(feature_input)
    feature.name = name
    result = feature.bodies.item(0)
    result.name = name
    return result


def _radial_points(op):
    a = math.radians(op["az"])
    ca, sa = math.cos(a), math.sin(a)
    result = []
    for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        r = op["radius"] + u * op["radial"] / 2
        t = v * op["tangential"] / 2
        result.append((r * ca - t * sa, r * sa + t * ca))
    return result


def build_body(root, params):
    """Build editable native Fusion features; return root occurrence and parts.

    The caller must be in a parametric Fusion Design. All Fusion geometry errors
    propagate. Color-library availability cannot change the dimensional model.
    """
    import adsk.core
    import native_parts as n
    spec = body_spec(params)
    occurrence = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occurrence.component.name = "MIST_body_native_candidate"
    components, bodies = {}, {}
    for p in spec["parts"]:
        part_occ = occurrence.component.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp = part_occ.component
        comp.name = p["name"]
        target = None
        for i, op in enumerate(p["ops"]):
            name = p["name"] + "_" + str(i + 1)
            kind = op["kind"]
            if kind == "box":
                tool = n.box(comp, name, op["center"], op["size"])
            elif kind == "cylinder":
                tool = n.cylinder(comp, name, op["start"], op["end"], op["radius"])
            elif kind == "annulus":
                tool = n.annulus(comp, name, op["start"], op["end"], op["radius"], op["inner"])
            elif kind == "radial_box":
                tool = n.polygon(comp, name, _radial_points(op), op["height"],
                                 origin=(0, 0, op["z"] - op["height"] / 2))
            elif kind == "polygon":
                tool = n.polygon(comp, name, op["points"], op["thickness"],
                                 origin=op["origin"], normal=op["normal"], x_axis=op["x_axis"])
            elif kind == "revolve":
                tool = _native_revolve(comp, name, op["points"])
            else:
                raise ValueError(kind)
            if target is None:
                if op["mode"] != "add":
                    raise ValueError("First operation must add material")
                target = tool
            elif op["mode"] == "cut":
                target = n.subtract(comp, target, [tool], name + "_cut")
            else:
                target = n.union(comp, target, [tool], name + "_join")
        target.name = p["name"]
        comp.attributes.add("MIST", "category", p["category"])
        comp.attributes.add("MIST", "manufacturing_note", p["note"])
        comp.attributes.add("MIST", "color_rgba", json.dumps(COLORS[p["color"]]))
        bodies[p["name"]] = target
        components[p["name"]] = comp
    transform = adsk.core.Matrix3D.create()
    transform.translation = adsk.core.Vector3D.create(0, 0, spec["assembly_z_offset"] / 10)
    n.place_occurrence(occurrence, transform)
    return dict(occurrence=occurrence, components=components, bodies=bodies,
                spec=spec, status="native_candidate_requires_Fusion_execution_and_interface_measurements")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--parameters", type=Path, default=Path(__file__).parents[1] / "simulation" / "parameters.json")
    parser.add_argument("--spec-out", type=Path)
    args = parser.parse_args()
    result = body_spec(json.loads(args.parameters.read_text(encoding="utf-8")))
    if args.spec_out:
        args.spec_out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    else:
        print(json.dumps({k: v for k, v in result.items() if k != "parts"}, indent=2))
