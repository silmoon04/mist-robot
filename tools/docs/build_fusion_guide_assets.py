#!/usr/bin/env python3
"""Build labelled MIST Fusion concept crops and cache attributed Autodesk media.

Run from the repository root:

    python tools/docs/build_fusion_guide_assets.py

The six source posters are never modified. Generated concept crops carry an
unmissable NOT TO SCALE ribbon because their baked-in dimensions conflict with
the current MIST master dimensions. Autodesk media is downloaded from official
Help pages for non-commercial CC BY-NC-SA documentation use; provenance is
recorded in ``docs/mist/images/fusion/asset-manifest.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "mist_3d" / "mist_fusion_guide"
OUTPUT_DIR = ROOT / "docs" / "mist" / "images" / "fusion"
CONCEPT_DIR = OUTPUT_DIR / "concept"
OFFICIAL_DIR = OUTPUT_DIR / "official"


@dataclass(frozen=True)
class Crop:
    source: str
    output: str
    box: tuple[int, int, int, int]
    label: str
    note: str


CROPS = (
    Crop(
        "c9f98018-dc76-4914-9e09-42f10d75449e.png",
        "01-target-appearance.png",
        (470, 95, 855, 615),
        "AI CONCEPT · NOT TO SCALE",
        "Target appearance only; its dimensions and leg topology are not authoritative.",
    ),
    Crop(
        "688908d9-0bdb-4bbb-b650-f1a0a5254c78.png",
        "02-upper-body-concept.png",
        (436, 94, 892, 540),
        "AI CONCEPT · REBUILD FROM PARAMETERS",
        "Upper-body form reference; shell, lid, and handle dimensions remain provisional.",
    ),
    Crop(
        "23794522-88e1-4b32-8522-f36c110bb668.png",
        "03-front-module-concept.png",
        (431, 101, 872, 539),
        "AI CONCEPT · PHONE GEOMETRY DIFFERS",
        "Front composition reference; the real Mi 9 SE envelope replaces the drawn screen.",
    ),
    Crop(
        "2ee53a2c-b6a6-414f-bd26-0ddb6c07c57e.png",
        "04-leg-topology-warning.png",
        (255, 101, 615, 611),
        "AI CONCEPT · NOT THE MIST LEG",
        "The poster omits q1 and the driven wheel; use the four-component chain in the guide.",
    ),
    Crop(
        "2dc4e473-bd40-4c91-8d6c-b93aed0190e5.png",
        "05-layout-warning.png",
        (791, 113, 1182, 607),
        "AI CONCEPT · 90° PATTERN IS WRONG",
        "MIST mounts are +25°, -25°, +109°, and -109°, not four equal quadrants.",
    ),
    Crop(
        "d9363efa-0ea2-4767-89ec-a16e4b8b0fc9.png",
        "06-motion-intent.png",
        (455, 101, 964, 626),
        "AI CONCEPT · VERIFY AXES & LIMITS",
        "Motion intent only; current Fusion screenshots and master ROM values override it.",
    ),
)


OFFICIAL_ASSETS = {
    "fusion-ui-overview.png": {
        "url": "https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/images/diagram/ui-overview-apr-26.png",
        "page": "https://help.autodesk.com/view/fusion360/ENU/?guid=GS-THE-FUSION-INTERFACE",
        "caption": "Fusion desktop interface map (April 2026 documentation).",
    },
    "parameters-dialog.png": {
        "url": "https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/images/example/parameter-favorite-dialog.png",
        "page": "https://help.autodesk.com/view/fusion360/ENU/?guid=SLD-MODIFY-PARAMETERS",
        "caption": "Parameter expression and calculated-value controls.",
    },
    "fully-constrained-sketch.png": {
        "url": "https://help.autodesk.com/cloudhelp/ENU/Fusion-Sketch/images/example/constrained.png",
        "page": "https://help.autodesk.com/cloudhelp/ENU/Fusion-Sketch/files/SKT-FULLY-DEFINE-CONSTRAIN-SKETCH.htm",
        "caption": "Unconstrained versus fully constrained sketch geometry.",
    },
    "hybrid-toolbar.png": {
        "url": "https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/images/DesignTypesHybridTB.png",
        "page": "https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/DesignIntent_UM.htm",
        "caption": "Hybrid Design toolbar: modeling and assembly tools in one document.",
    },
    "assembly-toolbar.png": {
        "url": "https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/images/DesignTypesAssemblyTB.png",
        "page": "https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/DesignIntent_UM.htm",
        "caption": "Assembly Design toolbar: external-part assembly workflow.",
    },
    "joint-revolute.gif": {
        "url": "https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/images/animation/joint-revolute-create.gif",
        "page": "https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-CREATE-JOINT.htm",
        "caption": "Creating a Revolute Joint.",
    },
    "joint-origin-between-faces.gif": {
        "url": "https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/images/animation/origin-between-two-faces.gif",
        "page": "https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-JOINT-ORIGIN.htm",
        "caption": "Joint Origin centred Between Two Faces.",
    },
    "duplicate-with-joints.gif": {
        "url": "https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/images/animation/duplicate-with-joints.gif",
        "page": "https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-DUPLICATE-WITH-JOINTS.htm",
        "caption": "Duplicate With Joints workflow.",
    },
    "interference-results.png": {
        "url": "https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/images/diagram/interference-1.png",
        "page": "https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/GUID-A6629113-B137-4EDE-B3B2-C9F1F3BA83D1.htm",
        "caption": "Interference analysis result at the current pose.",
    },
    "section-analysis.gif": {
        "url": "https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/images/animation/section-analysis.gif",
        "page": "https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-SECTION-ANALYSIS.htm",
        "caption": "Section Analysis for inspecting internal packaging.",
    },
    "export-3mf-dialog.png": {
        "url": "https://help.autodesk.com/cloudhelp/ENU/Fusion-CAM/images/dialog/am-3mf-export-configuration-dialog-jun-2024.png",
        "page": "https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-3D-PRINT.htm",
        "caption": "3MF export options; 3MF preserves units unlike STL.",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def font(size: int) -> ImageFont.ImageFont:
    candidates = (
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/seguisb.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def build_crop(spec: Crop) -> dict[str, object]:
    source = SOURCE_DIR / spec.source
    if not source.exists():
        raise FileNotFoundError(source)
    with Image.open(source) as original:
        image = original.convert("RGB").crop(spec.box)

    ribbon_height = max(38, image.height // 13)
    canvas = Image.new("RGB", (image.width, image.height + ribbon_height), "#171b1c")
    canvas.paste(image, (0, ribbon_height))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, canvas.width, ribbon_height), fill="#c95618")
    draw.text((14, ribbon_height // 2), spec.label, anchor="lm", fill="#fffaf0", font=font(max(13, ribbon_height // 3)))
    canvas = ImageOps.expand(canvas, border=2, fill="#171b1c")

    output = CONCEPT_DIR / spec.output
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)
    return {
        "kind": "ai-concept-crop",
        "output": output.relative_to(ROOT).as_posix(),
        "source": source.relative_to(ROOT).as_posix(),
        "crop_box": spec.box,
        "label": spec.label,
        "note": spec.note,
        "sha256": sha256(output),
    }


def download(url: str, output: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "MIST documentation asset builder/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)


def cache_official(name: str, data: dict[str, str], refresh: bool) -> dict[str, object]:
    output = OFFICIAL_DIR / name
    if refresh or not output.exists():
        download(data["url"], output)
    return {
        "kind": "autodesk-help-media",
        "output": output.relative_to(ROOT).as_posix(),
        "source_url": data["url"],
        "source_page": data["page"],
        "caption": data["caption"],
        "license": "CC BY-NC-SA 3.0 where stated on the linked Autodesk Help page",
        "retrieved": "2026-07-12",
        "sha256": sha256(output),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="re-download Autodesk assets")
    parser.add_argument("--skip-downloads", action="store_true", help="build AI crops only")
    args = parser.parse_args()

    CONCEPT_DIR.mkdir(parents=True, exist_ok=True)
    OFFICIAL_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = [build_crop(spec) for spec in CROPS]
    if not args.skip_downloads:
        for name, data in OFFICIAL_ASSETS.items():
            manifest.append(cache_official(name, data, args.refresh))

    manifest_path = OUTPUT_DIR / "asset-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "generated": "2026-07-12",
                "notes": [
                    "AI posters are appearance references only.",
                    "Autodesk media is locally cached for this non-commercial guide with attribution.",
                    "Check the source page before reusing the guide commercially.",
                ],
                "assets": manifest,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"built {len(manifest)} assets -> {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
