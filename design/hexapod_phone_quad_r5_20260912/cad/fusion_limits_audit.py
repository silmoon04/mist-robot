"""Read actual native joint limits and compare them with the current R5 manifest."""

import hashlib
import importlib.util
import json
import math
from pathlib import Path

import adsk.core
import adsk.fusion


def run(_context: str):
    source = Path(__file__).resolve().with_name("fusion_runtime_r5.py")
    specification = importlib.util.spec_from_file_location("hex_quad_r5_runtime_loader", source)
    loader = importlib.util.module_from_spec(specification)
    exec(compile(source.read_bytes(), str(source), "exec"), loader.__dict__)
    runtime = loader.load_runtime()
    _, links, _, _, digest = runtime._preflight()
    app = adsk.core.Application.get()
    matches = []
    for document in app.documents:
        marker = document.attributes.itemByName(runtime.GROUP, "input_sha256")
        if marker and marker.value == digest:
            matches.append(document)
    if len(matches) != 1:
        raise RuntimeError("Expected exactly one native R5 document for the current source bytes")
    document = matches[0]
    design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
    if design.rootComponent.asBuiltJoints.count != 13:
        raise RuntimeError("Native limit audit requires all thirteen joints")
    records = {}
    for name, link in links.items():
        if name == "base":
            continue
        joint = design.rootComponent.asBuiltJoints.itemByName("J_" + name)
        if joint is None:
            raise RuntimeError("Native joint missing: " + name)
        motion = adsk.fusion.RevoluteJointMotion.cast(joint.jointMotion)
        source_joint = link["joint"]
        neutral = float(source_joint["neutral_angle_rad"])
        expected = [float(value) - neutral for value in source_joint["limits_rad"]]
        actual = [motion.rotationLimits.minimumValue, motion.rotationLimits.maximumValue]
        enabled = [motion.rotationLimits.isMinimumValueEnabled, motion.rotationLimits.isMaximumValueEnabled]
        if not all(enabled) or any(abs(a - b) > 1e-8 for a, b in zip(actual, expected)):
            raise RuntimeError("Native limits differ from source: " + name)
        if abs(motion.rotationValue) > 1e-7:
            raise RuntimeError("Native joint is not at the verified neutral pose: " + name)
        records[name] = {
            "source_absolute_limits_rad": source_joint["limits_rad"],
            "source_neutral_angle_rad": neutral,
            "native_relative_limits_rad": actual,
            "native_relative_limits_deg": [math.degrees(value) for value in actual],
            "limits_enabled": enabled,
            "native_neutral_rotation_rad": motion.rotationValue,
            "match": True,
        }
    runtime._assert_poses(runtime._occurrences(design, links), links)
    report = {
        "status": "passed",
        "document_name": document.name,
        "source_manifest_sha256": hashlib.sha256(runtime.MANIFEST.read_bytes()).hexdigest(),
        "native_input_sha256": digest,
        "joint_count": len(records),
        "all_limits_match": True,
        "all_neutral_poses_preserved": True,
        "joints": records,
    }
    (runtime.DESTINATION / "native_limits.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "joint_count": len(records), "coxa_limits_deg": records["coxa_FL"]["native_relative_limits_deg"]}))
    return report
