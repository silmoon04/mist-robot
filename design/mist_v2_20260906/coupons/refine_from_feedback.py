"""Create a second-coupon parameter request from measured feedback.

Usage: python refine_from_feedback.py feedback.csv --out refinement_request.json
nominal_mm is the intended printed feature dimension, including an insert pilot
bore. measured_hardware_mm records the mating OD, ID, or width across flats.
Keep the print profile unchanged when testing a request. This script writes no
CAD, print bed, or production release.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys
import tempfile


FIELDS = (
    "feature_id", "interface", "nominal_mm", "cad_mm", "measured_part_mm",
    "measured_hardware_mm", "fit_result", "print_material", "layer_mm",
    "wall_count", "xy_compensation_mm", "notes",
)
FIT_RESULTS = frozenset({"slip", "loose", "tight", "failed", "not_tested"})
PROFILE_FIELDS = ("print_material", "layer_mm", "wall_count", "xy_compensation_mm")


class FeedbackError(ValueError):
    """Feedback is insufficient or invalid; no request may be written."""


def _number(value: str, field: str, row_number: int, *, positive: bool) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise FeedbackError(f"Row {row_number}: {field} needs a measurement.") from exc
    if not math.isfinite(number) or (positive and number <= 0):
        condition = "a positive finite value" if positive else "a finite value"
        raise FeedbackError(f"Row {row_number}: {field} must be {condition}.")
    return number


def parse_feedback(data: bytes) -> tuple[list[dict], list[dict]]:
    """Read complete tested rows; skip blank, unmeasured template, and not_tested rows."""
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FeedbackError("Feedback must be a UTF-8 CSV file.") from exc
    reader = csv.DictReader(io.StringIO(content, newline=""))
    if reader.fieldnames is None:
        raise FeedbackError("Feedback CSV is empty; no measurements were supplied.")
    if len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise FeedbackError("Feedback CSV contains duplicate column names.")
    missing = set(FIELDS) - set(reader.fieldnames)
    if missing:
        raise FeedbackError(f"Feedback CSV is missing columns: {', '.join(sorted(missing))}.")

    measured, ignored = [], []
    for raw in reader:
        row_number = reader.line_num
        if None in raw:
            raise FeedbackError(f"Row {row_number}: too many CSV values.")
        fields = {key: (raw.get(key) or "").strip() for key in FIELDS}
        if not any(fields.values()):
            ignored.append({"source_row": row_number, "reason": "blank"})
            continue
        fit = fields["fit_result"].lower()
        if fit == "not_tested":
            ignored.append({"source_row": row_number, "reason": "not_tested"})
            continue
        if not fit and not fields["measured_part_mm"] and not fields["measured_hardware_mm"]:
            ignored.append({"source_row": row_number, "reason": "unmeasured_template"})
            continue
        if fit not in FIT_RESULTS:
            raise FeedbackError(
                f"Row {row_number}: fit_result must be one of {', '.join(sorted(FIT_RESULTS))}."
            )
        for required in ("feature_id", "interface", "print_material"):
            if not fields[required]:
                raise FeedbackError(f"Row {row_number}: {required} is required.")
        record = dict(fields)
        for numeric in ("nominal_mm", "cad_mm", "measured_part_mm", "measured_hardware_mm", "layer_mm"):
            record[numeric] = _number(fields[numeric], numeric, row_number, positive=True)
        record["xy_compensation_mm"] = _number(
            fields["xy_compensation_mm"], "xy_compensation_mm", row_number, positive=False
        )
        walls = _number(fields["wall_count"], "wall_count", row_number, positive=True)
        if not walls.is_integer():
            raise FeedbackError(f"Row {row_number}: wall_count must be a positive integer.")
        record["wall_count"] = int(walls)
        record["fit_result"] = fit
        record["source_row"] = row_number
        record["submitted_fields"] = {key: raw.get(key) or "" for key in FIELDS}
        measured.append(record)
    if not measured:
        raise FeedbackError("No complete tested measurements found; no refinement request was created.")
    return measured, ignored


def _request_for_group(rows: list[dict]) -> dict:
    interface = rows[0]["interface"]
    is_insert = interface.lower().startswith("heat_insert_")
    slip_rows = [] if is_insert else [row for row in rows if row["fit_result"] == "slip"]
    # Stay near the design's intended dimension; do not pool errors across interfaces.
    selected = min(
        slip_rows or rows,
        key=lambda row: (
            abs(row["cad_mm"] - row["nominal_mm"]),
            abs(row["measured_part_mm"] - row["measured_hardware_mm"]),
            row["source_row"],
        ),
    )
    print_error = selected["measured_part_mm"] - selected["cad_mm"]
    if slip_rows:
        method = "confirmed_slip"
        center = selected["cad_mm"]
        target = selected["measured_part_mm"]
        reason = "Measured slip fit closest to nominal CAD dimension; ties use measured mating difference, then CSV row."
    else:
        method = "empirical_dimension_correction"
        target = selected["nominal_mm"]
        center = target - print_error
        reason = "Closest tested CAD dimension supplies the local print error; correct toward nominal_mm."
    candidates = [round(center + offset, 6) for offset in (-0.05, 0.0, 0.05)]
    if any(not math.isfinite(value) or value <= 0 for value in candidates):
        raise FeedbackError(f"Interface {interface}: corrected candidates are not positive finite dimensions.")
    if len(set(candidates)) != 3:
        raise FeedbackError(f"Interface {interface}: dimensions exceed precision for 0.05 mm candidate spacing.")
    return {
        "interface": interface,
        "nominal_mm": selected["nominal_mm"],
        "print_profile": {key: selected[key] for key in PROFILE_FIELDS},
        "selection_method": method,
        "selection_reason": reason,
        "selected_feature_id": selected["feature_id"],
        "selected_source_row": selected["source_row"],
        "center_cad_mm": round(center, 6),
        "candidate_cad_mm": candidates,
        "candidate_step_mm": 0.05,
        "basis": {
            "input_cad_mm": selected["cad_mm"],
            "measured_part_mm": selected["measured_part_mm"],
            "measured_hardware_mm": selected["measured_hardware_mm"],
            "target_part_mm": target,
            "print_error_mm": round(print_error, 6),
            "part_minus_hardware_mm": round(selected["measured_part_mm"] - selected["measured_hardware_mm"], 6),
            "fit_result": selected["fit_result"],
        },
        "validation_pending": (
            "Heat insertion and pull-out test required; cold slip does not confirm an insert joint."
            if is_insert else "Print and measure the second coupon; fit does not establish load capacity."
        ),
        "feedback": rows,
    }


def make_request(data: bytes, source_path: str) -> dict:
    measured, ignored = parse_feedback(data)
    groups: dict[tuple, list[dict]] = {}
    for row in measured:
        key = (row["interface"], row["nominal_mm"], *(row[field] for field in PROFILE_FIELDS))
        groups.setdefault(key, []).append(row)
    return {
        "schema_version": 1,
        "purpose": "second_coupon_parameter_request",
        "status": "requires_review",
        "production_release": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {"path": source_path, "sha256": hashlib.sha256(data).hexdigest()},
        "measurement_rows_used": len(measured),
        "ignored_rows": ignored,
        "rules": {
            "nominal_mm": "Intended printed feature dimension, not automatically the mating hardware dimension.",
            "grouping": ["interface", "nominal_mm", *PROFILE_FIELDS],
            "error_model": "Local additive dimension error from one measured coupon; no global hole factor.",
            "scope": "Parameter request only. Review fit purpose and print orientation before generating a second coupon bed.",
            "production": "No production geometry or release is produced.",
        },
        "interface_requests": [_request_for_group(rows) for rows in groups.values()],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feedback_csv", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    temporary = None
    try:
        if args.feedback_csv.resolve() == args.out.resolve():
            raise FeedbackError("Input feedback and output request must be different files.")
        request = make_request(args.feedback_csv.read_bytes(), str(args.feedback_csv.resolve()))
        payload = json.dumps(request, indent=2, allow_nan=False) + "\n"
        # Validate everything before creating output; replace a prior request atomically.
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=args.out.parent,
            prefix=f".{args.out.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        os.replace(temporary, args.out)
        return 0
    except (FeedbackError, OSError, csv.Error, OverflowError) as exc:
        print(f"{exc} No output was written; any existing request is unchanged.", file=sys.stderr)
        return 2
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
