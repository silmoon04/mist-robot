"""Assemble a review board from the unmodified generated raster sheets."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[2]
PREVIOUS = ROOT.parent / "mist_game_faces_20260929"
SITE = ROOT / "site"
POSES = [("attentive", "Attentive", 0, 0), ("considering", "Considering", 1, 0),
         ("skeptical", "Skeptical", 2, 0), ("amused", "Amused", 0, 1),
         ("concerned", "Concerned", 1, 1)]
DIRECTIONS = [
    ("geraldine-close", "Close to your selection", "Unequal eye shapes and small, crooked mouths; the closest continuation of the selected study."),
    ("geraldine-dry", "Drier reactions", "Lower lids, narrower openings and quieter mouths. The expressions should still read without a smile."),
    ("geraldine-warm", "Warmer / more exaggerated", "An experiment with taller and flatter eye pairs and rounder contour mass. This goes further from the selected silhouettes; concern and skepticism keep small, unsmiling mouths.")
]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main():
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "sheets").mkdir(exist_ok=True)
    (SITE / "prompts").mkdir(exist_ok=True)
    replacements = {
        "index.html": [
            ("<title>MIST face studies</title>", "<title>MIST / Sweet Geraldine variations</title>"),
            ("<h1>Face studies</h1>", "<h1>Sweet Geraldine variations</h1>"),
            ('href="../game-face-references/">References', 'href="../game-face-studies/#later-alligator-sweet-geraldine">Previous studies'),
            ("Static ImageGen studies for review. Our MIST adaptations of the references, not ready animations or work by the original artists.", "Your selected study, followed by three new takes on the same five expressions. Save a face or leave a note. These are still images."),
            ("Static MIST expression studies generated with ImageGen. Review five poses per study, save individual faces and keep notes.", "Compare your selected MIST Sweet Geraldine study with three new five-expression variations.")
        ],
        "app.js": [("mist-face-notes-20260929.json", "mist-geraldine-notes-20261001.json"),
                   ("mist-face-shortlist-20260929.md", "mist-geraldine-shortlist-20261001.md")],
        "review-state.js": [("mist.generated-game-faces.20260929.v1", "mist.geraldine-variations.20261001.v1"),
                            ("mist-generated-game-faces-review", "mist-geraldine-variations-review")],
        "style.css": []
    }
    for name, edits in replacements.items():
        source = (PREVIOUS / "site" / name).read_text(encoding="utf-8-sig")
        for before, after in edits:
            if before not in source:
                raise ValueError(f"Missing expected source text in {name}: {before}")
            source = source.replace(before, after)
        (SITE / name).write_text(source, encoding="utf-8", newline="\n")

    old_catalog = read(PREVIOUS / "site/catalog.json")
    selected = next(s for s in old_catalog["studies"] if s["id"] == "later-alligator-sweet-geraldine")
    selected = dict(selected, id="geraldine-selected", displayTitle="Your selected study", category="Selected reference",
                    approach="The five faces you saved. Kept here unchanged for comparison.")
    selected["poses"] = [dict(p, id="geraldine-selected__" + key) for p, (key, _, _, _) in zip(selected["poses"], POSES)]
    studies = [selected]
    for path in [selected["sheet"], selected["prompt"]]:
        shutil.copyfile(PREVIOUS / "site" / path, SITE / path)
    reference_prompt = SITE / selected["prompt"]
    reference_prompt.write_text(reference_prompt.read_text(encoding="utf-8-sig"), encoding="utf-8", newline="\n")

    sources = []
    for identifier, title, approach in DIRECTIONS:
        manifest = read(ROOT / "manifests" / f"{identifier}.json")
        image = ROOT / "images" / f"{identifier}.png"
        with Image.open(image) as raster:
            raster.load()
            width, height = raster.size
        if digest(image) != manifest["sha256"].lower():
            raise ValueError(f"Image changed since generation receipt: {identifier}")
        source = Path(manifest["generatedSource"])
        if not source.is_file() or digest(source) != digest(image):
            raise ValueError(f"Native source bytes mismatch: {identifier}")
        prompt = ROOT / manifest.get("promptFile", manifest["prompt"])
        if not prompt.resolve().is_relative_to((ROOT / "prompts").resolve()):
            raise ValueError(f"Invalid selected prompt: {identifier}")
        shutil.copyfile(image, SITE / "sheets" / image.name)
        public_prompt = SITE / "prompts" / f"{identifier}.txt"
        public_prompt.write_text(prompt.read_text(encoding="utf-8-sig"), encoding="utf-8", newline="\n")
        studies.append({
            "id": identifier, "displayTitle": title, "category": "New variation", "approach": approach,
            "sheet": f"sheets/{identifier}.png", "prompt": f"prompts/{identifier}.txt", "width": width, "height": height,
            "poses": [{"id": identifier + "__" + key, "label": label, "column": column, "row": row}
                      for key, label, column, row in POSES],
            "sourceStudyUrl": "https://silmoon04.github.io/mist/game-face-studies/#later-alligator-sweet-geraldine",
            "referenceUrl": selected["referenceUrl"], "tool": "built-in image_gen",
            "kind": "static expression study", "limitations": manifest.get("limitations", "Static studies, not production animation assets.")
        })
        sources.append({"id": identifier, "imageSha256": digest(image), "sourcePromptSha256": digest(prompt),
                        "packPromptSha256": digest(public_prompt),
                        "width": width, "height": height})
    save_json(SITE / "catalog.json", {"version": 1, "totalFaces": 20, "newFaces": 15, "studies": studies})
    save_json(SITE / "pack-info.json", {
        "date": "2026-10-01", "newSheets": 3, "newFaces": 15, "unchangedReferenceSheets": 1,
        "tool": "built-in image_gen", "imageHandling": "Native PNG bytes preserved; the page clips cells with CSS.",
        "promptHandling": "Selected prompt text preserved with LF line endings for Git publication.",
        "status": "Static style comparison; current robot animation pack unchanged.",
        "sources": sources, "feedbackSchema": "mist-geraldine-variations-review", "feedbackVersion": 1
    })
    paths = sorted(p.relative_to(SITE).as_posix() for p in SITE.rglob("*") if p.is_file() and p.name not in {"faces-pack.zip", "release.json"})
    hashes = {name: digest(SITE / name) for name in paths}
    save_json(SITE / "release.json", {"files": hashes, "newFaces": 15, "referenceFaces": 5})
    paths.append("release.json")
    with zipfile.ZipFile(SITE / "faces-pack.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in paths:
            archive.write(SITE / name, name)
    paths.append("faces-pack.zip")
    save_json(ROOT / "package-receipt.json", {"publicFiles": paths, "files": hashes,
              "zipBytes": (SITE / "faces-pack.zip").stat().st_size,
              "zipSha256": digest(SITE / "faces-pack.zip"), "newFaces": 15, "referenceFaces": 5})
    print(json.dumps({"site": str(SITE), "files": len(paths), "newFaces": 15,
                      "zipBytes": (SITE / "faces-pack.zip").stat().st_size}))


if __name__ == "__main__":
    main()
