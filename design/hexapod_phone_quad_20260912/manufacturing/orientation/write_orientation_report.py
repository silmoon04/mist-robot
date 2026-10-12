"""Build the orientation review from measured geometry and slicer evidence."""
from pathlib import Path
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh

import analyze_orientations as audit

HERE = Path(__file__).resolve().parent


def support_note(sku):
    if sku in ("power_distribution_tray", "ubec_tray"):
        return "Flip X180. Broad tray top on bed; feet upward; no geometric support."
    if sku == "coxa_upper_and_hip_saddle":
        return "Flip X180. Greater bed contact. Local support in clamp offsets and bridge; keep nut loading slots accessible."
    if sku == "hex_faceted_cover":
        return "Keep current top face down. Support raised body-fixing bosses inside cover as well as nut recesses. Remove before assembly."
    if sku == "battery_tray":
        return "Keep current floor down. Local support below four raised tabs; strip support away from nut openings before fitting battery."
    if sku == "femur_main_and_knee_saddle":
        return "Keep broad cheek down. Support raised knee saddle and transverse bridge; leave horn seating face clean."
    if sku == "tibia_curved_main_and_foot":
        return "Keep broad cheek down. Support elevated foot and bridge; remove from strap slot and transverse fastener access."
    if sku == "yaw_case_saddle":
        return "Keep feet down. Inspect short internal ledges and transverse screw holes; support can obstruct case and nut fits."
    if sku.startswith("phone_cradle_foot"):
        return "Keep broad side down. Inspect horizontal screw holes; avoid support scarring of hub and rear-frame seating faces."
    if sku == "phone_cradle_rear_frame":
        return "Keep back down. Small nut-pocket roofs need preview; keep phone corner seats and nut faces clean."
    if sku == "phone_pan_hub":
        return "Keep current. Nut-pocket roofs are the local concern; preserve metal horn seating and flat foot attachment faces."
    if sku == "phone_pan_servo_saddle":
        return "Keep floor down. Raised mounting feet and clamp tower undersides need preview; preserve case-seat dimensions."
    if sku == "phone_pan_servo_cap":
        return "Keep inverted. Inspect recessed features and raised shoulders; preserve case contact face."
    if sku in ("servo_bus_adapter_tray", "esp32_tray"):
        return "Keep current. Local rail slots and relieved feet need preview; keep cable-tie access open."
    return "Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer."


