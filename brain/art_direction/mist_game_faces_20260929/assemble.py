"""Assemble original ImageGen sheets into a review site without altering artwork."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
SOURCE = ROOT.parent / "game_face_research_20260929/board/catalog.json"
POSES = [("attentive", "Attentive", 0, 0), ("considering", "Considering", 1, 0),
         ("skeptical", "Skeptical", 2, 0), ("amused", "Amused", 0, 1),
         ("concerned", "Concerned", 1, 1)]
UI_FILES = ["index.html", "style.css", "app.js", "review-state.js"]


def write_json(path: Path, value: object) -> None:
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode())


def local_file(value: str, folder: str) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_relative_to((ROOT / folder).resolve()) or not path.is_file():
        raise ValueError(f"Invalid {folder} artifact: {value}")
    return path


def main() -> None:
    references = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = {}
    for manifest in sorted((ROOT / "manifests").glob("group*.json")):
        entries = json.loads(manifest.read_text(encoding="utf-8-sig"))
        if not isinstance(entries, list):
            raise ValueError(f"Expected record array: {manifest.name}")
        for entry in entries:
            if entry["id"] in records:
                raise ValueError(f"Duplicate generated study: {entry['id']}")
            records[entry["id"]] = entry
    missing = {entry["id"] for entry in references} - records.keys()
    extra = records.keys() - {entry["id"] for entry in references}
    if missing or extra:
        raise ValueError(f"Incomplete study set. Missing: {sorted(missing)}; extra: {sorted(extra)}")
    SITE.mkdir(exist_ok=True)
    (SITE / "sheets").mkdir(exist_ok=True)
    (SITE / "prompts").mkdir(exist_ok=True)
    public_files, studies, hashes = [], [], {}
    for reference in references:
        record = records[reference["id"]]
        if record.get("tool") != "built-in image_gen" or len(record.get("poses", [])) != 5:
            raise ValueError(f"Missing built-in provenance or five poses: {record['id']}")
        required = ["fiveFaces", "blankSixthCell", "mistIdentity", "emotionContrast"]
        if not all(record.get("qa", {}).get(key) is True for key in required):
            raise ValueError(f"Unresolved generator review: {record['id']}")
        sheet = local_file(record["sheet"], "sheets")
        prompt = local_file(record["prompt"], "prompts")
        with Image.open(sheet) as image:
            image.verify()
        with Image.open(sheet) as image:
            width, height = image.size
        for path in (sheet, prompt):
            rel = path.relative_to(ROOT).as_posix()
            if path.suffix == ".txt":
                (SITE / rel).write_bytes((path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").rstrip("\n") + "\n").encode())
            else:
                shutil.copyfile(path, SITE / rel)
            public_files.append(rel)
            hashes[rel] = hashlib.sha256((SITE / rel).read_bytes()).hexdigest()
        studies.append({"id": record["id"], "displayTitle": reference.get("displayTitle", reference["title"]),
                        "category": reference["category"], "approach": record["approach"],
                        "sheet": sheet.relative_to(ROOT).as_posix(), "prompt": prompt.relative_to(ROOT).as_posix(),
                        "width": width, "height": height,
                        "poses": [{"id": record["id"] + "__" + key, "label": label, "column": col, "row": row}
                                  for key, label, col, row in POSES],
                        "sourceStudyUrl": "https://silmoon04.github.io/mist/game-face-references/#" + record["id"],
                        "referenceUrl": record.get("sourceStudyUrl", reference["sources"][0]["url"]),
                        "people": reference.get("people", []), "limitations": record.get("limitations", ""),
                        "tool": "built-in image_gen", "kind": "static expression study"})
    catalog = {"version": 1, "studies": studies, "totalFaces": sum(len(s["poses"]) for s in studies)}
    if len(studies) != 35 or catalog["totalFaces"] != 175:
        raise ValueError("The requested 35 studies / 175 faces are incomplete")
    write_json(SITE / "catalog.json", catalog)
    public_files.append("catalog.json")
    for path in sorted((ROOT / "prompts").glob("*.txt")):
        if not any(path.stem == study["id"] or path.stem.startswith(study["id"] + "-") or path.stem.startswith(study["id"] + ".") for study in studies):
            raise ValueError(f"Unassigned prompt file: {path.name}")
        rel = path.relative_to(ROOT).as_posix()
        if rel not in public_files:
            (SITE / rel).write_bytes((path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").rstrip("\n") + "\n").encode())
            public_files.append(rel)
    for name in UI_FILES:
        content = (ROOT / "board" / name).read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode()
        (SITE / name).write_bytes(content)
        public_files.append(name)
    readme = """# MIST game-inspired faces

175 static ImageGen face studies across all 35 inspirations from the reference board.

Each unmodified original sheet contains five poses on a 3 by 2 grid: attentive, considering, skeptical, amused and concerned. The sixth cell is empty. The review page clips the original image in CSS; it does not redraw or warp the artwork.

These are original MIST interpretations of the research, generated with the built-in image_gen tool. They are not official artwork by the referenced artists, animation frames, separated eye/mouth assets, or a replacement for the live face system. Process-only sources inform our proposed pose approach rather than establish an inspected source facial style.

Exact generation and edit prompts are in prompts/, including named attempts that were not selected. Complete selected original raster sheets are in sheets/. Source links and credited research roles are in catalog.json. Saves and notes are local to the browser; export them to share a selection.

To review locally, extract this pack and run `python -m http.server 9051` in the extracted folder. Open http://127.0.0.1:9051/ . The published route is https://silmoon04.github.io/mist/game-face-studies/
"""
    (SITE / "README.md").write_bytes(readme.encode())
    public_files.append("README.md")
    for name in public_files:
        hashes[name] = hashlib.sha256((SITE / name).read_bytes()).hexdigest()
    receipt = {"studies": 35, "faces": 175, "date": "2026-09-29", "tool": "built-in image_gen", "files": hashes}
    write_json(SITE / "release.json", receipt)
    public_files.append("release.json")
    with zipfile.ZipFile(SITE / "faces-pack.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in public_files:
            archive.write(SITE / name, arcname="mist-game-face-studies/" + name)
    write_json(ROOT / "package-receipt.json", {**receipt, "publicFiles": public_files + ["faces-pack.zip"]})
    print(json.dumps({"studies": 35, "faces": 175, "site": str(SITE), "packBytes": (SITE / "faces-pack.zip").stat().st_size}))


if __name__ == "__main__":
    main()
