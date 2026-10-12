"""Validate or stage the MIST motion gallery and its downloadable asset pack.

The default is read-only. --stage preserves the verified previous public gallery
before changing its route in the deployment checkout. This script never pushes.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import zipfile

from PIL import Image

PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / "brain/art_direction/artist_studio_20260916/reuse/mist_motion_v3"
DOCS = PROJECT / "output/mist-acting-pages/docs"
DEST = DOCS / "acting-animations"
HISTORY = DOCS / "acting-animations-v2"
PUBLIC_URL = "https://silmoon04.github.io/mist/acting-animations/"
PACK = "MIST_motion_v3.zip"
UI_FILES = {"index.html", "style.css", "app.js", "runtime.js", "review-state.js"}
DOC_FILES = {"README.md", "AGENT_GUIDE.md", "PUBLIC_PROMPTS.md", "public_provenance.json", "REVIEW.md"}
TEXT_EXTENSIONS = {".html", ".css", ".js", ".json", ".txt", ".md", ".svg"}
ASSET_EXTENSIONS = {".png", ".webp", ".jpg", ".gif", ".svg"}
ASSET_ROOTS = {"frames", "layers", "blinks", "blink-layers", "components", "contact", "previews", "source", "sources"}
FORBIDDEN = re.compile(r"(?i)(?:[A-Z]:[\\/]+Users[\\/]+|127\.0\.0\.1|localhost|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{24,})")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_path(root: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    if not name or "\\" in name or ":" in name or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe public path: {name!r}")
    result = (root / relative).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError(f"Public path escapes its directory: {name!r}")
    return result


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def record_assets(value: object):
    """Only accept explicit manifest file records, never copy whole directories."""
    if isinstance(value, dict):
        if isinstance(value.get("file"), str):
            yield value["file"], value.get("sha256")
        if isinstance(value.get("sheet"), str):
            yield value["sheet"], value.get("sourceSha256")
        for child in value.values():
            yield from record_assets(child)
    elif isinstance(value, list):
        for child in value:
            yield from record_assets(child)


def verified_asset(name: str, expected: str | None) -> bytes:
    relative = PurePosixPath(name)
    if relative.parts[0] not in ASSET_ROOTS or relative.suffix.lower() not in ASSET_EXTENSIONS:
        raise ValueError(f"Unexpected manifest asset kind: {name}")
    data = checked_path(SOURCE, name).read_bytes()
    if not expected or sha(data) != expected:
        raise ValueError(f"Missing or incorrect asset hash: {name}")
    return data


def validate_frames(examples: list[dict]) -> None:
    if len(examples) != 18 or len({x["key"] for x in examples}) != 18:
        raise ValueError("Expected the 18 distinct acting IDs.")
    original = read_json(SOURCE.parent / "acting_studies_v1/catalog.json")
    expected = {f"{group['id']}/{example['id']}" for group in original["groups"] for example in group["examples"]}
    if {x["key"] for x in examples} != expected:
        raise ValueError("Acting IDs changed; saved selections must remain compatible.")
    for example in examples:
        if len(example["frames"]) != 12 or (example.get("width"), example.get("height")) != (512, 320):
            raise ValueError(f"Expected twelve poses on the common rig: {example['key']}")
        if not example.get("blinkFrames"):
            raise ValueError(f"Missing independent blink: {example['key']}")
        for kind in ("frames", "blinkFrames"):
            for index, frame in enumerate(example[kind]):
                if frame.get("index", index) != index:
                    raise ValueError(f"Frame order mismatch: {example['key']} {kind}")
                duration = frame.get("durationMs")
                if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
                    raise ValueError(f"Invalid exposure duration: {frame.get('file')}")
                if "exposureTicks" in frame and (frame["exposureTicks"] <= 0 or abs(duration - frame["exposureTicks"] * 1000 / 15) > 0.1):
                    raise ValueError(f"Exposure duration does not match 15 fps ticks: {frame.get('file')}")
                if set(frame.get("layers", {})) != {"leftEye", "rightEye", "mouth"}:
                    raise ValueError(f"Missing independently addressable layer: {frame.get('file')}")
                for record in [frame, *frame["layers"].values()]:
                    data = verified_asset(record["file"], record.get("sha256"))
                    expected_size = (512, 320) if record is frame else (record["width"], record["height"])
                    if record is not frame:
                        x, y = record["x"], record["y"]
                        width, height = expected_size
                        if any(not isinstance(value, int) for value in (x, y, width, height)) or min(x, y) < 0 or min(width, height) < 1 or x + width > 512 or y + height > 320:
                            raise ValueError(f"Layer bounds escape the common rig: {record['file']}")
                    with Image.open(io.BytesIO(data)) as image:
                        if image.size != expected_size or image.mode != "RGBA":
                            raise ValueError(f"Common transparent canvas mismatch: {record['file']}")


def payload() -> tuple[dict[str, bytes], dict]:
    manifest_bytes = (SOURCE / "manifest.json").read_bytes()
    manifest_sha = sha(manifest_bytes)
    manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    checks = read_json(SOURCE / "asset_checks.json")
    if not manifest.get("complete") or not checks.get("passed") or manifest.get("fps") != 15:
        raise ValueError("Manifest must be complete at 15 fps, with passing asset checks.")
    examples = [example for group in manifest["groups"] for example in group["examples"]]
    validate_frames(examples)
    provenance = read_json(SOURCE / "public_provenance.json")
    if provenance.get("manifestSha256") != manifest_sha:
        raise ValueError("Public provenance was built against a different manifest.")
    result = {name: checked_path(SOURCE, name).read_bytes() for name in UI_FILES | DOC_FILES}
    result["manifest.json"] = manifest_bytes
    records = list(record_assets(manifest))
    asset_hashes = {}
    for name, expected in records:
        if expected:
            if name in asset_hashes and asset_hashes[name] != expected:
                raise ValueError(f"Conflicting manifest hashes: {name}")
            asset_hashes[name] = expected
    # Conceptual pose buttons repeat a frame's path without another hash; the
    # authoritative frame or publicAssets record must still supply that hash.
    for name, expected in records:
        if name not in result:
            result[name] = verified_asset(name, expected or asset_hashes.get(name))
    preview_receipt = read_json(SOURCE / "previews/receipt.json")
    if preview_receipt.get("manifestSha256") != manifest_sha:
        raise ValueError("Previews were built against a different manifest.")
    for record in preview_receipt["outputs"]:
        result[record["file"]] = verified_asset(record["file"], record["sha256"])
    result["previews/receipt.json"] = json_bytes(preview_receipt)
    result["previews/README.md"] = (SOURCE / "previews/README.md").read_bytes()
    # These public documents are named explicitly, never inferred from a folder.
    for optional in ("transition_plans.json", "provenance.json", "animation_catalog.json"):
        path = SOURCE / optional
        if path.is_file():
            result[optional] = path.read_bytes()
    for name, data in result.items():
        if PurePosixPath(name).suffix in TEXT_EXTENSIONS:
            if FORBIDDEN.search(data.decode("utf-8-sig")):
                raise ValueError(f"Private path, local endpoint or credential pattern in {name}")
            # Match the repository's LF attributes before receipts and ZIP hashes.
            if b"\r\n" in data:
                if name in asset_hashes:
                    raise ValueError(f"Normalize the hashed text asset before compiling: {name}")
                result[name] = data.replace(b"\r\n", b"\n")
    archive_payload = dict(result)
    archive_payload["index.html"] = archive_payload["index.html"].replace(b'href="../acting-review/"', b'href="https://silmoon04.github.io/mist/acting-review/"')
    archive_payload["index.html"] = archive_payload["index.html"].replace(b'href="../acting-animations-v2/"', b'href="https://silmoon04.github.io/mist/acting-animations-v2/"')
    archive_payload["index.html"] = archive_payload["index.html"].replace(b'href="../"', b'href="https://silmoon04.github.io/mist/"')
    archive_payload["index.html"] = archive_payload["index.html"].replace(b'href="MIST_motion_v3.zip"', b'href="https://silmoon04.github.io/mist/acting-animations/MIST_motion_v3.zip"')
    archive_payload["pack_manifest.json"] = json_bytes({name: sha(data) for name, data in sorted(archive_payload.items())})
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(archive_payload.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 29, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    with zipfile.ZipFile(io.BytesIO(memory.getvalue())) as archive:
        if archive.testzip() is not None or any(archive.read(name) != data for name, data in archive_payload.items()):
            raise ValueError("Asset pack round-trip failed.")
    receipt = {"version": 3, "url": PUBLIC_URL, "examples": 18, "composedActingPoses": 216,
               "blinkPoses": sum(len(x["blinkFrames"]) for x in examples),
               "timing": "15 fps timebase with authored exposure durations; blink timelines are separate",
               "generation": "Reusable original MIST components and selected ImageGen component drawings; composed poses are not independent ImageGen generations",
               "files": {name: {"bytes": len(data), "sha256": sha(data)} for name, data in sorted(result.items())},
               "archive": {"file": PACK, "bytes": len(memory.getvalue()), "sha256": sha(memory.getvalue())}}
    result[PACK] = memory.getvalue()
    result["publication.json"] = json_bytes(receipt)
    if sha((SOURCE / "manifest.json").read_bytes()) != manifest_sha:
        raise ValueError("Composition manifest changed during packaging; retry after the composer finishes.")
    return result, receipt


def publication_payload(directory: Path) -> dict[str, bytes]:
    receipt = read_json(directory / "publication.json")
    records = dict(receipt["files"])
    records[receipt["archive"]["file"]] = receipt["archive"]
    result = {}
    for name, record in records.items():
        data = checked_path(directory, name).read_bytes()
        if sha(data) != record["sha256"] or len(data) != record["bytes"]:
            raise ValueError(f"Previously published file changed: {name}")
        result[name] = data
    result["publication.json"] = (directory / "publication.json").read_bytes()
    return result


def actual_files(directory: Path) -> set[str]:
    return {path.relative_to(directory).as_posix() for path in directory.rglob("*") if path.is_file()}


def write_payload(directory: Path, files: dict[str, bytes]) -> None:
    for name, data in files.items():
        target = checked_path(directory, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def stage(files: dict[str, bytes]) -> None:
    if not DEST.resolve().is_relative_to(DOCS.resolve()) or not HISTORY.resolve().is_relative_to(DOCS.resolve()):
        raise ValueError("Deployment paths must stay within the named docs directory.")
    old = publication_payload(DEST)
    extras = actual_files(DEST) - set(old)
    if extras:
        raise ValueError(f"Unknown current public files; leaving them untouched: {sorted(extras)}")
    old_receipt = read_json(DEST / "publication.json")
    if old_receipt.get("version") != 3:
        if HISTORY.exists():
            historical = publication_payload(HISTORY)
            if historical != old or actual_files(HISTORY) != set(historical):
                raise ValueError("Existing v2 history differs from the current v2 route.")
        else:
            write_payload(HISTORY, old)
        if publication_payload(HISTORY) != old:
            raise ValueError("V2 history copy did not verify; current route was not changed.")
    elif not (HISTORY / "publication.json").is_file():
        raise ValueError("A v3 route must retain the v2 historical publication.")
    # Delete only files recorded by the previous publication after verifying its
    # history. This never removes an unlisted file or a directory recursively.
    for name in set(old) - set(files):
        checked_path(DEST, name).unlink()
    write_payload(DEST, files)
    if actual_files(DEST) != set(files) or any(checked_path(DEST, name).read_bytes() != data for name, data in files.items()):
        raise ValueError("Staged publication differs from its validated payload.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", action="store_true", help="preserve v2 and stage validated v3 files in the existing deployment checkout")
    args = parser.parse_args()
    files, receipt = payload()
    if args.stage:
        stage(files)
    print(json.dumps({"mode": "staged" if args.stage else "validated without changing deployment files",
                      "url": PUBLIC_URL, "files": len(files), "examples": receipt["examples"],
                      "composedActingPoses": receipt["composedActingPoses"], "blinkPoses": receipt["blinkPoses"],
                      "archiveBytes": receipt["archive"]["bytes"]}))


if __name__ == "__main__":
    main()
