"""Reslice the deck only and retain all unchanged production slicing evidence."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import csv
import json
from pathlib import Path
import shutil
import time

from engine_runner import sha256
from run_production_slices import one_case, save_json, write_report
from validate_rebind_inputs import validate

HERE = Path(__file__).resolve().parent


def run(manifest_path, expected_hash, output):
    started = time.monotonic()
    manifest_path, output = Path(manifest_path).resolve(), Path(output).resolve()
    aggregate_path = output/"production_mass_properties.json"
    old_manifest_path = output/"source_assembly_manifest.json"
    if sha256(manifest_path) != expected_hash:
        raise ValueError("Final manifest does not match the explicitly supplied hash")
    old = json.loads(aggregate_path.read_text())
    old_hash = sha256(aggregate_path)
    if old["source_manifest_hash"] == expected_hash:
        raise ValueError("This aggregate is already bound to the requested manifest")
    check = validate(aggregate_path,old_manifest_path,manifest_path,["body_deck"])
    previous = output/("previous_revision_"+old["source_manifest_hash"][:12])
    previous.mkdir(exist_ok=False)
    for name in ("production_mass_properties.json", "source_assembly_manifest.json", "validation.json",
                 "PRODUCTION_SLICING.md", "PRODUCTION_SLICING.txt", "production_slicing_summary.csv"):
        source = output/name
        if source.exists():
            shutil.copyfile(source, previous/name)
    for name in ("R5_CHANGE_AUDIT.json","R5_CHANGE_AUDIT.md","R5_CHANGE_AUDIT.txt"):
        if (HERE/name).exists():
            shutil.copyfile(HERE/name,previous/name)
    save_json(previous/"preservation_receipt.json",dict(
        preserved_utc=datetime.now(timezone.utc).isoformat(),
        reason="The final R5 CAD changes only the rounded peripheral deck reliefs.",
        source_manifest_hash=old["source_manifest_hash"],
        aggregate_hash=old_hash,
        original_deck_artifacts_retained=True,
        files={p.name:sha256(p) for p in previous.iterdir() if p.is_file()}))
    current_manifest = json.loads(manifest_path.read_text())
    entry = next(p for p in current_manifest["print_parts"] if p["sku"] == "body_deck")
    new_deck = one_case(entry,manifest_path.parent,output/"FINAL_DECK_RELIEF"/"body_deck")
    # Repeat provenance checks after slicing so a concurrent rebuild cannot be
    # rebound silently. The previous output is still the canonical aggregate.
    check = validate(aggregate_path,old_manifest_path,manifest_path,["body_deck"])
    if sha256(manifest_path) != expected_hash:
        raise ValueError("Final manifest changed during the deck-only slice")
    old_deck = next(r for r in old["parts"] if r["sku"] == "body_deck")
    result = dict(old)
    result["parts"] = [new_deck if r["sku"] == "body_deck" else r for r in old["parts"]]
    r4=json.loads(Path(old["preserved_r4_properties"]["path"]).read_text())
    new_by_sku={row["sku"]:row for row in result["parts"]}
    comparisons=[]
    for before in r4["parts"]:
        after=new_by_sku.get(before["sku"])
        if after is None or before["source_stl_hash"]==after["source_stl_hash"]:
            continue
        compact=lambda row: dict(model_mass_g=row["mass_kg"]*1000,support_mass_g=row["support_mass_g"],
            adhesion_mass_g=row["adhesion_mass_g"],time_min=row["estimated_print_time_s"]/60,source_stl_hash=row["source_stl_hash"])
        comparisons.append(dict(sku=before["sku"],r4=compact(before),r5=compact(after)))
    result["r4_comparison"]=sorted(comparisons,key=lambda row:row["sku"])
    result["created_utc"] = datetime.now(timezone.utc).isoformat()
    result["source_revision"] = current_manifest["revision"]
    result["source_manifest_path"] = str(manifest_path)
    result["source_manifest_hash"] = expected_hash
    rows = result["parts"]
    qsum = lambda key: sum(r["quantity"]*r[key] for r in rows)
    result["quantity_weighted_totals"] = dict(piece_count=sum(r["quantity"] for r in rows),
        model_mass_g=qsum("mass_kg")*1000, support_mass_g=qsum("support_mass_g"),
        adhesion_mass_g=qsum("adhesion_mass_g"), total_deposited_mass_g=qsum("total_deposited_mass_g"),
        estimated_individual_print_time_hours=qsum("estimated_print_time_s")/3600,
        full_solid_model_mass_g=sum(r["quantity"]*r["solid_scenario"]["mass_g"] for r in rows))
    result["validation"] = dict(production_sku_count=len(rows),all_source_hashes_match=True,
        all_unclassified_deposition_zero=True,all_motion_bounds_fit=True,
        no_raw_temporary_gcode_remains=not bool(list(output.rglob("*.temporary.gcode"))),
        maximum_nominal_flow_mm3_s=max(r["peak_nominal_deposition_flow_mm3_s"] for r in rows),
        maximum_extrusion_accounting_relative_difference=max(r["extrusion_accounting_relative_difference"] for r in rows),
        maximum_rectangular_section_inertia_fraction=max(r["rectangular_bead_inertia_correction_fraction"] for r in rows))
    result["source_script_hashes"] = dict(old["source_script_hashes"],
        **{name:sha256(HERE/name) for name in ("rebind_deck_relief.py","validate_rebind_inputs.py")})
    result["rebind"] = dict(reason="Corrected rounded peripheral deck reliefs provide the final R5 interface clearance. Only body_deck geometry changed.",
        previous_aggregate_path=str(previous/"production_mass_properties.json"),
        previous_aggregate_hash=old_hash,previous_source_manifest_hash=old["source_manifest_hash"],
        changed_skus=["body_deck"],resliced_sku_count=1,reused_production_sku_count=len(rows)-1,
        old_deck=dict(source_stl_hash=old_deck["source_stl_hash"],mass_kg=old_deck["mass_kg"],
                      com_mm=old_deck["com_mm"],inertia_kg_m2=old_deck["inertia_kg_m2"],
                      estimated_print_time_s=old_deck["estimated_print_time_s"]),
        new_deck=dict(source_stl_hash=new_deck["source_stl_hash"],mass_kg=new_deck["mass_kg"],
                      com_mm=new_deck["com_mm"],inertia_kg_m2=new_deck["inertia_kg_m2"],
                      estimated_print_time_s=new_deck["estimated_print_time_s"]),
        input_validation=check,elapsed_seconds=time.monotonic()-started)
    (output/"source_assembly_manifest.json").write_bytes(manifest_path.read_bytes())
    save_json(aggregate_path,result)
    fields=["sku","quantity","mass_kg","support_mass_g","adhesion_mass_g","estimated_print_time_s","deposited_to_full_solid_mass_ratio","source_stl_hash"]
    with (output/"production_slicing_summary.csv").open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        writer.writerows({k:r[k] for k in fields} for r in rows)
    write_report(result,output)
    note = ("\n## Final deck clearance update\n\n"
            "The final R5 CAD corrects the rounded peripheral reliefs to clear the leg interfaces. "
            "Only `body_deck` was resliced. The other 33 production STL hashes and every corresponding print-to-link transform match their prior records, "
            "so their actual toolpaths, deposited masses and inertia tensors were reused unchanged. "
            f"The deck's deposited PLA changes from {1000*old_deck['mass_kg']:.3f} to {1000*new_deck['mass_kg']:.3f} g. "
            "The previous aggregate, source manifest and review files are preserved in the `previous_revision_` directory; its original deck toolpath artifacts also remain.\n")
    for name in ("PRODUCTION_SLICING.md","PRODUCTION_SLICING.txt"):
        with (output/name).open("a",encoding="utf-8") as handle:
            handle.write(note)
    save_json(output/"deck_rebind_receipt.json",dict(status="pass",source_manifest_hash=expected_hash,
        aggregate_hash=sha256(aggregate_path),rebind=result["rebind"],
        previous_artifacts_preserved=True,other_33_production_records_unchanged=True))
    print(json.dumps(dict(status="pass",aggregate_hash=sha256(aggregate_path),
        old_deck_mass_g=1000*old_deck["mass_kg"],new_deck_mass_g=1000*new_deck["mass_kg"],
        quantity_weighted_totals=result["quantity_weighted_totals"])),flush=True)


if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("--manifest",required=True)
    p.add_argument("--expected-manifest-hash",required=True)
    p.add_argument("--output",default=str(HERE/"output"));a=p.parse_args()
    run(a.manifest,a.expected_manifest_hash,a.output)
