"""Stage only reviewed animation concepts in the existing Pages clone."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
DESTINATION = ROOT.parents[2] / "output/mist-acting-pages/docs/animation-ideas"
REVIEWS = ["independent-presence.json", "independent-activities.json", "independent-speech-reactions.json"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    receipt = json.loads((ROOT / "package-receipt.json").read_text(encoding="utf-8"))
    contract = json.loads((ROOT / "concepts.json").read_text(encoding="utf-8"))
    if receipt["concepts"] != 12 or receipt["images"] != 36:
        raise ValueError("Incomplete concept release")
    reviews = []
    for name in REVIEWS:
        reviews.extend(json.loads((ROOT / "qa" / name).read_text(encoding="utf-8")))
    expected = {concept["id"] for concept in contract["concepts"]}
    if len(reviews) != 12 or {r["id"] for r in reviews} != expected:
        raise ValueError("Independent reviews must cover all 12 selected concepts")
    image_names = set()
    for record in reviews:
        if record.get("passed") is not True or record.get("blockers"):
            raise ValueError(f"Unresolved concept review: {record['id']}")
        if len(record["images"]) != 3:
            raise ValueError(f"Review must cover three images: {record['id']}")
        for image in record["images"]:
            path = (ROOT / image["file"]).resolve()
            if not path.is_relative_to((ROOT / "images").resolve()) or digest(path) != image["sha256"].lower():
                raise ValueError(f"Image changed since independent review: {image['file']}")
            image_names.add(image["file"])
    if len(image_names) != 36:
        raise ValueError("Independent image coverage is incomplete")
    if digest(ROOT / "site/concepts-pack.zip") != receipt["zipSha256"]:
        raise ValueError("Concept ZIP changed since release receipt")
    for name in receipt["publicFiles"]:
        source = (ROOT / "site" / name).resolve()
        destination = (DESTINATION / name).resolve()
        if not source.is_relative_to((ROOT / "site").resolve()) or not destination.is_relative_to(DESTINATION.resolve()):
            raise ValueError(f"Out-of-scope publication path: {name}")
        if name in receipt["files"] and digest(source) != receipt["files"][name]:
            raise ValueError(f"Assembled file changed since receipt: {name}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    print(json.dumps({"destination": str(DESTINATION), "publicFiles": len(receipt["publicFiles"])}))


if __name__ == "__main__":
    main()
