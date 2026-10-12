"""Register native atlas cells and assemble the portable review pack.

PIL/numpy are used only to inspect pixels and write JSON; raster bytes are copied
unchanged. No cel is repainted, warped, recoloured or resized here.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import numpy as np
from PIL import Image
from scipy.ndimage import label

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(mask, origin, padding=2):
    yy, xx = np.where(mask)
    if not len(xx):
        raise ValueError("Atlas contains an empty component region")
    x0, y0 = max(0, int(xx.min()) - padding), max(0, int(yy.min()) - padding)
    x1, y1 = min(mask.shape[1], int(xx.max()) + 1 + padding), min(mask.shape[0], int(yy.max()) + 1 + padding)
    rect = [x0 + origin[0], y0 + origin[1], x1-x0, y1-y0]
    anchor = [origin[0] + (int(xx.min())+int(xx.max())+1)/2,
              origin[1] + (int(yy.min())+int(yy.max())+1)/2]
    return rect, anchor


def eye_components(cell, origin):
    # Locate the two actual marks rather than splitting a cel at its midpoint.
    # Some native eye pairs cross that midpoint; halving there would clip a C
    # and include a sliver of its neighbour in the other eye's crop.
    labels, count = label(cell)
    areas = np.bincount(labels.ravel())[1:]
    indexes = np.argsort(areas)[-2:] + 1
    if len(indexes) != 2 or min(areas[indexes - 1]) < 12:
        raise ValueError("Eye cel does not contain two substantial native marks")
    components = [dict(zip(["rect", "anchor"], bounds(labels == i, origin))) for i in indexes]
    components.sort(key=lambda component: component["anchor"][0])
    return dict(zip(["left", "right"], components))


def register(identifier, kind, family, names):
    manifest = read(ROOT / "manifests" / (identifier + ".json"))
    path = ROOT / "images" / (identifier + ".png")
    if sha(path) != manifest["sha256"].lower() or sha(Path(manifest["generatedSource"])) != sha(path):
        raise ValueError("Native source receipt does not match: " + identifier)
    with Image.open(path) as image:
        if image.mode != "RGBA":
            raise ValueError("Native atlas must contain real alpha: " + identifier)
        pixels = np.array(image)
        width, height = image.size
    # Ignore RGB stored under zero-alpha pixels. High alpha and turquoise colour
    # define the drawn mark for bounding boxes, not a replacement image.
    foreground = (pixels[:, :, 3] > 80) & (pixels[:, :, 1] > 80) & (pixels[:, :, 2] > 80)
    frames, metrics = [], []
    for i, name in enumerate(names):
        x0, x1 = round((i % 4)*width/4), round((i % 4+1)*width/4)
        y0, y1 = round((i // 4)*height/3), round((i // 4+1)*height/3)
        cell = foreground[y0:y1, x0:x1]
        frame = {"id": name, "source": [x0, y0, x1-x0, y1-y0]}
        labels, count = label(cell)
        areas = np.bincount(labels.ravel())[1:]
        significant = int(np.sum(areas >= 12))
        metrics.append({"id": name, "inkPixels": int(cell.sum()), "significantComponents": significant})
        if not cell.any():
            raise ValueError(f"Empty atlas cel: {identifier}/{name}")
        if kind == "eyes":
            frame.update(eye_components(cell, [x0, y0]))
        else:
            frame["rect"], frame["anchor"] = bounds(cell, [x0, y0])
        frames.append(frame)
    if kind == "eyes":
        ref = frames[0]
        # One uniform family scale for every cel; no scale-to-fit blinking.
        scale = 22 / max(ref["left"]["rect"][3], ref["right"]["rect"][3])
        left_y, right_y = ref["left"]["anchor"][1], ref["right"]["anchor"][1]
        mid = (left_y+right_y)/2
        positions = {"left": [31, 25+(left_y-mid)*scale], "right": [69, 25+(right_y-mid)*scale]}
        data = {"file": "assets/"+path.name, "width": width, "height": height, "columns": 4, "rows": 3,
                "frames": frames, "scale": round(scale, 8), "positions": positions}
    else:
        max_width = max(f["rect"][2] for f in frames)
        data = {"file": "assets/"+path.name, "width": width, "height": height, "columns": 4, "rows": 3,
                "frames": frames, "scale": round(22/max_width, 8), "position": [50, 46]}
    report = {"id": identifier, "sha256": sha(path), "width": width, "height": height,
              "alphaZeroFraction": float(np.mean(pixels[:, :, 3] == 0)),
              "alphaPartialFraction": float(np.mean((pixels[:, :, 3] > 0) & (pixels[:, :, 3] < 255))),
              "frames": metrics, "registration": "Per-component translation only; fixed uniform family scale. Native art untouched."}
    (SITE / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, SITE / "assets" / path.name)
    (SITE / "prompts").mkdir(exist_ok=True)
    prompt_path = Path(manifest.get("promptFile", manifest.get("prompt", "")))
    if not prompt_path.is_absolute():
        prompt_path = ROOT / prompt_path
    (SITE / "prompts" / (identifier+".txt")).write_text(prompt_path.read_text(encoding="utf-8-sig"), encoding="utf-8", newline="\n")
    return data, report


def main():
    contract = read(ROOT / "production-contract.json")
    eyes, mouths, reports = {}, {}, []
    for family in contract["eyeAtlas"]["families"]:
        eyes[family], report = register("eyes-"+family, "eyes", family, contract["eyeAtlas"]["frames"])
        reports.append(report)
    for family in contract["mouthAtlas"]["families"]:
        mouths[family], report = register("mouths-"+family, "mouths", family, contract["mouthAtlas"]["frames"])
        reports.append(report)
    extra_assets = []
    detail_path = ROOT / "images/eyes-concerned-detail.png"
    if detail_path.exists() and (ROOT / "manifests/eyes-concerned-detail.json").exists():
        detail_manifest = read(ROOT / "manifests/eyes-concerned-detail.json")
        if sha(detail_path) != detail_manifest["sha256"].lower() or sha(Path(detail_manifest["generatedSource"])) != sha(detail_path):
            raise ValueError("Concerned detail source receipt differs")
        with Image.open(detail_path) as image:
            if image.mode != "RGBA":
                raise ValueError("Concerned detail needs genuine alpha")
            pixels = np.array(image)
            width, height = image.size
        ink = (pixels[:, :, 3] > 80) & (pixels[:, :, 1] > 80) & (pixels[:, :, 2] > 80)
        details = []
        for i, name in enumerate(["closed", "look-left", "look-right"]):
            x0, x1 = round(i*width/3), round((i+1)*width/3)
            cell = ink[:, x0:x1]
            frame = {"id": name, "file": "assets/eyes-concerned-detail.png", "width": width, "height": height,
                     "source": [x0, 0, x1-x0, height]}
            frame.update(eye_components(cell, [x0, 0]))
            details.append(frame)
        # Match the gaze target's uniformly drawn scale to the regular family.
        gaze_height = max(details[1]["left"]["rect"][3], details[1]["right"]["rect"][3])
        detail_scale = 22 / gaze_height
        for frame in details:
            frame["scale"] = detail_scale
            index = next(i for i, f in enumerate(eyes["concerned"]["frames"]) if f["id"] == frame["id"])
            eyes["concerned"]["frames"][index] = frame
        shutil.copyfile(detail_path, SITE / "assets/eyes-concerned-detail.png")
        detail_prompt = Path(detail_manifest["promptFile"])
        if not detail_prompt.is_absolute():
            detail_prompt = ROOT / detail_prompt
        (SITE / "prompts/eyes-concerned-detail.txt").write_text(detail_prompt.read_text(encoding="utf-8-sig"), encoding="utf-8", newline="\n")
        extra_assets.append("assets/eyes-concerned-detail.png")
        reports.append({"id": "eyes-concerned-detail", "sha256": sha(detail_path),
                        "width": width, "height": height, "frames": [f["id"] for f in details],
                        "replaces": "Concerned closed/look-left/look-right; superseded three cels are not played.",
                        "alphaZeroFraction": float(np.mean(pixels[:, :, 3] == 0))})
    laugh_path = ROOT / "images/eyes-laughing-detail.png"
    if laugh_path.exists() and (ROOT / "manifests/eyes-laughing-detail.json").exists():
        laugh_manifest = read(ROOT / "manifests/eyes-laughing-detail.json")
        if sha(laugh_path) != laugh_manifest["sha256"].lower() or sha(Path(laugh_manifest["generatedSource"])) != sha(laugh_path):
            raise ValueError("Laughing detail source receipt differs")
        with Image.open(laugh_path) as image:
            if image.mode != "RGBA":
                raise ValueError("Laughing detail needs genuine alpha")
            pixels = np.array(image)
            width, height = image.size
        ink = (pixels[:, :, 3] > 80) & (pixels[:, :, 1] > 80) & (pixels[:, :, 2] > 80)
        laugh_names = laugh_manifest["atlas"]["frames"]
        donors = []
        for i, name in enumerate(laugh_names):
            x0, x1 = round((i % 2)*width/2), round((i % 2+1)*width/2)
            y0, y1 = round((i // 2)*height/3), round((i // 2+1)*height/3)
            right = eye_components(ink[y0:y1, x0:x1], [x0, y0])["right"]
            donors.append((name, right))
        donor_scale = 22 / max(right["rect"][3] for _, right in donors)
        for name, right in donors:
            right.update({"file": "assets/eyes-laughing-detail.png", "width": width, "height": height, "scale": donor_scale})
            frame = next(f for f in eyes["laughing"]["frames"] if f["id"] == name)
            frame["right"] = right
        shutil.copyfile(laugh_path, SITE / "assets/eyes-laughing-detail.png")
        (SITE / "prompts/eyes-laughing-detail.txt").write_text((ROOT / laugh_manifest["promptFile"]).read_text(encoding="utf-8-sig"), encoding="utf-8", newline="\n")
        extra_assets.append("assets/eyes-laughing-detail.png")
        reports.append({"id": "eyes-laughing-detail", "sha256": sha(laugh_path), "width": width, "height": height,
                        "frames": laugh_names, "replaces": "Six right-eye shapes; original left laughing arch retained.",
                        "alphaZeroFraction": float(np.mean(pixels[:, :, 3] == 0))})
    native_sheets = len(reports)
    native_cels = 108 + sum(len(report["frames"]) for report in reports[9:])
    save(SITE / "asset-manifest.json", {"version": 1, "fps": 15, "layout": {"width": 100, "height": 64,
         "background": "#080f0d", "eyes": {"left": [31,25], "right": [69,25]}, "mouth": {"at": [50,46]}},
         "closedBridge": {"family": "attentive", "frame": "closed"}, "extraAssets": extra_assets, "download": "animation-pack.zip",
         "presets": contract["presets"], "eyes": eyes, "mouths": mouths})
    save(SITE / "face-tool.json", {"type": "function", "function": {
         "name": "set_face", "description": "Choose MIST's expression for the current conversational beat. The player handles blinking, transitions and speech timing. Hold it until the emotional intent changes.",
         "parameters": {"type": "object", "properties": {"face_id": {"type": "string", "enum": [p["id"] for p in contract["presets"]]}},
                        "required": ["face_id"], "additionalProperties": False}}})
    adapter = SITE / "speech-module" / "duplex"
    adapter.mkdir(parents=True, exist_ok=True)
    (adapter / "__init__.py").write_text("", encoding="utf-8")
    for name in ["phoneme_cues.py", "lipsync.py"]:
        shutil.copyfile(ROOT.parents[1] / "duplex" / name, adapter / name)
    for name in ["cmudict-subset.json", "CMUDICT-LICENSE.txt"]:
        shutil.copyfile(ROOT / "speech" / name, adapter.parent / name)
    save(ROOT / "qa/asset-metrics.json", {"atlases": reports, "nativeSheets": native_sheets, "nativeCels": native_cels, "componentCels": 108, "presets": 13})
    save(SITE / "pack-info.json", {"date": "2026-10-02", "presets": 13, "eyeFamilies": 6, "speechMouthFamilies": 3,
         "nativeSheets": native_sheets, "nativeCels": native_cels, "componentCels": 108, "fps": 15, "tool": "built-in image_gen",
         "rasterHandling": "Native RGBA atlases preserved. Runtime selects cells and translates separate eyes/mouths using registration metadata; it does not stretch or rotate the shapes.",
         "liveDefaultChanged": False, "qualityStatus": "Animated review pack; user style feedback pending.",
         "speechLimit": contract["speechLimit"]})
    # Git Pages normalizes text to LF. Hash the same canonical text bytes while
    # preserving all native PNG and WAV bytes.
    for path in SITE.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".txt", ".py", ".js", ".mjs", ".css", ".md", ".html"}:
            path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    paths = sorted(p.relative_to(SITE).as_posix() for p in SITE.rglob("*") if p.is_file() and p.name not in {"animations-pack.zip", "animation-pack.zip", "release.json", "atlas-review.html"})
    hashes = {name: sha(SITE/name) for name in paths}
    save(SITE / "release.json", {"files": hashes, "presets": 13, "componentCels": 108})
    paths.append("release.json")
    with zipfile.ZipFile(SITE / "animation-pack.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in paths:
            archive.write(SITE / name, name)
    paths.append("animation-pack.zip")
    save(ROOT / "package-receipt.json", {"publicFiles": paths, "files": hashes,
         "zipSha256": sha(SITE/"animation-pack.zip"), "zipBytes": (SITE/"animation-pack.zip").stat().st_size,
         "presets": 13, "componentCels": 108})
    print(json.dumps({"presets": 13, "atlases": native_sheets, "componentCels": 108, "files": len(paths)}))


if __name__ == "__main__":
    main()
