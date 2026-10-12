"""Offline validator for face_assets/face_map.json (SPECS.md section 4).

Checks, all against ground-truth parsed from the repo (no network):
  - face_map.json parses and has {"version": 1, "expressions": {...}}
  - expressions keys == exactly the 20 EXPRESSIONS from extensions/robot-tools.ts
  - every entry has primary (str), alts (list[str], 0-3 items), why (str, non-trivial)
  - every primary/alt id is a real face id in face_assets/app/app_data.js faces[]
  - every primary face is talkSafe (the 4 known non-talkSafe ids are alt-only)
  - overall spread: >= 28 distinct face ids referenced (primary + alts, union)
  - semantic family sanity: primaries of the clear emotion expressions must come
    from the matching face group (happy->happy, sad->sad, angry/annoyed->angry|annoyed,
    neutral->neutral); positive expressions (love/proud/smug) must not use
    sad/angry/annoyed primaries; dark expressions (dead_inside/error/panic/suspicious)
    must not use happy primaries. Exotic expressions are otherwise unconstrained.

Exit 0 if all checks pass, exit 1 otherwise (with details printed to stdout).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FACE_MAP_PATH = REPO_ROOT / "face_assets" / "face_map.json"
APP_DATA_PATH = REPO_ROOT / "face_assets" / "app" / "app_data.js"
ROBOT_TOOLS_PATH = REPO_ROOT / "extensions" / "robot-tools.ts"

MIN_DISTINCT_FACES = 28
MAX_ALTS = 3
MIN_WHY_LEN = 15

# Semantic family constraints on PRIMARY faces (alts are judged leniently).
# Groups come from app_data.js faces[].group: angry, annoyed, happy, misc, misc_2, neutral, sad.
STRICT_FAMILY = {
    "happy": {"happy"},
    "sad": {"sad"},
    "angry": {"angry", "annoyed"},
    "annoyed": {"annoyed", "angry"},
    "neutral": {"neutral"},
}
POSITIVE_EXPRESSIONS = {"love", "proud", "smug"}       # must not read as sad/angry
NEGATIVE_GROUPS_FOR_POSITIVE = {"sad", "angry", "annoyed"}
DARK_EXPRESSIONS = {"dead_inside", "error", "panic", "suspicious"}  # must not read as happy
FORBIDDEN_GROUP_FOR_DARK = "happy"


class CheckError(Exception):
    pass


def parse_expressions(ts_path: Path) -> list[str]:
    if not ts_path.exists():
        raise CheckError(f"robot-tools.ts not found at {ts_path}")
    text = ts_path.read_text(encoding="utf-8")
    m = re.search(r"const\s+EXPRESSIONS\s*=\s*\[(.*?)\]", text, re.S)
    if not m:
        raise CheckError("could not find `const EXPRESSIONS = [...]` in robot-tools.ts")
    body = m.group(1)
    names = re.findall(r'"([^"]+)"', body)
    if not names:
        raise CheckError("EXPRESSIONS array parsed but contained no quoted strings")
    if len(names) != len(set(names)):
        dups = sorted({n for n in names if names.count(n) > 1})
        raise CheckError(f"EXPRESSIONS array contains duplicates: {dups}")
    return names


def parse_faces(app_data_path: Path) -> list[dict]:
    if not app_data_path.exists():
        raise CheckError(f"app_data.js not found at {app_data_path}")
    text = app_data_path.read_text(encoding="utf-8")
    m = re.search(r"window\.MIST_DATA\s*=\s*(\{.*\})\s*;?\s*$", text, re.S)
    if not m:
        raise CheckError("could not find `window.MIST_DATA = {...}` in app_data.js")
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise CheckError(f"app_data.js MIST_DATA is not valid JSON: {e}")
    faces = data.get("faces")
    if not isinstance(faces, list) or not faces:
        raise CheckError("app_data.js MIST_DATA has no non-empty 'faces' list")
    return faces


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        expected_expressions = parse_expressions(ROBOT_TOOLS_PATH)
    except CheckError as e:
        print(f"FATAL: {e}")
        return 1
    print(f"Parsed {len(expected_expressions)} expressions from robot-tools.ts: "
          f"{expected_expressions}")

    try:
        faces = parse_faces(APP_DATA_PATH)
    except CheckError as e:
        print(f"FATAL: {e}")
        return 1
    faces_by_id = {f["id"]: f for f in faces}
    print(f"Parsed {len(faces)} faces from app_data.js")

    if not FACE_MAP_PATH.exists():
        print(f"FATAL: {FACE_MAP_PATH} not found")
        return 1
    try:
        face_map = json.loads(FACE_MAP_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"FATAL: face_map.json is not valid JSON: {e}")
        return 1

    if face_map.get("version") != 1:
        errors.append(f"top-level 'version' should be 1, got {face_map.get('version')!r}")

    expressions = face_map.get("expressions")
    if not isinstance(expressions, dict):
        print("FATAL: face_map.json missing top-level 'expressions' object")
        return 1

    expected_set = set(expected_expressions)
    actual_set = set(expressions.keys())
    missing = expected_set - actual_set
    extra = actual_set - expected_set
    if missing:
        errors.append(f"expressions missing keys: {sorted(missing)}")
    if extra:
        errors.append(f"expressions has unexpected extra keys: {sorted(extra)}")
    if len(actual_set) != len(expected_set):
        warnings.append(
            f"expected exactly {len(expected_set)} expression keys, got {len(actual_set)}"
        )

    all_referenced: set[str] = set()

    for name in sorted(actual_set):
        entry = expressions[name]
        prefix = f"expressions.{name}"
        if not isinstance(entry, dict):
            errors.append(f"{prefix}: entry is not an object")
            continue

        primary = entry.get("primary")
        alts = entry.get("alts")
        why = entry.get("why")

        if not isinstance(primary, str) or not primary:
            errors.append(f"{prefix}.primary: missing or not a non-empty string")
            primary = None
        if alts is None:
            alts = []
        if not isinstance(alts, list) or not all(isinstance(a, str) for a in alts):
            errors.append(f"{prefix}.alts: must be a list of strings")
            alts = [a for a in (alts if isinstance(alts, list) else []) if isinstance(a, str)]
        if len(alts) > MAX_ALTS:
            errors.append(
                f"{prefix}.alts: has {len(alts)} alts, spec prefers 1-3 (max {MAX_ALTS})"
            )
        if not isinstance(why, str) or len(why.strip()) < MIN_WHY_LEN:
            errors.append(
                f"{prefix}.why: missing or too short (needs >= {MIN_WHY_LEN} chars of "
                f"concrete justification)"
            )

        if primary is not None:
            if primary not in faces_by_id:
                errors.append(f"{prefix}.primary: {primary!r} is not a real face id")
            else:
                all_referenced.add(primary)
                if not faces_by_id[primary].get("talkSafe", False):
                    errors.append(
                        f"{prefix}.primary: {primary!r} is not talkSafe "
                        f"(non-talkSafe faces must be alts only)"
                    )
                group = faces_by_id[primary].get("group", "")
                allowed = STRICT_FAMILY.get(name)
                if allowed is not None and group not in allowed:
                    errors.append(
                        f"{prefix}.primary: {primary!r} is group {group!r}, but the "
                        f"'{name}' expression requires one of {sorted(allowed)}"
                    )
                if name in POSITIVE_EXPRESSIONS and group in NEGATIVE_GROUPS_FOR_POSITIVE:
                    errors.append(
                        f"{prefix}.primary: positive expression '{name}' cannot use a "
                        f"{group!r}-family face ({primary!r})"
                    )
                if name in DARK_EXPRESSIONS and group == FORBIDDEN_GROUP_FOR_DARK:
                    errors.append(
                        f"{prefix}.primary: dark expression '{name}' cannot use a "
                        f"happy-family face ({primary!r})"
                    )

        for alt in alts:
            if alt not in faces_by_id:
                errors.append(f"{prefix}.alts: {alt!r} is not a real face id")
            else:
                all_referenced.add(alt)
            if primary is not None and alt == primary:
                warnings.append(f"{prefix}: alt {alt!r} duplicates primary")

    distinct_count = len(all_referenced)
    print(f"Distinct faces referenced (primary + alts, union): {distinct_count}")
    if distinct_count < MIN_DISTINCT_FACES:
        errors.append(
            f"only {distinct_count} distinct faces referenced overall, "
            f"need >= {MIN_DISTINCT_FACES}"
        )

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"\nFAILED with {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\nAll checks passed.")
    print(f"  expressions: {len(actual_set)}/20")
    print(f"  distinct faces referenced: {distinct_count} (>= {MIN_DISTINCT_FACES})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