def run():
    data = json.loads((HERE / "orientation_results.json").read_text())
    rows = data["results"]
    current = {r["sku"]: r for r in rows if r["orientation"] == "current"}
    sliced = json.loads((HERE / "slicer" / "slice_manifest.json").read_text())
    # Resolve the seven narrow-feature cases on a quarter-millimetre grid.
    refined = []
    selected = ["hex_faceted_cover", "battery_tray", "yaw_case_saddle", "coxa_upper_and_hip_saddle",
                "femur_main_and_knee_saddle", "tibia_curved_main_and_foot", "phone_cradle_rear_frame"]
    for sku in selected:
        source = next(s for s in data["source_stls"] if s["sku"] == sku)
        if audit.sha(source["path"]) != source["hash"]:
            raise RuntimeError(f"Source {sku} changed; rerun the audit before report generation")
        mesh = audit.oriented(trimesh.load_mesh(source["path"]), (0, 0, 0))
        fine = audit.raster_intervals(mesh, .25)
        coarse = current[sku]["support_envelope_mm3"]
        refined.append(dict(sku=sku, coarse_pitch_mm=audit.PITCH, fine_pitch_mm=.25,
                            coarse_support_envelope_mm3=coarse,
                            relative_volume_difference=abs(fine["support_envelope_mm3"]-coarse)/max(1, fine["support_envelope_mm3"]),
                            **fine))
    (HERE / "raster_resolution_check.json").write_text(json.dumps({"source_manifest_hash":data["source_manifest_hash"],
                                                                  "results":refined}, indent=2)+"\n", encoding="utf-8")
    lines = ["# Printing orientation and support audit", "",
             "Three production orientations should change: turn the supplied `power_distribution_tray`, `ubec_tray` and `coxa_upper_and_hip_saddle` STLs through 180 degrees about X. Keep the other existing orientations for the first physical fit build. The proposed rotations preserve assembled geometry. This audit itself did not modify CAD or production exports.", "",
             f"The audit covers all {len(current)} production SKUs in `{data['source_revision']}` and {len(rows)} orientation cases. Source manifest SHA-256: `{data['source_manifest_hash']}`. Results describe those exact bytes. Any later design revision needs a refreshed audit.", "",
             "## Changes supported by the evidence", "",
             "| Change | Measured reason | Assembly and fit consequence |", "| --- | --- | --- |",
             "| Flip `power_distribution_tray` and `ubec_tray` so their broad tray faces touch the bed | Their downward underside areas fall from 2,027 and 853 mm2 to zero. Bed contact increases from 100 mm2 each to 2,127 and 953 mm2. | No fastener or board position changes. Support is eliminated beneath the tray floors. |",
             "| Flip `coxa_upper_and_hip_saddle` about the current STL X axis | Exact bed contact increases from 92 to 378 mm2. Actual slicing changes time from 156.8 to 156.5 minutes and total PLA from 29.31 to 29.19 g. | Source print rotation changes from X=-90 to X=90. The nominal long axis stays parallel to layers. Retest its case fit in the final orientation and inspect support near nut loading slots. |",
             "| Correct support planning for `hex_faceted_cover` and `battery_tray` | Current orientations remain the practical choices. Their overhang columns occupy about 37.3 and 20.0 cm3 of air, chiefly below body-fixing bosses and battery tabs. | Remove supports before installing nuts, boards or the battery. If removal damages these interfaces, add local sloping ribs in a CAD revision rather than tilting either whole part. Ribs require connector, fastener and leg clearance checks. |", "",
             "The cover guide currently mentions only nut recesses. The raised body-fixing bosses also need support. The coxa guide currently says broad cheeks are on the bed; its original orientation contacts the bed through only about 92 mm2 of narrow features. A brim and a first-layer preview remain appropriate after the flip, especially around separated support islands.", "",
             "## Why 45 degrees is conditional", "",
             "A 45 degree tilt is a change of layer direction and contact area, not a general strength improvement. The actual femur comparison makes the support tradeoff explicit:", "",
             "| Femur orientation | Support angle from vertical | Predicted time | Total PLA | Support PLA |", "| --- | ---: | ---: | ---: | ---: |",
             "| Existing broad cheek down | 50 degrees | 172.4 min | 30.83 g | 3.58 g |",
             "| Rotate 45 degrees about long X axis | 50 degrees | 154.8 min | 27.19 g | 0.32 g |",
             "| Same rotated geometry | 40 degrees | 258.2 min | 41.54 g | 14.54 g |", "",
             "At 50 degrees, Cura deliberately leaves the nominal 45 degree faces unsupported. Tightening the support threshold to 40 degrees changes the result substantially. The tilt also changes the femur's height from 42.0 to 48.8 mm and its ideal zero-height planar bed contact from 2,486 mm2 to zero. Real first-layer contact is finite because the first layer has thickness, but this remains an edge-start orientation. A model brim was not included in these slices. Test a diagonal coupon with the intended cooling and brim before considering this as a production alternative.", "",
             "For a nominal tensile stress along a unit direction `a`, the normal traction on a layer with unit normal `n` is `sigma * (a dot n)^2`; the shear magnitude is `sigma * abs(a dot n) * sqrt(1 - (a dot n)^2)`. For the dominant long-axis bending fibres, rotating the femur about its long X axis keeps this nominal normal fraction at zero. Tilting about Y by 45 degrees raises it to 0.5. This is a stress-direction calculation, not a material strength ratio. Curved tibia regions, transverse bridges, horn fastener bearing and torsion have other local stress directions.", "",
             "Broad-side printing keeps the main femur and tibia bending outlines in the layer plane. Raised transverse bridges still carry loads across their layer interfaces. A hollow shell, higher infill percentage or diagonal print does not by itself establish a safe load. The separate structural assessment must address the bridge roots, screw holes and load paths.", "",
             "## Actual slicing", "",
             f"CuraEngine 5.13.0 completed {len(sliced['jobs'])} cases with a frozen numeric profile. Every movement stayed inside the nominal 225 x 225 x 265 mm envelope. The measured peak nominal deposition flow was 6.96 mm3/s. Source snapshots and extrusion accounting are in [the slicer comparison](slicer/SLICER_COMPARISON.md) and [validation](slicer/validation.json).", "",
             "The profile uses a 0.4 mm nozzle, 0.20 mm layers, 0.42 mm lines, five walls, six top and bottom layers, 35% gyroid, 210/60 C PLA, and 20/35/60/80 mm/s first-layer, outer-wall, inner-wall and infill speeds. Support is normal zigzag at 15%, with a 0.6 mm roof at 60%, 0.2 mm Z separation and 0.5 mm XY clearance. These are recorded analysis settings, not a validated printer profile. The saved toolpaths are compressed evidence with every command disabled.", "",
             "Across the three current integrated leg pieces, slicing predicts about 9.85 g of support per leg before any model brim. Four copies would use about 39.4 g of support. The co xa flip saves little filament; its benefit is adhesion. These figures exclude other robot parts and do not predict strength or physical support removal effort.".replace("co xa", "coxa"), "",
             "## Contact, access and dimensions", "",
             "Red surfaces in the visual are downward faces above the bed at a conservative 45 degree threshold. The geometry screen does not know whether the printer can bridge a particular span. For example, small nut-pocket roofs and 3.4 mm fastener holes may be printable as bridges, but a support blocker should follow a successful coupon and an inspected layer preview.", "",
             "Support that lands on another part surface can leave a second scar or obstruct a narrow opening. The screen records these lower contact areas and flags gaps below 6 mm. This is a tool-access warning, not a proof that support is trapped. Remove support before loading nuts, closing split cheeks or installing the phone. Fit coupons must preserve the final part orientation and settings at the interface being judged.", "",
             "All current part footprints fit the physical 225 mm bed with a nominal 4 mm brim. The 208 mm cover plus brim needs 216 mm, so it should be printed alone and checked against the slicer's actual excluded edge, skirt and purge paths. The landscape phone frame is 83.5 x 164.5 x 12.5 mm in its current print orientation. Keep it on its rear face; the phone remains landscape and upright when assembled.", "",
             "| SKU | Quantity | Current print dimensions, mm | Downward area, mm2 | Orientation and removal plan |", "| --- | ---: | --- | ---: | --- |"]
    for sku, r in current.items():
        dims = " x ".join(f"{r[k]:.1f}" for k in ("dim_x_mm", "dim_y_mm", "height_mm"))
        lines.append(f"| `{sku}` | {r['quantity']} | {dims} | {r['projected_overhang_45_inclusive_mm2']:.0f} | {support_note(sku)} |")
    lines.extend(["", "## Method and numerical limits", "",
                  "`analyze_orientations.py` tests current, flipped X180, both X90 sides, both Y90 sides, and positive/negative X45 and Y45 rotations. All rotations are additional to the supplied print-oriented STL. The script checks watertightness and source hashes before and after the run.", "",
                  "Projected area sums downward triangle area multiplied by the magnitude of its vertical normal. Faces on the bed are excluded. The inclusive 45 degree result deliberately counts borderline diagonal faces; the stricter 50 degree result shows support-threshold sensitivity. Area sums can include vertically stacked faces.", "",
                  "A deterministic 0.5 mm XY grid intersects triangle planes and pairs each downward overhang with the closest upward surface below it, or the bed. The volume integral sums projected pixel area times free vertical distance after a 0.2 mm top gap. It is an air-column envelope: support density, roof thickness, XY spread, tree paths and slicer bridge rules are not modeled. It must not be read as deposited plastic volume.", "",
                  "The algorithm passed analytic flat-plate and raised-roof tests. Seven parts with small features were rechecked at 0.25 mm grid spacing. These checks do not validate mechanical strength, cooling, warping, support breakaway or physical dimensions.", "",
                  "| Part | Support envelope at 0.25 mm, cm3 | Change from 0.5 mm grid |", "| --- | ---: | ---: |"])
    for r in refined:
        lines.append(f"| `{r['sku']}` | {r['support_envelope_mm3']/1000:.3f} | {100*r['relative_volume_difference']:.1f}% |")
    lines.extend(["", "The largest relative grid difference occurs in small nut-pocket features. Use the exact projected area for orientation screening and actual slice previews for local support decisions. No support-removal force or service load has been experimentally established.", ""])
    text = "\n".join(lines)
    (HERE / "ORIENTATION_AND_SUPPORT_AUDIT.md").write_text(text, encoding="utf-8")
    (HERE / "ORIENTATION_AND_SUPPORT_AUDIT.txt").write_text(text, encoding="utf-8")
    make_visual(current)


