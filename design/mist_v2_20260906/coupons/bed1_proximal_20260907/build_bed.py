"""Build the revised MIST first fit bed without modifying the original bed.

A fixed, locally authorized interface_contract.json is required for exports.
The contract separately records whether the leg has adopted these interfaces.
Run with ../.venv/Scripts/python.exe. All generated files stay beside this file.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent / "build_coupon_bed.py"
spec = importlib.util.spec_from_file_location("original_bed_recipe", SOURCE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_hashes():
    paths = [SOURCE, OUT.parent / "coupon_recipe.json",
             OUT.parent / "feedback_BED1.csv", OUT.parent / "fit_parameters.json"]
    paths += sorted((OUT.parent / "bed1").glob("*"))
    return {str(p.relative_to(OUT.parent)): sha(p) for p in paths if p.is_file()}


def add_feature(recipe, feature_id, interface, nominal, cad, x, y, **kw):
    recipe["features"].append(dict(feature_id=feature_id, interface=interface,
        nominal_mm=nominal, cad_mm=cad, x_mm=x, y_mm=y,
        part="06_624_retainer_boss", **kw))


def make_recipe(contract):
    recipe = base.make_recipe()
    original = json.loads(json.dumps(recipe))
    p = base.Part("06_624_retainer_boss")
    boss = contract["carrier_boss"]
    cap = contract["carrier_keeper"]
    # The spine joins the original 624 lug away from its M3 clearance hole.
    p.box(136, 16.5, 0, 3, 196.5, 3)
    p.box(15, 210, 0, 201, 6, 3)
    p.box(210, 70.5, 0, 6, 145.5, 3)
    p.box(18, 199, 0, 79.5, 3, 1.2)
    p.box(94.5, 199, 0, 3, 14, 1.2)
    for x, y in [(73.5, 213), (213, 213), (213, 73.5)]:
        p.box(x-2.5, y-2.5, 0, 5, 5, 6)
    for axis, x, y in [("X", 73.5, 213), ("Y", 213, 73.5)]:
        add_feature(recipe, "datum_139p5_"+axis, "long_datum_"+axis,
            139.5, 139.5, x, y, end_center_mm=[213, 213], pad_size_mm=5,
            pad_top_z_mm=6, backing_top_z_mm=3, outer_face_distance_mm=144.5,
            inner_face_distance_mm=134.5, measurement_axis=axis,
            purpose="Measure pad faces above the 3 mm backing; average outer and inner readings")
    p.label("139.5", 165, 213, 3, 2.4)
    for x, seat in zip([18, 57, 96], boss["candidate_seats_mm"]):
        y = 190
        p.cyl(x, y, 0, boss["outer_diameter_mm"], boss["height_mm"])
        p.cyl(x, y, -.1, boss["through_diameter_mm"], boss["height_mm"]+.2, True)
        p.cyl(x, y, boss["floor_mm"], seat, boss["seat_depth_mm"]+.1, True)
        lead = boss.get("lead_in_height_mm", 0)
        if lead:
            p.cone(x, y, boss["height_mm"]-lead, seat,
                   seat+boss["lead_in_diametral_mm"], lead+.1, True)
        for dx, dy in boss["bolt_centers_local_mm"]:
            p.cyl(x+dx, y+dy, -.1, boss["bolt_diameter_mm"], boss["height_mm"]+.2, True)
        p.label(str(round((seat-22)*100)), x, y+14, boss["height_mm"], 2)
        add_feature(recipe, f"proximal_bearing_OD22_{round((seat-22)*100):03}",
            "proximal_carrier_bearing_OD22", 22, seat, x, y,
            boss_outer_mm=boss["outer_diameter_mm"], seat_depth_mm=boss["seat_depth_mm"],
            floor_mm=boss["floor_mm"], through_diameter_mm=boss["through_diameter_mm"],
            print_axis="Z", purpose="627/608 outer-race fit and actual carrier retention profile")
    # Thin exterior tabs preserve a single slicer object. Cut them before use.
    p.box(120, 17.2, 0, 19, 1.6, .8)
    cx, cy = 106, 18
    p.cyl(cx, cy, 0, cap["outer_diameter_mm"], cap["thickness_mm"])
    p.cyl(cx, cy, -.1, cap["inner_diameter_mm"], cap["thickness_mm"]+.2, True)
    for dx, dy in cap["bolt_centers_local_mm"]:
        p.cyl(cx+dx, cy+dy, -.1, cap["bolt_diameter_mm"], cap["thickness_mm"]+.2, True)
    p.label("22", cx, cy+14, cap["thickness_mm"], 2)
    add_feature(recipe, "proximal_OD22_keeper", "proximal_carrier_keeper", 22,
        cap["inner_diameter_mm"], cx, cy, outer_diameter_mm=cap["outer_diameter_mm"],
        thickness_mm=cap["thickness_mm"], purpose="Detach exterior tab and test actual bearing keeper")
    wafer = contract["face_carrier"]
    cx, cy = 117, 72
    p.box(129, 71.2, 0, 10, 1.6, .8)
    p.cyl(cx, cy, 0, 30, wafer["thickness_mm"])
    p.cyl(cx, cy, -.1, wafer["center_bore_mm"], wafer["thickness_mm"]+.2, True)
    for i in range(4):
        a = i*math.pi/2
        p.cyl(cx+8*math.cos(a), cy+8*math.sin(a), -.1,
              wafer["sleeve_seat_mm"], wafer["thickness_mm"]+.2, True)
    add_feature(recipe, "face_carrier_PCD16", "face_carrier_PCD", 16, 16, cx, cy,
        hole_count=4, hole_diameter_mm=wafer["sleeve_seat_mm"],
        thickness_mm=wafer["thickness_mm"], central_diameter_mm=wafer["center_bore_mm"],
        minimum_radial_ligament_mm=8-wafer["sleeve_seat_mm"]/2-wafer["center_bore_mm"]/2,
        purpose="Dimension and sleeve fit only; no teeth or torque capacity claim")
    # The ladder repeats the actual 8 mm compression-sleeve engagement depth.
    p.box(106, 93, 0, 27, 10, 8)
    p.box(132, 97, 0, 7, 2, 1.2)
    for index, (x, d) in enumerate(zip([111, 119, 127], [6.55, 6.60, 6.75]), 1):
        p.cyl(x, 98, -.1, d, 8.2, True)
        for mark in range(index):
            p.cyl(x+mark-(index-1)/2, 93.9, 7.6, .6, .5, True)
        add_feature(recipe, f"sleeve_OD6p5_{round(d*100)}", "steel_sleeve_OD6p5",
            6.5, d, x, 98, hole_depth_mm=8, print_axis="Z", identification_dots=index)
    if contract.get("jack_bridge"):
        jack = contract["jack_bridge"]
        # Source x -> bed X, source -z (u) -> bed Y, source y -> bed Z.
        # This keeps the jack-nut axis horizontal when bearing bores print Z.
        p.box(103, 36, 0, 26, 20, 22)
        p.box(128, 45, 0, 11, 2, 1.2)
        p.shape("horizontal_cylinder", True, x=116, y=35.8, z=11,
                diameter=4.4, length=20.4)
        p.shape("horizontal_hex", True, x=116, y=35.9, z=11,
                across_flats=jack["nut_pocket_af_mm"], length=14.1)
        p.box(106.9, 49.95, 1.9, 18.2, 2.1, 18.2, True)
        if jack.get("plate_side_opening"):
            p.box(116, 49.95, 1.9, 13.1, 2.1, 18.2, True)
        add_feature(recipe, "jack_M4_coupling_nut", "jack_M4_coupling_nut_AF", 7,
            jack["nut_pocket_af_mm"], 116, 36, pocket_length_mm=14.1,
            print_axis="Y_horizontal", hole_center_z_mm=11, actual_nut_length_mm=12,
            purpose="Detach the exterior tab before horizontal nut and plate insertion")
        add_feature(recipe, "jack_load_plate", "jack_load_plate_pocket", 18, 18.2,
            116, 51, nominal_thickness_mm=2, pocket_thickness_mm=2.1)
    # A capsule slot in a 4 mm wall repeats the sliding-carriage interface.
    p.box(116, 182, 0, 13, 19, 4)
    p.box(127, 198, 0, 12, 3, 1.2)
    p.cyl(122.5, 189.5, -.1, 4.4, 4.2, True)
    p.cyl(122.5, 193.5, -.1, 4.4, 4.2, True)
    p.box(120.3, 189.5, -.1, 4.4, 4, 4.2, True)
    add_feature(recipe, "slider_M4_slot", "slider_M4_slot_width", 4, 4.4,
        122.5, 191.5, total_length_mm=8.4, wall_thickness_mm=4, print_axis="Z")
    recipe["parts"][5]["ops"] += p.recipe()["ops"]
    recipe.update(purpose="first_fit_bed_proximal_interfaces", production_release=False,
        source_recipe_sha256=sha(SOURCE), interface_contract=contract,
        interface_contract_sha256=(sha(OUT / "interface_contract.json")
            if (OUT / "interface_contract.json").exists()
            else hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()),
        datum_pad_centers_mm=[[73.5, 213], [213, 213], [213, 73.5]],
        retained_original_part_names=[p["name"] for p in original["parts"]])
    recipe["notes"] += ["Seven objects; object 06 carries connected calibration additions.",
        "Keeper and face wafer detach at 0.8 mm exterior tabs before fit testing.",
        "Cut the jack block's 1.2 mm exterior tab before loading the side plate; do not twist it free.",
        "Sleeve holes run left to right: 6.55, 6.60, 6.75 mm, marked by one, two, three dots.",
        "Measure long datum pads above Z=3 mm; nominal outside 144.5 and inside 134.5 mm.",
        "New carrier and transmission interfaces are prototype fit coupons, not structural releases."]
    return recipe, original


def primitive(cq, op):
    if op["kind"] == "horizontal_cylinder":
        return cq.Solid.makeCylinder(op["diameter"]/2, op["length"],
            cq.Vector(op["x"], op["y"], op["z"]), cq.Vector(0, 1, 0))
    if op["kind"] == "horizontal_hex":
        r = op["across_flats"] / math.sqrt(3)
        # Plane local Y points toward bed -Z; hex symmetry preserves source flats.
        plane = cq.Plane(origin=(op["x"], op["y"], op["z"]),
                         xDir=(1, 0, 0), normal=(0, 1, 0))
        return cq.Workplane(plane).polyline([(r*math.cos(i*math.pi/3),
            r*math.sin(i*math.pi/3)) for i in range(6)]).close().extrude(op["length"]).val()
    return base.primitive(cq, op)


def build_shape(cq, data):
    adds = [primitive(cq, o) for o in data["ops"] if o["op"] == "add"]
    cuts = [primitive(cq, o) for o in data["ops"] if o["op"] == "cut"]
    body = adds[0].fuse(*adds[1:]).clean() if len(adds) > 1 else adds[0]
    return body.cut(*cuts).clean() if cuts else body


def preview(meshes, recipe, *, watermark=None):
    import os
    os.environ["MPLCONFIGDIR"] = str(OUT / ".mplconfig")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    import numpy as np
    from matplotlib.collections import PolyCollection
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    colors = ["#6698af", "#dfae70", "#7caa87", "#ae89a2", "#ae89a2", "#6476ad", "#8c9bc5"]
    fig, ax = plt.subplots(figsize=(12, 12))
    for (name, mesh), color in zip(meshes.items(), colors):
        faces = mesh.faces[mesh.face_normals[:, 2] > .5]
        ax.add_collection(PolyCollection(mesh.vertices[faces][:, :, :2],
            facecolors=color, edgecolors="none", antialiaseds=False))
    for part in recipe["parts"]:
        for op in part["ops"]:
            if op["op"] == "cut" and op["kind"] == "box" and op["sz"] <= .51:
                ax.add_patch(plt.Rectangle((op["x"], op["y"]), op["sx"], op["sy"],
                    color="#35424d", linewidth=0))
    for f in recipe["features"]:
        if f["interface"].startswith("bearing"):
            ax.text(f["x_mm"], f["y_mm"], f'{f["cad_mm"]:.2f}',
                ha="center", va="center", fontsize=6.2)
    for x, seat in zip([18, 57, 96], recipe["interface_contract"]["carrier_boss"]["candidate_seats_mm"]):
        ax.text(x, 190, f"{seat:.2f}", ha="center", va="center", fontsize=8)
    for x, y, text in [(106, 18, "OD22\nkeeper"),
                        (119, 109, "6.55 / 6.60 / 6.75"), (123, 178, "M4 slot")]:
        ax.text(x, y, text, ha="center", va="center", fontsize=7)
    ax.annotate("16 PCD / 4 sleeves", xy=(113, 85), xytext=(111, 88),
                ha="center", va="center", fontsize=7,
                arrowprops=dict(arrowstyle="-", linewidth=.6))
    if recipe["interface_contract"].get("jack_bridge"):
        ax.text(116, 46, "Horizontal\nM4 nut / plate", ha="center", va="center", fontsize=7)
    for x, y, label in [(73.5, 213, "A"), (213, 213, "B"), (213, 73.5, "C")]:
        ax.add_patch(plt.Rectangle((x-2.5, y-2.5), 5, 5, fill=False,
                                  edgecolor="#e9effa", linewidth=.8))
        ax.text(x, y, label, ha="center", va="center", fontsize=7, color="white", weight="bold")
    ax.set(xlim=(-4, 222), ylim=(-4, 222), aspect="equal", xlabel="X / mm", ylabel="Y / mm")
    ax.set_title("MIST revised first fit bed | 7 handled objects | 216 × 216 mm", loc="left", fontsize=16, pad=18)
    ax.grid(alpha=.15)
    if watermark:
        fig.text(.5, .48, watermark, ha="center", va="center", rotation=32,
                 fontsize=34, color="#a92d29", alpha=.65, weight="bold")
    prefix = "PROBE_UNCONFIRMED" if watermark else "BED1_PROXIMAL"
    fig.savefig(OUT / (prefix+"_TOP_VIEW.png"), dpi=170, bbox_inches="tight")
    plt.close(fig)
    fig = plt.figure(figsize=(13, 10))
    ax = fig.add_subplot(111, projection="3d")
    polygons, face_colors = [], []
    light = np.array([-.35, -.5, .79])
    light = light / np.linalg.norm(light)
    for (name, mesh), color in zip(meshes.items(), colors):
        polygons.append(mesh.vertices[mesh.faces])
        shade = .5 + .5*np.clip(mesh.face_normals @ light, 0, 1)
        face_colors.append(np.array(mcolors.to_rgb(color))[None, :]*shade[:, None])
    coll = Poly3DCollection(np.concatenate(polygons), facecolors=np.concatenate(face_colors),
        edgecolors="none", linewidths=0, alpha=1, antialiased=False, zsort="average")
    ax.add_collection3d(coll)
    ax.set(xlim=(0, 220), ylim=(0, 220), zlim=(0, 30), xlabel="X / mm", ylabel="Y / mm", zlabel="Z / mm")
    ax.set_box_aspect((220, 220, 45))
    ax.view_init(elev=49, azim=-112)
    ax.set_title("MIST fit bed | raised datum pads and horizontal jack pocket", loc="left", fontsize=15)
    if watermark:
        fig.text(.5, .48, watermark, ha="center", va="center", rotation=25,
                 fontsize=32, color="#a92d29", alpha=.65, weight="bold")
    fig.savefig(OUT / (prefix+"_PERSPECTIVE.png"), dpi=155, bbox_inches="tight")
    plt.close(fig)


def run(recipe_only=False):
    before = protected_hashes()
    contract = json.loads((OUT / "interface_contract.json").read_text())
    fixed_coupon_authorized = (contract.get("status") == "fixed_coupon_contract_pending_leg_adoption"
                               and contract.get("root_authorized_export") is True)
    if not fixed_coupon_authorized and contract.get("status") != "confirmed_candidate_interfaces":
        raise RuntimeError("A fixed, authorized coupon contract is required before export")
    recipe, original = make_recipe(contract)
    (OUT / "coupon_recipe.json").write_text(json.dumps(recipe, indent=2)+"\n")
    (OUT / "feature_manifest.json").write_text(json.dumps(recipe["features"], indent=2)+"\n")
    if recipe_only:
        assert before == protected_hashes(), "Protected original files changed"
        return
    import cadquery as cq
    import trimesh
    from mesh_checks import inspect_mesh_shells
    shapes, meshes, checks = [], {}, []
    for i, data in enumerate(recipe["parts"]):
        print("Building", data["name"], flush=True)
        body = build_shape(cq, data)
        assert body.isValid(), "Invalid BRep: "+data["name"]
        assert len(body.Solids()) == 1, (data["name"], len(body.Solids()))
        stl = OUT / (data["name"]+".stl")
        cq.exporters.export(body, str(stl), tolerance=.03, angularTolerance=.08)
        cq.exporters.export(body, str(OUT / (data["name"]+".step")))
        mesh = trimesh.load_mesh(stl, process=True)
        assert mesh.is_watertight and mesh.is_winding_consistent, data["name"]
        shell_checks = inspect_mesh_shells(mesh)
        retained_ops = original["parts"][i]["ops"]
        assert data["ops"][:len(retained_ops)] == retained_ops
        original_loss = 0.0
        if i == 5:
            original_body = build_shape(cq, original["parts"][i])
            original_loss = original_body.cut(body).Volume()
            assert original_loss < 1e-5, "Object06 extension removed original geometry"
        shapes.append(body)
        meshes[data["name"]] = mesh
        checks.append(dict(part=data["name"], brep_valid=True, solid_count=1,
            watertight=True, winding_consistent=True, mesh_shell_checks=shell_checks,
            volume_mm3=body.Volume(), mesh_volume_mm3=float(mesh.volume),
            bounds_mm=mesh.bounds.tolist(), triangles=len(mesh.faces),
            original_operations_retained=True, original_geometry_removed_mm3=original_loss))
    distances = []
    for i, a in enumerate(shapes):
        for j, b in enumerate(shapes[:i]):
            overlap = a.intersect(b).Volume()
            assert overlap < 1e-5, (j+1, i+1, overlap)
            distance = a.distance(b)
            assert distance > 1e-5, "Two slicer objects touch"
            distances.append(dict(parts=[j+1, i+1], distance_mm=distance, intersection_mm3=overlap))
    compound = cq.Compound.makeCompound(shapes)
    stem = "MIST_BED1_PROXIMAL_ALL_PARTS"
    cq.exporters.export(compound, str(OUT / (stem+".step")))
    cq.exporters.export(compound, str(OUT / (stem+".stl")), tolerance=.03, angularTolerance=.08)
    base.export_3mf(meshes, OUT / (stem+".3mf"))
    step_roundtrip = cq.importers.importStep(str(OUT / (stem+".step"))).val()
    assert step_roundtrip.isValid() and len(step_roundtrip.Solids()) == 7
    all_mesh = trimesh.util.concatenate(list(meshes.values()))
    assert all(d <= 216.00001 for d in all_mesh.extents[:2]), all_mesh.bounds
    assert all_mesh.bounds[0, 2] > -1e-5
    with zipfile.ZipFile(OUT / (stem+".3mf")) as archive:
        xml = ET.fromstring(archive.read("3D/3dmodel.model"))
        assert xml.attrib["unit"] == "millimeter"
        assert len(xml.findall(".//{*}object")) == 7
        assert len(xml.findall(".//{*}item")) == 7
    after = protected_hashes()
    assert before == after, "Protected original files changed"
    validation = dict(status="geometry_checks_passed_physical_fit_pending", part_count=7,
        bounds_mm=all_mesh.bounds.tolist(), extent_mm=all_mesh.extents.tolist(),
        model_volume_cm3=sum(s.Volume() for s in shapes)/1000,
        solid_PLA_estimate_g=sum(s.Volume() for s in shapes)/1000*1.24,
        tessellation_mm=.03, inter_part_intersections_mm3=0,
        minimum_inter_part_distance_mm=min(d["distance_mm"] for d in distances),
        pairwise_checks=distances, checks=checks, units_3mf="millimeter",
        step_roundtrip_valid=True, step_roundtrip_solids=7,
        source_files_unchanged=True, protected_original_sha256=before,
        contract_sha256=sha(OUT / "interface_contract.json"),
        coupon_contract_status=contract["status"],
        manufacturing_interface_confirmation=contract.get("manufacturing_interface_confirmation", "pending_leg_adoption"),
        builder_sha256=sha(Path(__file__).resolve()),
        unvalidated=["leg adoption of coupon interfaces", "printer profile", "printed fit", "horizontal pocket bridging",
            "sleeve and coupling-nut dimensions", "bearing retention", "structural loads"])
    (OUT / "validation.json").write_text(json.dumps(validation, indent=2)+"\n")
    preview(meshes, recipe)
    files = sorted(p for p in OUT.iterdir() if p.is_file()
        and p.suffix.lower() in [".3mf", ".stl", ".step", ".png"]
        and not p.name.startswith("PROBE_"))
    (OUT / "artifact_sha256.json").write_text(json.dumps({p.name:sha(p) for p in files}, indent=2)+"\n")
    print(json.dumps({k:v for k,v in validation.items() if k not in ["checks", "pairwise_checks", "protected_original_sha256"]}, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe-only", action="store_true")
    run(parser.parse_args().recipe_only)
