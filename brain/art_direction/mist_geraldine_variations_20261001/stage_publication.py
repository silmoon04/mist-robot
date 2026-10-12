"""Copy the reviewed files into this task's existing isolated Pages clone."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
DEST = ROOT.parents[2] / "output/mist-acting-pages/docs/geraldine-variations"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt = json.loads((ROOT / "package-receipt.json").read_text(encoding="utf-8"))
    review = json.loads((ROOT / "qa/independent-style-review.json").read_text(encoding="utf-8-sig"))
    expected_ids = {"geraldine-close", "geraldine-dry", "geraldine-warm"}
    if len(review["sheets"]) != 3 or {s["id"] for s in review["sheets"]} != expected_ids:
        raise ValueError("All three sheets need independent review.")
    for sheet in review["sheets"]:
        path = (ROOT / sheet["file"]).resolve()
        if not path.is_relative_to((ROOT / "images").resolve()):
            raise ValueError("Out-of-scope image review path.")
        if sheet["passed"] is not True or sheet["blockers"] or digest(path) != sheet["sha256"].lower():
            raise ValueError(f"Unreviewed or changed sheet: {sheet['id']}")
    if digest(SITE / "faces-pack.zip") != receipt["zipSha256"]:
        raise ValueError("ZIP differs from release receipt.")
    for name in receipt["publicFiles"]:
        source = (SITE / name).resolve()
        target = (DEST / name).resolve()
        if not source.is_relative_to(SITE.resolve()) or not target.is_relative_to(DEST.resolve()):
            raise ValueError("Out-of-scope publication path.")
        if name in receipt["files"] and digest(source) != receipt["files"][name]:
            raise ValueError(f"Source changed since assembly: {name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    print(json.dumps({"destination": str(DEST), "files": len(receipt["publicFiles"])}))


if __name__ == "__main__":
    main()
