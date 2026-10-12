"""Slice frozen production SKUs and integrate deposited part mass properties."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
import trimesh

from deposition_properties import parse_gcode
from engine_runner import slice_one, sha256

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMPARED = ("coxa_upper_and_hip_saddle", "femur_main_and_knee_saddle", "tibia_curved_main_and_foot")


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def archive_inert(raw_path):
    path = Path(raw_path)
    text = path.read_text(encoding="utf-8")
    disabled = "; ANALYSIS EVIDENCE ONLY. EVERY MACHINE COMMAND IS DISABLED. DO NOT PRINT.\n"
    disabled += "\n".join(line if line.lstrip().startswith(";") or not line.strip() else "; DISABLED| "+line
                          for line in text.splitlines())+"\n"
    artifact = path.with_name(path.name.replace(".temporary.gcode", ".disabled.gcode.gz"))
    artifact.write_bytes(gzip.compress(disabled.encode("utf-8"),mtime=0))
    path.unlink()
    return dict(path=str(artifact), sha256=sha256(artifact),
                raw_text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                all_commands_disabled=True, raw_temporary_removed=True)


def solid_properties(path):
    mesh = trimesh.load_mesh(path, process=True)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError("Invalid closed production mesh: "+str(path))
    density = 1.24e-6
    return dict(mass_kg=float(mesh.volume*density), mass_g=float(mesh.volume*density*1000),
                com_mm=mesh.center_mass.tolist(),
                inertia_kg_m2=(mesh.moment_inertia*density*1e-6).tolist(),
                volume_mm3=float(mesh.volume), assumption="Uniform full-solid PLA at 1.24 g/cm3")


def one_case(entry, source_dir, case_dir):
    start = time.monotonic()
    path = source_dir / entry["stl"]
    expected = sha256(path)
    engine = slice_one(path, case_dir, entry["sku"])
    raw = Path(engine["raw_temporary_path"])
    try:
        deposition = parse_gcode(raw.read_text(encoding="utf-8"), engine["gcode_to_source_transform"])
        solid = solid_properties(path)
        part = deposition["properties"]["model"]
        support = deposition["properties"]["support"]
        adhesion = deposition["properties"]["adhesion"]
        parsed_volume = deposition["total_deposited_volume_mm3"]
        discrepancy = abs(parsed_volume-engine["engine_filament_volume_mm3"])/max(1., engine["engine_filament_volume_mm3"])
        allowed_discrepancy = max(.001, 1.1/max(1., engine["engine_filament_volume_mm3"]))
        if discrepancy > allowed_discrepancy:
            raise ValueError(f"Extrusion accounting differs from the engine for {entry['sku']}: {discrepancy:.4%}")
        if not deposition["unclassified_deposition_is_zero"] or part["mass_kg"] <= 0:
            raise ValueError("Missing or unclassified model deposition: "+entry["sku"])
        if sha256(path) != expected or engine["source_sha256"] != expected:
            raise ValueError("Source STL changed during slicing: "+entry["sku"])
        bounds = np.asarray(engine["source_bounds_mm"])
        if np.any(np.asarray(part["com_mm"]) < bounds[0]-.5) or np.any(np.asarray(part["com_mm"]) > bounds[1]+.5):
            raise ValueError("Deposited COM falls outside source geometry bounds: "+entry["sku"])
        peak = max(p.get("peak_nominal_deposition_flow_mm3_s",0) for p in deposition["properties"].values())
        if peak > 8.1:
            raise ValueError(f"Flow exceeds 8 mm3/s analysis limit: {entry['sku']} {peak}")
        row = dict(sku=entry["sku"], quantity=entry["quantity"], source_stl_path=str(path),
                   source_stl_hash=expected, source_print_rotation_deg=entry.get("print_rotation"),
                   mass_kg=part["mass_kg"], com_mm=part["com_mm"],
                   inertia_kg_m2=part["inertia_line_about_com_kg_m2"],
                   support_mass_g=support["mass_g"], adhesion_mass_g=adhesion["mass_g"],
                   total_deposited_mass_g=deposition["total_deposited_mass_g"],
                   estimated_print_time_s=deposition["estimated_total_print_time_s"],
                   peak_nominal_deposition_flow_mm3_s=peak,
                   solid_scenario=solid, deposited_to_full_solid_mass_ratio=part["mass_kg"]/solid["mass_kg"],
                   rectangular_bead_inertia_correction_fraction=part["rectangular_section_spectral_fraction"],
                   extrusion_accounting_relative_difference=discrepancy,
                   extrusion_accounting_tolerance=allowed_discrepancy,
                   deposition=deposition, engine=engine, status="pass")
    finally:
        inert = archive_inert(raw) if raw.exists() else None
    row["gcode_evidence"] = inert
    row["elapsed_analysis_seconds"] = time.monotonic()-start
    row["engine"]["raw_file_disposition"] = "Removed after parsing; only disabled compressed evidence remains."
    save_json(case_dir / "properties.json", row)
    print(json.dumps(dict(sku=row["sku"], model_g=round(row["mass_kg"]*1000,3),
                          support_g=round(row["support_mass_g"],3),
                          time_min=round(row["estimated_print_time_s"]/60,1))), flush=True)
    return row


def write_report(result, output):
    rows = result["parts"]
    total = result["quantity_weighted_totals"]
    lines = ["# Production slicing and deposited mass properties", "",
             f"CuraEngine sliced all {len(rows)} production SKUs, representing {total['piece_count']} printed pieces, from `{result['source_revision']}`. The robot-part PLA estimate is {total['model_mass_g']:.1f} g; removable support is {total['support_mass_g']:.1f} g and adhesion material is {total['adhesion_mass_g']:.1f} g. Printing every piece separately at the recorded profile totals {total['estimated_individual_print_time_hours']:.1f} predicted hours. A packed plate has different travel, cooling and adhesion overhead.", "",
             "Part mass, centre of mass and inertia come from each emitted model-deposition path. Support, support interfaces and skirt material stay separate. The properties use the exact supplied print-STL frame in millimetres; `mass_kg`, `com_mm` and `inertia_kg_m2` are the fields to transform into each assembly link. The inertia tensor is about the deposited part's own centre of mass.", "",
             "| SKU | Qty | Part PLA, g | Support, g | Adhesion, g | Time, min | Part / full-solid mass |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in rows:
        lines.append(f"| `{r['sku']}` | {r['quantity']} | {1000*r['mass_kg']:.3f} | {r['support_mass_g']:.3f} | {r['adhesion_mass_g']:.3f} | {r['estimated_print_time_s']/60:.1f} | {r['deposited_to_full_solid_mass_ratio']:.3f} |")
    lines.extend(["", "## Profile and validation", "",
                  "The numeric profile uses a 0.4 mm nozzle, 0.20 mm layers, 0.42 mm nominal line width, five walls, six top and bottom layers, 35% gyroid, 210/60 C PLA, and an 8 mm3/s flow ceiling. Support is normal zigzag at 15%, with a 60% roof, 0.6 mm roof thickness, 0.2 mm Z separation and 0.5 mm XY clearance. All resolved settings and source hashes accompany the individual cases. It is an analysis profile, not measured printer calibration.", "",
                  f"All slice motions fit the recorded 225 x 225 x 265 mm envelope. Peak nominal deposition flow was {result['validation']['maximum_nominal_flow_mm3_s']:.3f} mm3/s. The maximum relative difference between integrated E volume and Cura's rounded volume was {100*result['validation']['maximum_extrusion_accounting_relative_difference']:.4f}%. Small parts allow for the integer-rounded engine volume. No deposition remained unclassified.", "",
                  "The parser accounts for absolute and relative E, G92 resets, G90/G91 coordinate modes, and retraction repayment. It rejects unsupported arcs, volumetric extrusion or moving-Z deposition. Mode behavior follows the [Marlin M82 documentation](https://marlinfw.org/docs/gcode/M082.html) and [G92 documentation](https://marlinfw.org/docs/gcode/G092.html). Eight analytic/parser tests and the independent R2 toolpath review are saved alongside the pipeline.", "",
                  "The engine uses explicit placement with automatic centering disabled. Each case records the original STL to G-code transform and its inverse, including nonzero mesh minima. Engine coordinates are quantized to 0.001 mm; float32 export and vertex rounding errors are also recorded.", "",
                  "## Mass and inertia model", "",
                  "For each fresh deposited filament length E, the volume is `E * pi * 1.75^2 / 4`. Multiplying by the nominal 1.24 g/cm3 density gives mass. The bead centre lies half a layer below the commanded nozzle Z. A line segment from p to q has midpoint c and central second moment `m * ((c-C)(c-C)^T + (q-p)(q-p)^T / 12)`, where C is the complete part COM. Summed second moments yield `I = trace(Q) * identity - Q`. Millimetres are converted to metres in the returned inertia tensor.", "",
                  f"An additional rectangular bead model infers cross-section width from emitted volume divided by path length and layer height. Its largest spectral inertia correction was {100*result['validation']['maximum_rectangular_section_inertia_fraction']:.4f}% among these SKUs. This quantifies one geometric approximation; actual bead shape, pressure, corner overlap, shrinkage and density remain unmeasured. No single infill multiplier is applied to CAD mass or inertia.", "",
                  "The uniform full-solid PLA mass, COM and inertia remain in every case as a separate comparison scenario. Neither scenario establishes printed strength. Actual part masses should replace these estimates after printing, while placement and joint loads need separate mechanical checks.", "",
                  "Per-category deposition path times omit acceleration, travel and cooling. Use only the total Cura slice time for print scheduling. All retained G-code commands are disabled and compressed; there are no machine-ready toolpaths in this analysis output.", "",
                  "## R2 comparison of integrated leg parts", "",
                  "The comparison reslices the three R2 source meshes with the same explicit numeric profile. Coxa orientation and R3 geometry both change, so this measures the complete production proposal rather than geometry alone.", "",
                  "| Part | R2 / R3 model g | R2 / R3 support g | R2 / R3 minutes |", "| --- | ---: | ---: | ---: |"])
    for c in result["r2_comparison"]:
        a,b = c["r2"],c["r3"]
        lines.append(f"| `{c['sku']}` | {a['model_mass_g']:.2f} / {b['model_mass_g']:.2f} | {a['support_mass_g']:.2f} / {b['support_mass_g']:.2f} | {a['time_min']:.1f} / {b['time_min']:.1f} |")
    lines.extend(["", f"Source manifest SHA-256: `{result['source_manifest_hash']}`. Source meshes were checked again after the batch. These results apply to those bytes; changes to geometry, orientation or slicing settings require a new run.", ""])
    text = "\n".join(lines)
    (output/"PRODUCTION_SLICING.md").write_text(text,encoding="utf-8")
    (output/"PRODUCTION_SLICING.txt").write_text(text,encoding="utf-8")


def run(manifest_path, output, expected_hash=None, baseline_path=None):
    start = time.monotonic()
    manifest_path, output = Path(manifest_path).resolve(), Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    manifest_hash = sha256(manifest_path)
    if expected_hash and manifest_hash != expected_hash:
        raise ValueError("The manifest is not the explicitly frozen source")
    manifest = json.loads(manifest_path.read_text())
    entries = manifest["print_parts"]
    if not entries or len({e["sku"] for e in entries}) != len(entries):
        raise ValueError("Expected distinct nonempty production SKUs")
    source_dir = manifest_path.parent
    sources = {e["sku"]:sha256(source_dir/e["stl"]) for e in entries}
    (output/"source_assembly_manifest.json").write_bytes(manifest_path.read_bytes())
    rows, errors = [], []
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {pool.submit(one_case,e,source_dir,output/"ANALYSIS_ONLY"/e["sku"]):e["sku"] for e in entries}
        for future in as_completed(jobs):
            try:
                rows.append(future.result())
            except Exception as error:
                errors.append(dict(sku=jobs[future],error=repr(error)))
                print("FAILED",jobs[future],repr(error),flush=True)
    if errors:
        save_json(output/"failed_batch.json",dict(source_manifest_hash=manifest_hash,errors=errors,completed_skus=[r["sku"] for r in rows]))
        raise RuntimeError("Some production SKUs failed; see failed_batch.json")
    by_sku = {r["sku"]:r for r in rows}
    rows = [by_sku[e["sku"]] for e in entries]
    comparisons = []
    if baseline_path:
        baseline_path = Path(baseline_path).resolve()
        old = json.loads(baseline_path.read_text())
        selected = [e for e in old["print_parts"] if e["sku"] in COMPARED]
        with ThreadPoolExecutor(max_workers=2) as pool:
            old_jobs = {pool.submit(one_case,e,baseline_path.parent,output/"R2_COMPARISON_ONLY"/e["sku"]):e["sku"] for e in selected}
            for future in as_completed(old_jobs):
                old_row = future.result()
                new_row = by_sku[old_row["sku"]]
                compact = lambda r: dict(model_mass_g=r["mass_kg"]*1000,support_mass_g=r["support_mass_g"],
                    adhesion_mass_g=r["adhesion_mass_g"],time_min=r["estimated_print_time_s"]/60,source_stl_hash=r["source_stl_hash"])
                comparisons.append(dict(sku=old_row["sku"],r2=compact(old_row),r3=compact(new_row)))
    if sha256(manifest_path) != manifest_hash:
        raise ValueError("Source manifest changed during the batch")
    for entry in entries:
        if sha256(source_dir/entry["stl"]) != sources[entry["sku"]]:
            raise ValueError("Source STL changed during the batch: "+entry["sku"])
    qsum = lambda field: sum(r["quantity"]*r[field] for r in rows)
    total = dict(piece_count=sum(r["quantity"] for r in rows),model_mass_g=qsum("mass_kg")*1000,
                 support_mass_g=qsum("support_mass_g"),adhesion_mass_g=qsum("adhesion_mass_g"),
                 total_deposited_mass_g=qsum("total_deposited_mass_g"),
                 estimated_individual_print_time_hours=qsum("estimated_print_time_s")/3600,
                 full_solid_model_mass_g=sum(r["quantity"]*r["solid_scenario"]["mass_g"] for r in rows))
    result = dict(status="pass",created_utc=datetime.now(timezone.utc).isoformat(),source_revision=manifest["revision"],
        source_manifest_path=str(manifest_path),source_manifest_hash=manifest_hash,
        coordinate_convention="Each part uses its exact supplied print-STL frame; com_mm is in mm, inertia_kg_m2 is about its own COM.",
        source_script_hashes={name:sha256(HERE/name) for name in ("run_production_slices.py","deposition_properties.py","engine_runner.py")},
        quantity_weighted_totals=total, parts=rows,r2_comparison=sorted(comparisons,key=lambda c:c["sku"]),
        validation=dict(production_sku_count=len(rows),all_source_hashes_match=True,
            all_unclassified_deposition_zero=True,all_motion_bounds_fit=True,
            no_raw_temporary_gcode_remains=not bool(list(output.rglob("*.temporary.gcode"))),
            maximum_nominal_flow_mm3_s=max(r["peak_nominal_deposition_flow_mm3_s"] for r in rows),
            maximum_extrusion_accounting_relative_difference=max(r["extrusion_accounting_relative_difference"] for r in rows),
            maximum_rectangular_section_inertia_fraction=max(r["rectangular_bead_inertia_correction_fraction"] for r in rows)),
        elapsed_analysis_seconds=time.monotonic()-start)
    save_json(output/"production_mass_properties.json",result)
    with (output/"production_slicing_summary.csv").open("w",newline="",encoding="utf-8") as handle:
        fields=["sku","quantity","mass_kg","support_mass_g","adhesion_mass_g","estimated_print_time_s","deposited_to_full_solid_mass_ratio","source_stl_hash"]
        writer=csv.DictWriter(handle,fieldnames=fields); writer.writeheader()
        writer.writerows({k:r[k] for k in fields} for r in rows)
    write_report(result,output)
    print("COMPLETE",json.dumps(total),flush=True)
    return result


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",required=True)
    parser.add_argument("--expected-manifest-hash")
    parser.add_argument("--output",default=str(HERE/"output"))
    parser.add_argument("--baseline-manifest",default=str(HERE/"R2_SOURCE_SNAPSHOTS/assembly_manifest.json"))
    args=parser.parse_args()
    run(args.manifest,args.output,args.expected_manifest_hash,args.baseline_manifest)
