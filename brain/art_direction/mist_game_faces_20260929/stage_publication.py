"""Stage only the assembled public face study route in the existing Pages clone."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
DESTINATION = ROOT.parents[2] / "output/mist-acting-pages/docs/game-face-studies"


def main() -> None:
    receipt = json.loads((ROOT / "package-receipt.json").read_text(encoding="utf-8"))
    if receipt["studies"] != 35 or receipt["faces"] != 175:
        raise ValueError("Incomplete requested study set")
    reviewed = []
    for name in ("independent_first20.json", "independent_last15.json"):
        reviewed.extend(json.loads((ROOT / "qa" / name).read_text(encoding="utf-8")))
    if len(reviewed) != 35 or len({r["id"] for r in reviewed}) != 35:
        raise ValueError("Independent review does not cover all 35 selected sheets")
    for record in reviewed:
        if record.get("passed") is not True or record.get("blockers"):
            raise ValueError(f"Unresolved image review: {record['id']}")
        if hashlib.sha256((ROOT / record["sheet"]).read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError(f"Image changed since independent review: {record['id']}")
    if (ROOT / "site/faces-pack.zip").stat().st_size >= 95_000_000:
        raise ValueError("Research pack exceeds the intended single-file upload limit")
    for name in receipt["publicFiles"]:
        source = (ROOT / "site" / name).resolve()
        target = (DESTINATION / name).resolve()
        if not source.is_relative_to((ROOT / "site").resolve()) or not target.is_relative_to(DESTINATION.resolve()):
            raise ValueError(f"Out-of-scope publication file: {name}")
        if name in receipt["files"] and hashlib.sha256(source.read_bytes()).hexdigest() != receipt["files"][name]:
            raise ValueError(f"Assembled file changed since receipt: {name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    print(json.dumps({"destination": str(DESTINATION), "publicFiles": len(receipt["publicFiles"])}))


if __name__ == "__main__":
    main()