def make_visual(current):
    selected = ["coxa_upper_and_hip_saddle", "femur_main_and_knee_saddle", "tibia_curved_main_and_foot",
                "hex_faceted_cover", "battery_tray", "phone_cradle_rear_frame"]
    titles = ["Coxa, original print orientation", "Femur, broad cheek down", "Tibia, broad cheek down",
              "Cover, top face down", "Battery tray, floor down", "Landscape frame, back down"]
    fig = plt.figure(figsize=(16, 10.4), facecolor="#f6f6f3")
    for index, (sku, title) in enumerate(zip(selected, titles), 1):
        mesh = audit.oriented(trimesh.load_mesh(audit.CAD / "print_stl" / f"{sku}.stl"), (0, 0, 0))
        mask = (mesh.face_normals[:, 2] <= -math.cos(math.radians(45)) + 1e-7) & (mesh.triangles[:, :, 2].max(axis=1) > .21)
        ax = fig.add_subplot(2, 3, index, projection="3d")
        ax.set_facecolor("#f6f6f3")
        ax.add_collection3d(Poly3DCollection(mesh.triangles, facecolors="#aebbc3", edgecolors="none", alpha=.14))
        ax.add_collection3d(Poly3DCollection(mesh.triangles[mask], facecolors="#c74934", edgecolors="none", alpha=.96))
        d = mesh.extents
        floor = [[[0, 0, -.4], [d[0], 0, -.4], [d[0], d[1], -.4], [0, d[1], -.4]]]
        ax.add_collection3d(Poly3DCollection(floor, facecolors="#dae3da", alpha=.3))
        ax.set_xlim(0, d[0]); ax.set_ylim(0, d[1]); ax.set_zlim(0, d[2])
        ax.set_box_aspect(d.copy())
        ax.view_init(elev=24, azim=-59)
        ax.set_axis_off()
        ax.set_title(title, fontsize=12, weight="bold", pad=0)
        r = current[sku]
        ax.text2D(.05, -.01, f"{d[0]:.1f} x {d[1]:.1f} x {d[2]:.1f} mm\nDownward faces: {r['projected_overhang_45_inclusive_mm2']:.0f} mm2", transform=ax.transAxes, fontsize=10, color="#333d42")
    fig.suptitle("Where the current print orientations need support review", fontsize=20, weight="bold", x=.05, ha="left", y=.97)
    fig.text(.05, .925, "Red: downward faces above the bed at 45 degrees. Transparent grey: solid geometry. Green: print bed.", fontsize=12, color="#414d52")
    fig.text(.05, .025, "Geometry screening only. Small bridges, local support blockers and breakaway access require slice preview and fit coupons.", fontsize=10, color="#414d52")
    fig.subplots_adjust(left=.025, right=.975, top=.875, bottom=.085, wspace=.015, hspace=.15)
    fig.savefig(HERE / "support_hotspots.png", dpi=145, facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    run()
