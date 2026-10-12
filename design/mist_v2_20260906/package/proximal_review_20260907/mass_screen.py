"""Mass inventory of the preserved 577-part checked assembly; no CAD mutations."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent.parent
REPORT = PACKAGE / "cad/leg_output_checked_20260907/leg_geometry_report.json"


def main():
    raw = REPORT.read_bytes()
    report = json.loads(raw)
    lookup = {(group, p["name"]): p for group, spec in report["specifications"].items()
              for p in spec["parts"]}
    rows = []
    totals = defaultdict(lambda: defaultdict(float))
    missing = []
    for p in report["parts"]:
        spec = lookup[(p["group"], p["name"])]
        if p["category"] == "print":
            mass = p["solid_material_mass_g"]
            basis = "fully_solid_declared_print_material"
        elif "mass_g" in spec:
            mass = spec["mass_g"]
            basis = spec.get("mass_provenance", "declared_mass")
        elif "density_g_cm3" in spec:
            mass = spec["density_g_cm3"] * p["volume_cm3"]
            basis = spec.get("mass_provenance", "solid_density_estimate")
        else:
            mass = None
            basis = "not_assigned"
            missing.append(p["assembly_name"])
        row = dict(name=p["name"], group=p["group"], category=p["category"],
                   link=p.get("link"), mass_g=mass, basis=basis,
                   volume_cm3=p["volume_cm3"],
                   bounds_partlocal_mm=p["bounds_partlocal_mm"])
        rows.append(row)
        if mass is not None:
            totals[p["group"]][p["category"]] += mass
    fl = [r for r in rows if r["group"] == "FL"]
    by_link = defaultdict(float)
    for r in fl:
        if r["mass_g"] is not None:
            by_link[r["link"]] += r["mass_g"]
    def sum_names(prefixes, category=None):
        return sum(r["mass_g"] or 0 for r in fl
                   if any(r["name"].startswith(s) for s in prefixes)
                   and (category is None or r["category"] == category))
    summary = dict(source=str(REPORT), source_sha256=hashlib.sha256(raw).hexdigest(),
                   part_count=len(rows), per_group_g=dict(totals),
                   FL_by_rigid_link_g=dict(by_link), missing_mass=missing,
                   FL_mass_groups_g={
                       "knee_input_all_K_parts_except_servo": sum_names(["K"]),
                       "knee_input_print_K_parts": sum_names(["K"],"print"),
                       "hip_servo_saddle_and_cap": sum_names(["H08", "H10"]),
                       "knee_servo_saddle_and_cap": sum_names(["K08", "K10"]),
                       "femur_cheeks": sum_names(["F01"]),
                       "tibia_cheeks": sum_names(["T02", "T03"]),
                       "wheel_cradle": sum_names(["W07"]),
                       "wheel_tire": sum_names(["W04"]),
                       "wheel_hub": sum_names(["W03"]),
                       "yaw_mount_plus_coxa": sum_names(["Y01", "P01"]),
                       "knee_608_pair": sum_names(["F06"]),
                       "remote_627_pair": sum_names(["K01"]),
                       "knee_shaft_and_inner_spacers": sum_names(["T01", "T06"]),
                   })
    (HERE / "mass_inventory.json").write_text(json.dumps(dict(summary=summary, parts=rows),indent=2)+"\n")
    print(json.dumps(summary,indent=2))
    print("FL print descending:")
    for r in sorted((r for r in fl if r["category"]=="print"),key=lambda r:r["mass_g"],reverse=True)[:18]:
        print(f"{r['mass_g']:7.2f}g {r['name']}")
    print("FL hardware descending:")
    for r in sorted((r for r in fl if r["category"]!="print" and r["mass_g"] is not None),key=lambda r:r["mass_g"],reverse=True)[:18]:
        print(f"{r['mass_g']:7.2f}g {r['name']}")


if __name__ == "__main__":
    main()
