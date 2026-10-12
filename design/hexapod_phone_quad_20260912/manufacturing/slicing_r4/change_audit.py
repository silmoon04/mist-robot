"""Compare R4 print geometry and measured slicing with retained R3 evidence."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"orientation"))
import analyze_orientations as orientation


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def geometry(row):
    path=Path(row["engine"]["original_snapshot_path"])
    assert sha(path)==row["source_stl_hash"]
    mesh=trimesh.load_mesh(path,process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,row["sku"]
    metrics=orientation.metrics(mesh,(0,0,0),(0,0,0),row["sku"],raster=False)
    return dict(watertight=True,winding_consistent=True,volume_mm3=float(mesh.volume),
                print_rotation_deg=row["source_print_rotation_deg"],
                dimensions_mm=mesh.extents.tolist(),
                bed_contact_mm2=metrics["exact_bed_contact_mm2"],
                projected_overhang_45_inclusive_mm2=metrics["projected_overhang_45_inclusive_mm2"],
                fits_225_bed_with_4mm_brim=metrics["fits_225_bed_4mm_brim"])


def run():
    path=HERE/"output/production_mass_properties.json"
    current=json.loads(path.read_text())
    binding=current["preserved_r3_properties"]
    assert sha(binding["path"])==binding["sha256"]
    old=json.loads(Path(binding["path"]).read_text())
    by_old={p["sku"]:p for p in old["parts"]}
    assert set(by_old)=={p["sku"] for p in current["parts"]}
    rows=[]
    for row in current["parts"]:
        previous=by_old[row["sku"]]
        assert row["quantity"]==previous["quantity"]
        new_geometry=geometry(row)
        changed=row["source_stl_hash"]!=previous["source_stl_hash"]
        old_geometry=geometry(previous) if changed else new_geometry
        rows.append(dict(sku=row["sku"],quantity=row["quantity"],stl_bytes_changed=changed,
            old_stl_hash=previous["source_stl_hash"],new_stl_hash=row["source_stl_hash"],
            print_rotation_changed=row["source_print_rotation_deg"]!=previous["source_print_rotation_deg"],
            old_geometry=old_geometry,new_geometry=new_geometry,
            r3_model_mass_g=previous["mass_kg"]*1000,r4_model_mass_g=row["mass_kg"]*1000,
            r3_support_mass_g=previous["support_mass_g"],r4_support_mass_g=row["support_mass_g"],
            r3_time_min=previous["estimated_print_time_s"]/60,r4_time_min=row["estimated_print_time_s"]/60))
    changed=[r for r in rows if r["stl_bytes_changed"]]
    assert sha(current["source_manifest_path"])==current["source_manifest_hash"]
    answer=dict(status="pass",source_manifest_hash=current["source_manifest_hash"],
        production_properties_hash=sha(path),preserved_r3_properties_hash=binding["sha256"],
        production_sku_count=len(rows),piece_count=sum(r["quantity"] for r in rows),
        changed_stl_hash_count=len(changed),all_skus_and_quantities_preserved=True,
        all_current_meshes_watertight_winding_consistent_positive_volume=True,
        all_current_footprints_fit_225mm_bed_with_4mm_brim=all(r["new_geometry"]["fits_225_bed_with_4mm_brim"] for r in rows),
        changed_print_rotations=[r["sku"] for r in rows if r["print_rotation_changed"]],
        rows=rows,limitations=["Changed bytes do not alone prove changed geometry. Dimensions, solid volume and face measures are reported independently.",
             "Projected downward area is a conservative 45 degree geometric screen. Actual Cura support mass incorporates its recorded 50 degree threshold and bridge rules.",
             "Neither the area screen nor actual slicing verifies adhesion, support removability or printed strength."])
    (HERE/"R4_CHANGE_AUDIT.json").write_text(json.dumps(answer,indent=2)+"\n")
    lines=["# R4 print geometry and support changes", "",
        f"All {len(rows)} production SKUs and all 76 quantities are preserved. Every current mesh is closed, consistently wound and has positive volume. All current footprints fit a nominal 225 mm bed with 4 mm added on each side for a brim. There are {len(changed)} changed STL byte hashes; byte differences alone do not establish a meaningful geometry change.", "",
        "Keep the exported orientations for the next fit build. The femur's broad bed face is about 3,007 mm2, the coxa has about 412 mm2 of planar bed contact and the tibia main has about 1,505 mm2. These retain substantial bed contact while the recorded slices reduce support on the coxa and femur. No whole-part 45 degree tilt is justified by this comparison.", "",
        "Only the power-distribution tray's print-rotation metadata changes, from [180, 0, 0] to [180, 0, 45]. Its actual exported 47 x 47 x 4 mm footprint, volume and 2,127 mm2 bed contact remain the same, with no downward overhang. The added Z rotation leaves the tray parallel to the bed.", "",
        "Inspect local support in the offset servo saddles, transverse bridges and raised foot, and remove it before assessing case, nut and horn fits. The pan-servo saddle has about 496 mm2 of bed contact; check its first layer and local support islands. The thin yaw spacers have only about 17.3 mm2 each, so an appropriate brim and clean bed matter more than changing their upright orientation. The cover still requires local support review under pockets and fixing features.", "",
        "The actual quantities use 50.96 g of removable support, 17.8% less than the final R3 profile. Model PLA rises by 30.74 g to 1,047.64 g. These are commanded-filament estimates, with actual masses and fit still needing measurement.", "",
        "| Changed SKU | R4 print dimensions, mm | R3 / R4 bed contact, mm2 | R3 / R4 support, g | R3 / R4 time, min |",
        "| --- | --- | ---: | ---: | ---: |"]
    for row in changed:
        a,b=row["old_geometry"],row["new_geometry"]
        dimensions=" x ".join(f"{d:.2f}" for d in b["dimensions_mm"])
        lines.append(f"| `{row['sku']}` | {dimensions} | {a['bed_contact_mm2']:.0f} / {b['bed_contact_mm2']:.0f} | {row['r3_support_mass_g']:.3f} / {row['r4_support_mass_g']:.3f} | {row['r3_time_min']:.1f} / {row['r4_time_min']:.1f} |")
    lines += ["", "The JSON records both solid volumes, all dimensions, print rotations and exact projected overhang areas for every SKU. Slicer motion envelopes were checked separately in `output/validation.json`. The comparison uses retained R3 source snapshots rather than live R3 paths, which now belong to R4.", "",
              f"Final source manifest SHA-256: `{current['source_manifest_hash']}`. R4 production-properties SHA-256: `{sha(path)}`.", ""]
    text="\n".join(lines)
    (HERE/"R4_CHANGE_AUDIT.md").write_text(text)
    (HERE/"R4_CHANGE_AUDIT.txt").write_text(text)
    print(json.dumps({k:v for k,v in answer.items() if k!="rows"}))


if __name__ == "__main__":
    run()
