"""Package the selected native concept images and their feedback page."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
UI_FILES = ["index.html", "style.css", "app.js", "review-state.js"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode())


def checked_file(value: str, directory: str) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_relative_to((ROOT / directory).resolve()) or not path.is_file():
        raise ValueError(f"Invalid {directory} asset: {value}")
    return path


def main() -> None:
    source = json.loads((ROOT / "concepts.json").read_text(encoding="utf-8"))
    concepts = source["concepts"]
    if len(concepts) != 12 or sum(len(c["poses"]) for c in concepts) != 36:
        raise ValueError("The agreed concept set is incomplete")
    SITE.mkdir(exist_ok=True)
    (SITE / "images").mkdir(exist_ok=True)
    (SITE / "prompts").mkdir(exist_ok=True)
    files, public_concepts = [], []
    for concept in concepts:
        manifest = json.loads((ROOT / "manifests" / (concept["id"] + ".json")).read_text(encoding="utf-8-sig"))
        if manifest.get("id") != concept["id"] or manifest.get("tool") != "built-in image_gen":
            raise ValueError(f"Missing built-in provenance: {concept['id']}")
        records = {item["id"]: item for item in manifest["images"]}
        if set(records) != {p["id"] for p in concept["poses"]} or len(manifest["images"]) != 3:
            raise ValueError(f"Missing or repeated key pose: {concept['id']}")
        poses = []
        for pose in concept["poses"]:
            record = records[pose["id"]]
            image_path = checked_file(record["file"], "images")
            if image_path.name != pose["filename"]:
                raise ValueError(f"Incorrect selected filename: {pose['id']}")
            prompt_path = checked_file(record["prompt"], "prompts")
            if digest(image_path) != record["sha256"].lower():
                raise ValueError(f"Image changed since generator review: {pose['id']}")
            generated_source = Path(record["generatedSource"])
            if not generated_source.is_file() or digest(generated_source) != digest(image_path):
                raise ValueError(f"Selected bytes do not match returned artifact: {pose['id']}")
            if not all(record.get("qa", {}).get(key) is True for key in ["singleFace", "mistIdentity", "noStrayMarks"]):
                raise ValueError(f"Unresolved generator review: {pose['id']}")
            with Image.open(image_path) as image:
                image.verify()
            with Image.open(image_path) as image:
                width, height = image.size
            if width != height or min(width, height) < 768:
                raise ValueError(f"Key pose must be a clear native square image: {pose['id']}")
            image_name = image_path.relative_to(ROOT).as_posix()
            prompt_name = prompt_path.relative_to(ROOT).as_posix()
            shutil.copyfile(image_path, SITE / image_name)
            (SITE / prompt_name).write_bytes((prompt_path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").rstrip("\n") + "\n").encode())
            files.extend([image_name, prompt_name])
            poses.append({**pose, "image": image_name, "prompt": prompt_name, "width": width, "height": height,
                          "limitations": record.get("limitations", "")})
        public_concepts.append({**concept, "poses": poses, "limitations": manifest.get("limitations", "")})
    public_concepts.sort(key=lambda c: c["wave"])
    catalog = {"version": 1, "count": 12, "imageCount": 36, "reviewType": source["reviewType"],
               "tool": "built-in image_gen", "concepts": public_concepts,
               "migration": {"stage": "feedback", "currentPackChanged": False, "targetFps": 15,
                             "steps": ["Choose key poses", "Draw separated eyes, mouths and in-betweens",
                                       "Test loops, transitions, speech and interruptions", "Enable one verified family with fallback"]}}
    write_json(SITE / "catalog.json", catalog)
    files.append("catalog.json")
    for name in UI_FILES:
        (SITE / name).write_bytes((ROOT / "board" / name).read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode())
        files.append(name)
    info = ("MIST animation ideas: 12 concepts, three native ImageGen key poses each.\n"
            "These are static previews, not complete animation sequences or separated production layers.\n"
            "The current face pack stays active. Proposed timing needs testing in the live renderer.\n"
            "Review locally: run python -m http.server 9052 in this folder, then open http://127.0.0.1:9052/ .\n"
            "Save idea choices and pose notes; export JSON to share feedback.\n"
            "Published review: https://silmoon04.github.io/mist/animation-ideas/\n")
    (SITE / "pack-info.txt").write_bytes(info.encode())
    files.append("pack-info.txt")
    files = sorted(set(files))
    hashes = {name: digest(SITE / name) for name in files}
    receipt = {"date": "2026-09-30", "concepts": 12, "images": 36, "tool": "built-in image_gen", "files": hashes}
    write_json(SITE / "release.json", receipt)
    files.append("release.json")
    with zipfile.ZipFile(SITE / "concepts-pack.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(SITE / name, arcname="mist-animation-ideas/" + name)
    if (SITE / "concepts-pack.zip").stat().st_size >= 95_000_000:
        raise ValueError("Concept pack is too large for intended release")
    write_json(ROOT / "package-receipt.json", {**receipt, "publicFiles": files + ["concepts-pack.zip"],
                                             "zipSha256": digest(SITE / "concepts-pack.zip")})
    print(json.dumps({"concepts": 12, "images": 36, "publicFiles": len(files) + 1,
                      "packBytes": (SITE / "concepts-pack.zip").stat().st_size}))


if __name__ == "__main__":
    main()
