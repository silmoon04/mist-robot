"""Add a staged assembly check without repeating unchanged motion geometry."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import leg
from check_r4_staged_nuts import run_staged_nuts, run_actual_washer_access


CAD = Path(__file__).resolve().parent
REPORT = CAD / "output" / "r4_leg_interface_check.json"
ADDENDUM = CAD / "output" / "r4_leg_staged_assembly_check.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hashes(names):
    return {name: sha(CAD / name) for name in names}


def main():
    original_bytes = REPORT.read_bytes()
    report = json.loads(original_bytes)
    original_sources = report["source_sha256_after"]
    if report["source_sha256_before"] != original_sources:
        raise RuntimeError("Cannot reuse motion results whose sources changed during checking")
    current_sources = hashes(original_sources)
    if current_sources != original_sources:
        raise RuntimeError("Original checker or geometry bytes changed; rerun the complete leg check")
    names = list(original_sources) + ["check_r4_staged_nuts.py", "add_r4_staged_nut_check.py"]
    before = hashes(names)
    parts = leg.build_leg()
    staged = run_staged_nuts(parts)
    actual_access = run_actual_washer_access(parts)
    after = hashes(names)
    changed = [name for name in names if before[name] != after[name]]
    critical_failures = [failure for failure in actual_access["failures"]
                         if failure.get("kind") not in ("nut_insertion", "nut_holding_tube")]
    access_errors = any("error" in failure for failure in actual_access["failures"])
    base_geometry_passed = all(report[name]["passed"] for name in
                               ("solid_checks", "motion", "connector_reserves", "retention"))
    report["original_clamp_access_diagnostic"] = (
        "The original clamp_access section used a bare screw head. Its measurements and failures are preserved. "
        "Use actual_washer_clamp_access for the planned 0.5 mm head washer stack.")
    report["actual_washer_clamp_access"] = actual_access
    report["staged_nut_assembly"] = staged
    report["fully_assembled_service_access_passed"] = actual_access["passed"]
    report["staged_assembly_passed"] = staged["passed"] and not changed
    report["corrected_screw_and_driver_access_passed"] = not critical_failures and not access_errors and not changed
    report["accepted_staged_assembly_gate_passed"] = (
        base_geometry_passed and report["staged_assembly_passed"] and
        report["corrected_screw_and_driver_access_passed"])
    report["original_complete_assembly_diagnostic_passed"] = report["passed"]
    report["original_report_path"] = str(REPORT)
    report["passed"] = report["accepted_staged_assembly_gate_passed"]
    report["top_level_passed_meaning"] = (
        "This separate addendum evaluates the verified preload procedure. "
        "The original strict complete-assembly report is preserved unchanged at original_report_path.")
    report["staged_addendum_provenance"] = dict(
        created_utc=datetime.now(timezone.utc).isoformat(),
        previous_report_sha256=hashlib.sha256(original_bytes).hexdigest(),
        source_sha256_before=before, source_sha256_after=after,
        source_files_changed=changed,
        motion_reuse_basis="Every original checker and geometry source hash still matches the completed 27-pose report",
    )
    ADDENDUM.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["R4 staged assembly addendum", "",
             "Original complete-assembly diagnostic passed: " + str(report["original_complete_assembly_diagnostic_passed"]),
             "Corrected complete-assembly service access passed: " + str(report["fully_assembled_service_access_passed"]),
             "Staged nut assembly passed: " + str(report["staged_assembly_passed"]),
             "Corrected screw and driver access passed: " + str(report["corrected_screw_and_driver_access_passed"]),
             "Accepted staged assembly gate passed: " + str(report["accepted_staged_assembly_gate_passed"]),
             "", "The planned clamp screw stack uses a 0.5 mm head washer.",
             "Raw under-head Y=16.865 mm; M3 x 35 tip Y=-18.135 mm; seated driver begins at Y=19.865 mm.",
             "", "Staged check:"]
    for key, value in staged.items():
        if key in ("scope", "counts", "procedure", "limitations"):
            lines.append("  " + key + ": " + str(value))
    lines += ["", "Corrected complete-assembly access counts: " + str(actual_access.get("counts", {})),
              "Corrected service obstructions retained:"]
    for failure in actual_access["failures"]:
        lines.append("  " + failure["tool"] + " against " + failure["part"] +
                     ": " + str(failure.get("intersection_mm3", failure.get("error"))) + " mm3")
    lines += ["", "Addendum source SHA256 before:"]
    lines += ["  " + name + ": " + value for name, value in before.items()]
    lines += ["", "Addendum source SHA256 after:"]
    lines += ["  " + name + ": " + value for name, value in after.items()]
    lines += ["", "Changed addendum sources: " + str(changed), ""]
    with ADDENDUM.with_suffix(".txt").open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print("Staged assembly", report["staged_assembly_passed"],
          "corrected screw access", report["corrected_screw_and_driver_access_passed"],
          "complete service access", report["fully_assembled_service_access_passed"],
          "accepted staged gate", report["accepted_staged_assembly_gate_passed"], flush=True)
    return 0 if report["accepted_staged_assembly_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
