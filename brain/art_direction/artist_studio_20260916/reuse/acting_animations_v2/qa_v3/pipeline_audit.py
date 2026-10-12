"""Read-only motion diagnostics for the v2 source manifest and extraction metrics."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
checks = json.loads((ROOT / "asset_checks.json").read_text(encoding="utf-8"))


def center(box):
    return [box[0] + box[2] / 2, box[1] + box[3] / 2]


examples = []
for example in checks["examples"]:
    frames = example["frames"]
    samples = []
    for a, b in [(4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10), (11, 0)]:
        translation_a = frames[a]["registration"]["translation"]
        translation_b = frames[b]["registration"]["translation"]
        delta = {axis: translation_b[axis] - translation_a[axis] for axis in "xy"}
        layers = {}
        for name in ["leftEye", "rightEye", "mouth"]:
            box_a = frames[a]["layers"][name]["bbox"]
            box_b = frames[b]["layers"][name]["bbox"]
            center_a, center_b = center(box_a), center(box_b)
            registered_delta = [center_b[i] - center_a[i] for i in range(2)]
            layers[name] = {
                "beforeBox": box_a,
                "afterBox": box_b,
                "registeredCenterDelta": registered_delta,
                "sourceCenterDelta": [registered_delta[0] - delta["x"], registered_delta[1] - delta["y"]],
            }
        samples.append({"from": a, "to": b, "registrationDelta": delta, "layers": layers})
    examples.append({"key": example["key"], "canvas": [example["width"], example["height"]], "samples": samples})

handoffs = []
for source in checks["examples"]:
    for target in checks["examples"]:
        if source["key"] == target["key"]:
            continue
        scale = min(source["width"] / target["width"], source["height"] / target["height"])
        dx = (source["width"] - target["width"] * scale) / 2
        dy = (source["height"] - target["height"] * scale) / 2
        eye_jumps = {}
        for name in ["leftEye", "rightEye"]:
            a = center(source["frames"][3]["layers"][name]["bbox"])
            b = center(target["frames"][3]["layers"][name]["bbox"])
            eye_jumps[name] = round(math.dist(a, [dx + b[0] * scale, dy + b[1] * scale]), 3)
        handoffs.append({"source": source["key"], "target": target["key"], "targetScale": scale,
                         "eyeCenterJumpPixels": eye_jumps, "maxJump": max(eye_jumps.values())})
handoffs.sort(key=lambda item: item["maxJump"], reverse=True)
receipt = {
    "scope": "Motion risks, not a quality pass. All frame numbers are zero based.",
    "manifestSha256": hashlib.sha256((ROOT / "manifest.json").read_bytes()).hexdigest(),
    "limitations": ["Bounding-box centers change when shapes deform; large values need visual interpretation.",
                    "Source row-placement drift is large and the existing registration often corrects it successfully.",
                    "Registration delta alone is not proof of unwanted motion."],
    "examples": examples,
    "closedHandoffs": handoffs,
    "handoffsOver20Pixels": sum(item["maxJump"] > 20 for item in handoffs),
}
destination = Path(__file__).with_name("pipeline_metrics.json")
destination.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"file": str(destination), "examples": len(examples), "handoffs": len(handoffs),
                  "handoffsOver20Pixels": receipt["handoffsOver20Pixels"], "worst": handoffs[:3]}, indent=2))
