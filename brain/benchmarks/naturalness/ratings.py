"""Decode human review exports separately from automated benchmark measurements."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics


DIMENSIONS = ("understanding", "emotional_fit", "usefulness", "conversational_flow",
              "personality", "voice_quality", "speech_timing", "expressions")


def _score(value):
    if value in (None, "", "unassessable"):
        return None
    if type(value) is int and 1 <= value <= 5:
        return value
    if isinstance(value, str) and value in ("1", "2", "3", "4", "5"):
        return int(value)
    raise ValueError(f"Rating must be 1 to 5, blank or unassessable: {value!r}")


def aggregate_reviews(key: dict, rating_paths: list[Path]) -> dict:
    """Validate and decode downloaded ratings; files are sources, not proven people.

    Legacy answer keys lacking evidence_modes permit text ratings only. This fails
    closed for audio ratings until a new key supplies the recorded evidence mode.
    """
    if not key.get("pack_sha256") or not key.get("pairs"):
        raise ValueError("Answer key requires pack_sha256 and pairs")
    pairs = {}
    for pair in key["pairs"]:
        if pair["pair_id"] in pairs:
            raise ValueError("Duplicate pair ID in answer key")
        if set(pair["mapping"]) != {"A", "B"} or set(pair["mapping"].values()) != {"baseline", "candidate"}:
            raise ValueError("Invalid A/B answer mapping")
        pairs[pair["pair_id"]] = pair
    if not rating_paths:
        raise ValueError("At least one human ratings export is required")
    seen_exports, observations, sources = set(), [], []
    preferences = dict.fromkeys(("baseline", "candidate", "tie", "unclear", "unrated"), 0)
    for path in map(Path, rating_paths):
        export = json.loads(path.read_text(encoding="utf-8-sig"))
        digest = hashlib.sha256(json.dumps(export, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if digest in seen_exports:
            raise ValueError("Duplicate ratings export; refusing to count it twice")
        seen_exports.add(digest)
        if export.get("pack_sha256") != key["pack_sha256"]:
            raise ValueError("Ratings export belongs to a different review pack")
        source_id = hashlib.sha256(str(path.resolve()).encode()).hexdigest()
        seen_pairs = set()
        for row in export.get("reviews", []):
            pair_id = row.get("pair_id")
            if pair_id not in pairs:
                raise ValueError(f"Unknown review pair: {pair_id!r}")
            if pair_id in seen_pairs:
                raise ValueError(f"Duplicate pair review in one export: {pair_id}")
            seen_pairs.add(pair_id)
            pair = pairs[pair_id]
            evidence = pair.get("evidence_modes", {label: {"view_mode": "text-only", "conversation_audio": False} for label in ("A", "B")})
            expected_view = "text-only" if all(evidence[label]["view_mode"] == "text-only" for label in ("A", "B")) else "audio-available"
            if row.get("view_mode", expected_view) != expected_view:
                raise ValueError(f"Forged or mismatched pair evidence mode: {pair_id}")
            preference = row.get("preference", "")
            if preference not in ("", "A", "B", "tie", "unclear"):
                raise ValueError(f"Unknown preference: {preference!r}")
            winner = pair["mapping"].get(preference, preference or "unrated")
            preferences[winner] += 1
            decoded, missing = {}, {}
            for label in ("A", "B"):
                option = row.get("options", {}).get(label, {})
                mode = evidence[label]["view_mode"]
                if option.get("view_mode", mode) != mode:
                    raise ValueError(f"Forged or mismatched option evidence mode: {pair_id}/{label}")
                ratings = option.get("ratings", {})
                if set(ratings) - set(DIMENSIONS):
                    raise ValueError("Unknown rating dimension")
                values, absent = {}, {}
                for dimension in DIMENSIONS:
                    raw = ratings.get(dimension)
                    score = _score(raw)
                    forbidden = dimension == "expressions" or (dimension == "voice_quality" and mode != "text-and-audio") or (dimension == "speech_timing" and not evidence[label].get("conversation_audio", False))
                    if score is not None and forbidden:
                        raise ValueError(f"Unsupported {dimension} rating for {pair_id}/{label}")
                    values[dimension] = score
                    absent[dimension] = "unassessable" if raw == "unassessable" else "unrated" if score is None else "rated"
                decoded[pair["mapping"][label]] = values
                missing[pair["mapping"][label]] = absent
            observations.append({"pair_id": pair_id, "case_id": pair["case_id"], "repeat": pair["repeat"],
                                 "source_id": source_id, "preference": winner, "ratings": decoded,
                                 "rating_states": missing, "note": str(row.get("note", "")), "view_mode": expected_view})
        sources.append({"source_id": source_id, "export_sha256": digest,
                        "reviewed_pairs": len(seen_pairs), "missing_pairs": sorted(set(pairs) - seen_pairs)})
    dimension_summary = {}
    for dimension in DIMENSIONS:
        paired = [row for row in observations if all(row["ratings"][side][dimension] is not None for side in ("baseline", "candidate"))]
        deltas = [row["ratings"]["candidate"][dimension] - row["ratings"]["baseline"][dimension] for row in paired]
        dimension_summary[dimension] = {
            "paired_observations": len(paired),
            "distinct_case_repetitions": len({(row["case_id"], row["repeat"]) for row in paired}),
            "distinct_cases": len({row["case_id"] for row in paired}),
            "rater_source_files": len({row["source_id"] for row in paired}),
            "candidate_minus_baseline_mean": statistics.mean(deltas) if deltas else None,
            "candidate_minus_baseline_median": statistics.median(deltas) if deltas else None,
            "candidate_higher": sum(d > 0 for d in deltas), "equal": sum(d == 0 for d in deltas),
            "baseline_higher": sum(d < 0 for d in deltas),
            "unpaired_or_unrated_observations": len(observations) - len(paired),
        }
    return {"schema_version": 1, "kind": "human_review_summary", "pack_sha256": key["pack_sha256"],
            "rater_source_files": len(sources), "review_observations": len(observations),
            "distinct_case_repetitions": len({(row["case_id"], row["repeat"]) for row in observations}),
            "preferences": preferences, "dimensions": dimension_summary, "sources": sources,
            "observations": observations,
            "interpretation": "Descriptive paired ratings only. Files do not prove distinct raters. Repeated cases and ratings are correlated. No overall score or significance claim is calculated. Missing ratings are not zero."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", required=True, type=Path)
    parser.add_argument("--ratings", required=True, nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = aggregate_reviews(json.loads(args.key.read_text(encoding="utf-8-sig")), args.ratings)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "review_observations": result["review_observations"]}))


if __name__ == "__main__":
    main()
