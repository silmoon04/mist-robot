"""Write public provenance from the explicitly approved MIST generation records.

Private records are read without modification. Only known prompt text, relative
asset identifiers and verified hashes are exported; local tool paths are omitted.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / "brain/art_direction/artist_studio_20260916/reuse/mist_motion_v3"
PRIVATE_INPUTS = (
    "prompts/mouths/generation.json",
    "prompts/eyes/prompts.json",
    "prompts/eyes/stroke_repair.txt",
)
PARTS_PREFIX = "brain/art_direction/artist_studio_20260916/reuse/parts/"
FORBIDDEN = re.compile(r"(?i)(?:[A-Z]:[\\/]|[\\/]Users[\\/]|127\.0\.0\.1|localhost|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{24,})")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig"))


def asset_record(name: str) -> dict:
    path = (ROOT / name).resolve()
    if not path.is_relative_to(ROOT.resolve()) or "\\" in name or ":" in name:
        raise ValueError(f"Invalid source asset: {name}")
    return {"asset": name, "sha256": digest(path)}


def repository_reference(part: str) -> dict:
    if Path(part).name != part or part not in {
        "circle_gap_03.png", "angry_hook_00.png", "mouth_line_30.png",
        "mouth_smile_arc_37.png", "mouth_open_smile_filled_33.png", "mouth_frown_arc_28.png",
    }:
        raise ValueError(f"Unexpected generation reference: {part}")
    path = PROJECT / (PARTS_PREFIX + part)
    return {"repositoryAsset": PARTS_PREFIX + part, "sha256": digest(path)}


def main():
    manifest_path = ROOT / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    if not manifest.get("complete") or not manifest.get("componentsReady"):
        raise ValueError("Wait for the complete component manifest before exporting provenance.")
    private_hashes = {name: digest(ROOT / name) for name in PRIVATE_INPUTS}
    eyes = read_json("components/eyes/manifest.json")
    eye_prompts = read_json("prompts/eyes/prompts.json")
    stroke_prompt = (ROOT / PRIVATE_INPUTS[2]).read_text(encoding="utf-8-sig").strip()
    mouth_prompts = read_json("prompts/mouths/generation.json")
    if mouth_prompts.get("tool") != "built-in image_gen" or mouth_prompts.get("transparentBackground") is not True:
        raise ValueError("Unexpected mouth generation provider or transparency setting.")
    records, selected_sources, normalized_cells = [], [], []
    for family, canonical in (("round", "circle_gap_03.png"), ("hook", "angry_hook_00.png")):
        prefix = f"components/eyes/{family}"
        reference = asset_record(f"components/eyes/{family}_reference.png")
        steps = [
            ("v1", eye_prompts["initial"][family], [reference]),
            ("v2", eye_prompts["closureRepair"][family], [asset_record(prefix + "/source_v1.png")]),
            ("v3", eye_prompts["palette"], [asset_record(prefix + "/source_v2.png"), reference]),
        ]
        if family == "round":
            steps.append(("v4", stroke_prompt, [asset_record(prefix + "/source_v3.png"), reference]))
        selected = "components/eyes/" + eyes["families"][family]["selectedSource"]
        if selected != prefix + ("/source_v4.png" if family == "round" else "/source_v3.png"):
            raise ValueError("Eye source selection changed; update the documented generation chain.")
        for version, prompt, references in steps:
            output = asset_record(f"{prefix}/source_{version}.png")
            records.append({"id": f"eyes/{family}/{version}", "tool": "built-in image_gen.imagegen",
                            "transparentBackground": True, "prompt": prompt,
                            "references": references, "output": output,
                            "selectedSheet": output["asset"] == selected})
        selected_sources.append(asset_record(selected))
        normalized_cells.append({"family": f"eyes/{family}", "canonicalReference": repository_reference(canonical),
                                 "normalization": eyes["normalization"],
                                 "cells": [{**asset_record("components/eyes/" + cell["file"]),
                                            "origin": "canonical" if index == 0 else "generated",
                                            "source": "components/eyes/" + cell["source"]}
                                           for index, cell in enumerate(eyes["families"][family]["cells"])]})
    expected_mouths = {"smile", "bowl", "concern"}
    if {entry["name"] for entry in mouth_prompts["records"]} != expected_mouths:
        raise ValueError("Mouth generation families changed; review the export allowlist.")
    for entry in mouth_prompts["records"]:
        family = entry["name"]
        metadata = read_json(f"components/mouths/{family}/metadata.json")
        # The private output path is deliberately not copied or rewritten.
        # The selected immutable workspace source is verified independently.
        output = asset_record(f"components/mouths/{family}/source.png")
        references = [repository_reference(value.replace("\\", "/").rsplit("/", 1)[-1]) for value in entry["refs"]]
        records.append({"id": f"mouths/{family}/v1", "tool": "built-in image_gen.imagegen",
                        "transparentBackground": True, "prompt": entry["prompt"], "references": references,
                        "output": output, "selectedSheet": True})
        selected_sources.append(output)
        normalized_cells.append({"family": f"mouths/{family}",
                                 "normalization": metadata["registration"] + "; " + metadata["palette"],
                                 "cells": [{**asset_record(f"components/mouths/{family}/" + frame["file"]),
                                            "origin": "canonical" if frame["index"] == 0 else "generated"}
                                           for frame in metadata["frames"]]})
    cells = [cell for family in normalized_cells for cell in family["cells"]]
    origins = {kind: {cell["sha256"] for cell in cells if cell["origin"] == kind} for kind in ("generated", "canonical")}
    source_kinds = Counter(source["kind"] for source in manifest["sources"])
    examples = [example for group in manifest["groups"] for example in group["examples"]]
    value = {
        "version": 3, "manifestSha256": manifest_sha,
        "provider": "OpenAI built-in image_gen.imagegen tool",
        "description": "Original MIST components and selected generated component drawings assembled into reusable layered poses.",
        "counts": {"imageGenerationCalls": len(records), "selectedGeneratedSheets": len(selected_sources),
                   "generatedUniqueComponentCels": len(origins["generated"]),
                   "canonicalUniqueComponentCels": len(origins["canonical"]),
                   "componentCelFiles": len(cells),
                   "manifestSourceRecordsByKind": dict(source_kinds),
                   "composedActingPoses": sum(len(example["frames"]) for example in examples),
                   "composedBlinkPoses": sum(len(example["blinkFrames"]) for example in examples)},
        "counting": "Unique component cels are counted by exact PNG hash across the supplied families. Shared neutral mouths and shared closed eyes count once. These counts describe reusable drawings, not separately generated full faces. Source records in the composition manifest describe which files the composer used.",
        "normalization": "Original source sheets stay unchanged. Extracted cels use a common scale per family, fixed attachment registration and shared MIST RGB #5eeadd while retaining the generated alpha silhouettes. Canonical starting cells and one common closed-eye cell provide consistent handoffs.",
        "selectedSources": selected_sources, "components": normalized_cells, "generationRecords": records,
        "privateRecordsPreserved": True,
    }
    serialized = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if FORBIDDEN.search(serialized):
        raise ValueError("Unexpected private path or credential-like text in public provenance.")
    counts = value["counts"]
    lines = ["# Generation record", "",
             f"The {counts['composedActingPoses']} acting poses and {counts['composedBlinkPoses']} blink poses are compositions. They reuse original MIST parts and component drawings from {counts['selectedGeneratedSheets']} selected ImageGen sheets. They are not separately generated full faces.", "",
             f"The component families contain {counts['generatedUniqueComponentCels']} distinct generated cels and {counts['canonicalUniqueComponentCels']} distinct canonical cels, counted by exact PNG content. Shared neutral mouths and closed eyes count once. The source manifest records which component files are used by the final compositions.", "",
             f"There were {counts['imageGenerationCalls']} built-in ImageGen calls including revisions. The prompts below are preserved as recorded. Output identifiers are relative asset names; private machine paths are omitted. Earlier drafts are marked as unselected.", "",
             "Source sheets remain unchanged. Extracted cells use a common family scale, fixed attachment registration and MIST's #5eeadd palette while retaining their alpha silhouettes. `public_provenance.json` records source hashes, reference names, component counts and the manifest hash.", ""]
    for record in records:
        lines.extend(["## " + record["id"], "", "Tool: `" + record["tool"] + "`. Transparent background enabled.", "",
                      "Output: `" + record["output"]["asset"] + "` (" + ("selected" if record["selectedSheet"] else "earlier draft") + ").", "",
                      "References: " + ", ".join("`" + ref.get("asset", ref.get("repositoryAsset")) + "`" for ref in record["references"]) + ".", "",
                      "```text", record["prompt"], "```", ""])
    markdown = "\n".join(lines)
    if FORBIDDEN.search(markdown):
        raise ValueError("Unexpected private path in public prompts.")
    if any(digest(ROOT / name) != expected for name, expected in private_hashes.items()):
        raise ValueError("Private generation records changed during export; retry after generation finishes.")
    if digest(manifest_path) != manifest_sha:
        raise ValueError("Composition manifest changed during export; retry after the composer finishes.")
    (ROOT / "public_provenance.json").write_text(serialized, encoding="utf-8")
    (ROOT / "PUBLIC_PROMPTS.md").write_text(markdown, encoding="utf-8")
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
