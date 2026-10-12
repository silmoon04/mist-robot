"""Import the new quadruped into a separate Fusion document in explicit stages.

Run inside Fusion through the local MCP script interface. Set RUN_STAGE before
calling run(), or pass 'import', 'joints', 'inspect', 'export', or 'all'. STEP
geometry becomes editable native BRep geometry. Construction geometry is made
in direct mode, then history is enabled for as-built joints. STEP import does
not recreate the source modeling history.

API signatures were checked against the installed adsk Python declarations in
AppData/Roaming/Autodesk/Autodesk Fusion 360/API/Python/defs/adsk on 2026-09-12.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import traceback
from datetime import datetime, timezone
from pathlib import Path

import adsk.core
import adsk.fusion


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "output"
DESTINATION = OUTPUT / "fusion"
MANIFEST = OUTPUT / "assembly_manifest.json"
GROUP = "hexapod_phone_quad_20260912"
RUN_STAGE = "import"
EXPECTED_LINKS = 14
EXPECTED_JOINTS = 13


def _now():
    return datetime.now(timezone.utc).isoformat()


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _progress(state, **changes):
    state.update(changes)
    state["updated_utc"] = _now()
    _write(DESTINATION / "progress.json", state)


def _vector(value):
    result = tuple(float(x) for x in value)
    if len(result) != 3 or not all(math.isfinite(x) for x in result):
        raise ValueError("Expected three finite coordinates")
    return result


def _matrix_rows(value):
    rows = [list(map(float, row)) for row in value]
    if len(rows) != 4 or any(len(row) != 4 for row in rows):
        raise ValueError("assembly_transform must be a row-major 4 x 4 matrix")
    if not all(math.isfinite(v) for row in rows for v in row):
        raise ValueError("Nonfinite assembly transform")
    if any(abs(a - b) > 1e-9 for a, b in zip(rows[3], (0, 0, 0, 1))):
        raise ValueError("Invalid homogeneous transform last row")
    for i in range(3):
        for j in range(3):
            dot = sum(rows[k][i] * rows[k][j] for k in range(3))
            if abs(dot - (1 if i == j else 0)) > 1e-7:
                raise ValueError("Assembly pose must contain a rigid rotation")
    determinant = (
        rows[0][0] * (rows[1][1] * rows[2][2] - rows[1][2] * rows[2][1])
        - rows[0][1] * (rows[1][0] * rows[2][2] - rows[1][2] * rows[2][0])
        + rows[0][2] * (rows[1][0] * rows[2][1] - rows[1][1] * rows[2][0])
    )
    if abs(determinant - 1) > 1e-7:
        raise ValueError("Assembly transform contains a reflection")
    return rows


def _fusion_matrix(rows):
    result = adsk.core.Matrix3D.create()
    for i in range(4):
        for j in range(4):
            value = rows[i][j] / 10 if i < 3 and j == 3 else rows[i][j]
            if not result.setCell(i, j, value):
                raise RuntimeError("Could not set Fusion transformation cell")
    return result


def _matrix_mm(matrix):
    return [
        [matrix.getCell(i, j) * (10 if i < 3 and j == 3 else 1) for j in range(4)]
        for i in range(4)
    ]


def _world_point(pose, point):
    return [sum(pose[i][k] * point[k] for k in range(3)) + pose[i][3] for i in range(3)]


def _world_axis(pose, axis):
    result = [sum(pose[i][k] * axis[k] for k in range(3)) for i in range(3)]
    length = math.sqrt(sum(v * v for v in result))
    if length < 1e-12:
        raise ValueError("Joint axis is zero")
    return [v / length for v in result]


def _preflight():
    payload = MANIFEST.read_bytes()
    manifest = json.loads(payload)
    if manifest.get("units") != "mm":
        raise ValueError("Manifest units must be mm")
    links = manifest["links"]
    if not isinstance(links, dict) or len(links) != EXPECTED_LINKS or "base" not in links:
        raise ValueError(f"Expected base and {EXPECTED_LINKS - 1} moving links")
    source_hashes = {}
    for name, entry in links.items():
        if not re.fullmatch(r"[A-Za-z0-9_]+", name):
            raise ValueError(f"Invalid link name: {name}")
        entry["assembly_transform"] = _matrix_rows(entry["assembly_transform"])
        step = (OUTPUT / entry.get("step", f"links/{name}.step")).resolve()
        if not step.is_relative_to((OUTPUT / "links").resolve()):
            raise ValueError("Link STEP must be under output/links")
        if not step.is_file():
            raise FileNotFoundError(step)
        entry["_step_path"] = str(step)
        source_hashes[name] = hashlib.sha256(step.read_bytes()).hexdigest()
        if name != "base":
            joint = entry["joint"]
            if joint["parent"] not in links or joint["parent"] == name:
                raise ValueError(f"Invalid parent for {name}")
            _vector(joint["origin_mm"])
            _vector(joint["axis"])
            if sum(float(a) ** 2 for a in joint["axis"]) < 1e-12:
                raise ValueError(f"Zero joint axis for {name}")
            if joint["type"] not in ("revolute", "continuous"):
                raise ValueError(f"Unsupported joint type for {name}")
            neutral = float(joint["neutral_angle_rad"])
            if not math.isfinite(neutral):
                raise ValueError("Joint neutral angle must be finite")
            limits = joint.get("limits_rad")
            if limits is not None:
                if len(limits) != 2 or not all(math.isfinite(float(v)) for v in limits):
                    raise ValueError("Joint limits must contain two finite radians")
                if not float(limits[0]) <= neutral <= float(limits[1]):
                    raise ValueError(f"Neutral position lies outside limits for {name}")
    order, unresolved = ["base"], set(links) - {"base"}
    while unresolved:
        ready = sorted(name for name in unresolved if links[name]["joint"]["parent"] in order)
        if not ready:
            raise ValueError("Joint graph has a cycle or disconnected parent chain")
        order.extend(ready)
        unresolved.difference_update(ready)
    digest = hashlib.sha256(payload + json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()
    return manifest, links, order, source_hashes, digest


def _document_for_input(app, digest):
    matches = []
    for i in range(app.documents.count):
        document = app.documents.item(i)
        marker = document.attributes.itemByName(GROUP, "input_sha256")
        if marker and marker.value == digest:
            matches.append(document)
    if len(matches) != 1:
        raise RuntimeError(f"Expected one imported document for these source bytes; found {len(matches)}")
    document = matches[0]
    if not document.activate():
        raise RuntimeError("Could not activate the imported document")
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design is None:
        raise RuntimeError("Imported document has no Fusion design")
    return document, design


def _occurrences(design, links):
    result = {}
    for occurrence in design.rootComponent.occurrences:
        name = occurrence.component.name
        if name in links:
            if name in result:
                raise RuntimeError(f"Duplicate imported link occurrence: {name}")
            result[name] = occurrence
    if set(result) != set(links):
        raise RuntimeError(f"Imported link set is incomplete: {sorted(set(links) - set(result))}")
    return result


def _walk_occurrences(occurrence):
    yield occurrence
    for child in occurrence.childOccurrences:
        yield from _walk_occurrences(child)


def _bodies(occurrence):
    for nested in _walk_occurrences(occurrence):
        yield from nested.bRepBodies


def _shape_bounds_mm(bodies):
    low, high = [math.inf] * 3, [-math.inf] * 3
    count = 0
    for body in bodies:
        bb = body.preciseBoundingBox
        a, b = bb.minPoint, bb.maxPoint
        for i, (x, y) in enumerate(zip((a.x, a.y, a.z), (b.x, b.y, b.z))):
            low[i], high[i] = min(low[i], x * 10), max(high[i], y * 10)
        count += 1
    if not count:
        raise RuntimeError("Imported link contains no native BRep bodies")
    return [low, high]


def _pose_error(occurrence, target):
    actual = _matrix_mm(occurrence.transform2)
    return {
        "translation_error_mm": max(abs(actual[i][3] - target[i][3]) for i in range(3)),
        "rotation_matrix_error": max(abs(actual[i][j] - target[i][j]) for i in range(3) for j in range(3)),
    }


def _assert_poses(occurrences, links):
    checks = {name: _pose_error(occurrences[name], entry["assembly_transform"]) for name, entry in links.items()}
    bad = {name: error for name, error in checks.items() if error["translation_error_mm"] > 1e-4 or error["rotation_matrix_error"] > 1e-7}
    if bad:
        raise RuntimeError("Native assembly pose changed: " + json.dumps(bad))
    return checks


def _configure_grounding(design, occurrences, links, state):
    """Pin only the base wrapper; internal imported rigid groups stay intact."""
    before = {
        name: {
            "is_grounded": occurrence.isGrounded,
            "is_ground_to_parent": occurrence.isGroundToParent if hasattr(occurrence, "isGroundToParent") else None,
        }
        for name, occurrence in occurrences.items()
    }
    needs_change = [
        name for name, values in before.items()
        if values["is_grounded"] != (name == "base")
        or (values["is_ground_to_parent"] is not None and values["is_ground_to_parent"] != (name == "base"))
    ]
    if needs_change and design.rootComponent.asBuiltJoints.count:
        raise RuntimeError("Unexpected wrapper grounding in an existing joint assembly: " + json.dumps(before))
    for name in needs_change:
        occurrence = occurrences[name]
        if name != "base":
            if occurrence.isGrounded:
                occurrence.isGrounded = False
            if hasattr(occurrence, "isGroundToParent") and occurrence.isGroundToParent:
                occurrence.isGroundToParent = False
            error = _pose_error(occurrence, links[name]["assembly_transform"])
            if error["translation_error_mm"] > 1e-6 or error["rotation_matrix_error"] > 1e-9:
                occurrence.transform2 = _fusion_matrix(links[name]["assembly_transform"])
        else:
            occurrence.isGrounded = True
            if hasattr(occurrence, "isGroundToParent") and not occurrence.isGroundToParent:
                occurrence.isGroundToParent = True
    state["wrapper_grounding"] = {
        name: {
            "is_grounded": occurrence.isGrounded,
            "is_ground_to_parent": occurrence.isGroundToParent if hasattr(occurrence, "isGroundToParent") else None,
        }
        for name, occurrence in occurrences.items()
    }
    state["pose_checks"] = _assert_poses(occurrences, links)
    if needs_change:
        state.setdefault("grounding_adjustments", []).append({"before": before, "changed_wrappers": needs_change})


def _appearance_source(app):
    fallback = None
    for library in app.materialLibraries:
        for appearance in library.appearances:
            title = appearance.name.lower()
            if "plastic" in title and "matte" in title:
                return appearance
            if fallback is None and "plastic" in title:
                fallback = appearance
    return fallback


def _apply_appearances(app, design, occurrences, state):
    source = _appearance_source(app)
    if source is None:
        state["warnings"].append("No installed plastic appearance was found; imported appearance retained")
        return
    colors = {"base": (49, 62, 74), "coxa": (232, 125, 44), "femur": (220, 226, 230), "tibia": (58, 70, 79), "phone": (25, 131, 157)}
    appearances = {}
    for family, rgb in colors.items():
        appearance = design.appearances.addByCopy(source, f"Quadruped_{family}")
        color_property = None
        for prop in appearance.appearanceProperties:
            color_property = adsk.core.ColorProperty.cast(prop)
            if color_property is not None:
                break
        if color_property is None:
            state["warnings"].append(f"Appearance {family} has no editable color property")
            continue
        color_property.value = adsk.core.Color.create(*rgb, 255)
        appearances[family] = appearance
    for name, occurrence in occurrences.items():
        family = name.split("_")[0]
        if family in appearances:
            occurrence.appearance = appearances[family]


def _import(app, links, order, digest, state):
    document = None
    for i in range(app.documents.count):
        existing = app.documents.item(i)
        marker = existing.attributes.itemByName(GROUP, "input_sha256")
        if marker and marker.value == digest:
            existing.activate()
            existing_design = adsk.fusion.Design.cast(app.activeProduct)
            if existing_design and existing_design.rootComponent.bRepBodies.count == 0 and existing_design.rootComponent.occurrences.count == 0:
                document = existing
                break
            raise RuntimeError("These source bytes already have an open imported document; use a later stage")
    if document is None:
        document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.name = "Hexapod reference quadruped phone " + datetime.now().strftime("%Y%m%d_%H%M%S")
    document.attributes.add(GROUP, "input_sha256", digest)
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design is None:
        raise RuntimeError("A new Fusion design was not created")
    design.designType = adsk.fusion.DesignTypes.DirectDesignType
    root = design.rootComponent
    _progress(state, document_name=document.name, current_step="new_document_created", imported_links=[])
    importer = app.importManager
    import_details = {}
    for name in order:
        _progress(state, current_step=f"importing_{name}")
        occurrence = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occurrence.component.name = name
        options = importer.createSTEPImportOptions(links[name]["_step_path"])
        options.isViewFit = False
        if hasattr(importer, "importToTarget2"):
            returned = importer.importToTarget2(options, occurrence.component)
            if returned is None:
                raise RuntimeError(f"STEP import failed for {name}")
            returned_types = [item.objectType for item in returned]
        else:
            if not importer.importToTarget(options, occurrence.component):
                raise RuntimeError(f"STEP import failed for {name}")
            returned_types = ["legacy_importToTarget_bool"]
        bodies = list(_bodies(occurrence))
        if not bodies or not all(body.isSolid for body in bodies):
            raise RuntimeError(f"STEP link {name} did not import as closed native BRep solids")
        for index, body in enumerate(bodies, 1):
            native = body.nativeObject or body
            native.name = f"{name}__{native.name or f'body_{index:03d}'}"
        occurrence.transform2 = _fusion_matrix(links[name]["assembly_transform"])
        children = list(occurrence.childOccurrences)
        if children:
            members = adsk.core.ObjectCollection.create()
            members.add(occurrence)
            for child in children:
                members.add(child)
            group = root.rigidGroups.add(members, True)
            if group is None:
                raise RuntimeError(f"Could not keep imported subcomponents of {name} rigid")
        occurrence.component.isConstructionFolderLightBulbOn = False
        import_details[name] = {
            "returned_object_types": returned_types,
            "direct_body_count": occurrence.component.bRepBodies.count,
            "descendant_occurrence_count": sum(1 for _ in _walk_occurrences(occurrence)) - 1,
            "native_body_count": len(bodies),
        }
        state["imported_links"].append(name)
        state["import_details"] = import_details
        _progress(state, current_step=f"imported_{name}")
        adsk.doEvents()
    occurrences = _occurrences(design, links)
    _configure_grounding(design, occurrences, links, state)
    if root.bRepBodies.count:
        raise RuntimeError("STEP import unexpectedly put bodies outside link components")
    state["pose_checks"] = _assert_poses(occurrences, links)
    try:
        _apply_appearances(app, design, occurrences, state)
    except Exception as error:
        state["warnings"].append("Optional appearance assignment failed: " + str(error))
    _progress(state, current_step="import_complete", import_complete=True)
    return document, design


def _joint_geometry(parent, origin_mm, axis, name, create_missing=False, root=None):
    """Make a joint frame whose own Z axis follows the required hinge.

    Autodesk forum report and workaround, March 2025:
    https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/asbuiltjoints-add-seems-to-disrespect-jointdirections/td-p/13360610
    The local Fusion 2705.1.11 motion tests reproduced the ignored custom axis.
    """
    component = parent.component
    parent_pose = _matrix_mm(parent.transform2)
    world_origin_mm = _world_point(parent_pose, origin_mm)
    world_axis = _world_axis(parent_pose, axis)
    plane = component.constructionPlanes.itemByName(name + "_frame_plane")
    sketch = component.sketches.itemByName(name + "_frame_sketch")
    if (plane is None or sketch is None) and not create_missing:
        raise RuntimeError(f"Missing prepared oriented sketch for {name}; do not disable existing joint history")
    if plane is None:
        specification = component.constructionPlanes.createInput()
        world_plane = adsk.core.Plane.create(
            adsk.core.Point3D.create(*(v / 10 for v in world_origin_mm)),
            adsk.core.Vector3D.create(*world_axis),
        )
        if not specification.setByPlane(world_plane):
            raise RuntimeError(f"Could not define oriented joint plane for {name}")
        plane = component.constructionPlanes.add(specification)
        plane.name = name + "_frame_plane"
        plane.isLightBulbOn = False
    if sketch is None:
        sketch = component.sketches.add(plane)
        sketch.name = name + "_frame_sketch"
        sketch_proxy = sketch.createForAssemblyContext(parent)
        center = sketch_proxy.modelToSketchSpace(
            adsk.core.Point3D.create(*(v / 10 for v in world_origin_mm))
        )
        if abs(center.z) > 1e-5:
            raise RuntimeError(f"Desired joint center for {name} is outside its oriented sketch plane")
        circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(center, 0.2)
        if circle is None:
            raise RuntimeError(f"Could not create oriented joint-frame circle for {name}")
        sketch.isLightBulbOn = False
    if sketch.sketchCurves.sketchCircles.count != 1:
        raise RuntimeError(f"Expected exactly one construction circle in the joint frame for {name}")
    circle = sketch.sketchCurves.sketchCircles.item(0)
    circle_proxy = circle.createForAssemblyContext(parent)
    geometry = adsk.fusion.JointGeometry.createByCurve(
        circle_proxy, adsk.fusion.JointKeyPointTypes.CenterKeyPoint
    )
    if geometry is None:
        raise RuntimeError(f"Could not derive joint geometry from the oriented circle for {name}")
    reported_origin = geometry.origin
    actual_origin_mm = [reported_origin.x * 10, reported_origin.y * 10, reported_origin.z * 10]
    reported_axis = geometry.primaryAxisVector
    actual_axis = [reported_axis.x, reported_axis.y, reported_axis.z]
    length = math.sqrt(sum(v * v for v in actual_axis))
    alignment = sum(a * b for a, b in zip(actual_axis, world_axis)) / max(length, 1e-12)
    # The proxy origin is world-space, but Fusion 2705.1.11 reports the primary
    # axis in parent-local coordinates here. Actual world motion is tested below.
    if max(abs(a - b) for a, b in zip(actual_origin_mm, world_origin_mm)) > 1e-4:
        raise RuntimeError("Oriented circle joint-frame diagnostic: " + json.dumps({
            "joint": name,
            "expected_origin_world_mm": world_origin_mm,
            "reported_geometry_origin_mm": actual_origin_mm,
            "expected_axis_world": world_axis,
            "reported_geometry_primary_axis": actual_axis,
            "axis_alignment_dot": alignment,
            "parent_transform_mm": parent_pose,
        }))
    return geometry


def _rotation_matrix(axis, radians):
    x, y, z = axis
    c, s, d = math.cos(radians), math.sin(radians), 1 - math.cos(radians)
    return [
        [c + x * x * d, x * y * d - z * s, x * z * d + y * s],
        [y * x * d + z * s, c + y * y * d, y * z * d - x * s],
        [z * x * d - y * s, z * y * d + x * s, c + z * z * d],
    ]


def _probe_joint_motion(motion, child, parent, origin_world_mm, axis_world, occurrences, links):
    """Check one degree of actual child motion and restore the assembled pose."""
    if child.isGrounded or (hasattr(child, "isGroundToParent") and child.isGroundToParent):
        raise RuntimeError("Cannot probe a moving link while its wrapper is grounded")
    initial = float(motion.rotationValue)
    before = _matrix_mm(child.transform2)
    parent_before = _matrix_mm(parent.transform2)
    step = math.radians(1)
    limits = motion.rotationLimits
    lower = limits.minimumValue if limits.isMinimumValueEnabled else -math.inf
    upper = limits.maximumValue if limits.isMaximumValueEnabled else math.inf
    if not lower + 1e-8 <= initial + step <= upper - 1e-8:
        step = -step
    if not lower + 1e-8 <= initial + step <= upper - 1e-8:
        raise RuntimeError("Joint range does not permit a bounded one-degree motion check")
    after, parent_after, actual_scalar = None, None, None
    try:
        motion.rotationValue = initial + step
        adsk.doEvents()
        after = _matrix_mm(child.transform2)
        parent_after = _matrix_mm(parent.transform2)
        actual_scalar = float(motion.rotationValue)
    finally:
        motion.rotationValue = initial
        adsk.doEvents()
    restored = _assert_poses(occurrences, links)
    if abs(float(motion.rotationValue) - initial) > 1e-7:
        raise RuntimeError("Joint motion check did not restore its original angle")
    expected_delta = _rotation_matrix(axis_world, step)
    expected_pose = [[0.0] * 4 for _ in range(4)]
    expected_pose[3][3] = 1.0
    for i in range(3):
        for j in range(3):
            expected_pose[i][j] = sum(expected_delta[i][k] * before[k][j] for k in range(3))
        expected_pose[i][3] = origin_world_mm[i] + sum(
            expected_delta[i][k] * (before[k][3] - origin_world_mm[k]) for k in range(3)
        )
    actual_delta = [
        [sum(after[i][k] * before[j][k] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]
    cosine = max(-1.0, min(1.0, (sum(actual_delta[i][i] for i in range(3)) - 1) / 2))
    measured_angle = math.acos(cosine)
    antisymmetric = [
        actual_delta[2][1] - actual_delta[1][2],
        actual_delta[0][2] - actual_delta[2][0],
        actual_delta[1][0] - actual_delta[0][1],
    ]
    measured_axis = [value / (2 * math.sin(step)) for value in antisymmetric]
    axis_length = math.sqrt(sum(v * v for v in measured_axis))
    if axis_length > 1e-9:
        measured_axis = [v / axis_length for v in measured_axis]
    alignment = sum(a * b for a, b in zip(measured_axis, axis_world))
    # Choose a real point in the child's local frame whose radius is far from
    # parallel to the hinge. Its finite displacement also verifies hinge position.
    candidates = ((25, 0, 0), (0, 25, 0), (0, 0, 25))
    def radial_distance_squared(local):
        point = _world_point(before, local)
        radius = [point[i] - origin_world_mm[i] for i in range(3)]
        along = sum(a * b for a, b in zip(radius, axis_world))
        return sum(v * v for v in radius) - along * along
    local_datum = max(candidates, key=radial_distance_squared)
    datum_before = _world_point(before, local_datum)
    datum_after = _world_point(after, local_datum)
    datum_expected = _world_point(expected_pose, local_datum)
    radius = [datum_before[i] - origin_world_mm[i] for i in range(3)]
    derivative = [
        axis_world[1] * radius[2] - axis_world[2] * radius[1],
        axis_world[2] * radius[0] - axis_world[0] * radius[2],
        axis_world[0] * radius[1] - axis_world[1] * radius[0],
    ]
    datum_error = math.sqrt(sum((a - b) ** 2 for a, b in zip(datum_after, datum_expected)))
    translation_error = max(abs(after[i][3] - expected_pose[i][3]) for i in range(3))
    rotation_error = max(abs(after[i][j] - expected_pose[i][j]) for i in range(3) for j in range(3))
    parent_translation_drift = max(abs(parent_after[i][3] - parent_before[i][3]) for i in range(3))
    parent_rotation_drift = max(abs(parent_after[i][j] - parent_before[i][j]) for i in range(3) for j in range(3))
    passed = (
        abs(actual_scalar - (initial + step)) < 1e-7
        and abs(measured_angle - abs(step)) < 1e-5
        and alignment > 0.9999
        and datum_error < 0.02
        and translation_error < 0.02
        and rotation_error < 1e-5
        and parent_translation_drift < 1e-4
        and parent_rotation_drift < 1e-7
    )
    report = {
        "passed": passed,
        "commanded_delta_rad": step,
        "measured_angle_magnitude_rad": measured_angle,
        "measured_positive_world_axis": measured_axis,
        "expected_positive_world_axis": list(axis_world),
        "axis_alignment_dot": alignment,
        "expected_hinge_world_mm": list(origin_world_mm),
        "datum_local_mm": list(local_datum),
        "datum_before_world_mm": datum_before,
        "datum_after_world_mm": datum_after,
        "datum_expected_world_mm": datum_expected,
        "datum_cross_product_derivative_mm_per_rad": derivative,
        "datum_error_mm": datum_error,
        "child_origin_error_mm": translation_error,
        "child_rotation_matrix_error": rotation_error,
        "parent_translation_drift_mm": parent_translation_drift,
        "parent_rotation_matrix_drift": parent_rotation_drift,
        "all_neutral_poses_restored": all(
            p["translation_error_mm"] <= 1e-4 and p["rotation_matrix_error"] <= 1e-7 for p in restored.values()
        ),
    }
    if not passed:
        raise RuntimeError("Native joint kinematic probe failed after restoring neutral: " + json.dumps(report))
    return report


def _joints(design, links, order, state):
    if not design.isRootComponentActive and not design.activateRootComponent():
        raise RuntimeError("Could not activate root for world-coordinate construction input")
    root = design.rootComponent
    occurrences = _occurrences(design, links)
    _configure_grounding(design, occurrences, links, state)
    state["pose_checks"] = _assert_poses(occurrences, links)
    direct = design.designType == adsk.fusion.DesignTypes.DirectDesignType
    if direct and root.asBuiltJoints.count:
        raise RuntimeError("Unexpected existing as-built joints in direct mode")
    prepared = state.setdefault("prepared_joint_geometry", [])
    for child_name in order[1:]:
        entry = links[child_name]["joint"]
        name = "J_" + child_name
        _progress(state, current_step=f"preparing_geometry_{name}")
        _joint_geometry(
            occurrences[entry["parent"]],
            _vector(entry["origin_mm"]),
            _vector(entry["axis"]),
            name,
            create_missing=direct,
            root=root,
        )
        if child_name not in prepared:
            prepared.append(child_name)
        _progress(state, current_step=f"prepared_geometry_{name}")
    if direct:
        _progress(state, current_step="enabling_history_for_as_built_joints")
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        adsk.doEvents()
    if design.designType != adsk.fusion.DesignTypes.ParametricDesignType:
        raise RuntimeError("Fusion did not enable the history required by as-built joints")
    root = design.rootComponent
    occurrences = _occurrences(design, links)
    _configure_grounding(design, occurrences, links, state)
    state["pose_checks"] = _assert_poses(occurrences, links)
    _progress(state, current_step="joint_geometry_prepared_and_history_enabled", history_enabled=True)
    existing = {joint.name: joint for joint in root.asBuiltJoints}
    records = state.setdefault("joints", {})
    for child_name in order[1:]:
        entry = links[child_name]["joint"]
        name = "J_" + child_name
        if name in existing and records.get(child_name, {}).get("motion_probe", {}).get("passed"):
            continue
        _progress(state, current_step=f"creating_{name}")
        parent_name = entry["parent"]
        parent, child = occurrences[parent_name], occurrences[child_name]
        origin, axis = _vector(entry["origin_mm"]), _vector(entry["axis"])
        geometry = _joint_geometry(parent, origin, axis, name, root=root)
        if name in existing:
            joint = existing[name]
            if joint.occurrenceOne.component.name != child_name or joint.occurrenceTwo.component.name != parent_name:
                raise RuntimeError(f"Existing joint {name} connects unexpected link occurrences")
        else:
            specification = root.asBuiltJoints.createInput(child, parent, geometry)
            if not specification.setAsRevoluteJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection):
                raise RuntimeError(f"Could not configure revolute motion for {name}")
            joint = root.asBuiltJoints.add(specification)
            if joint is None:
                raise RuntimeError(f"Native as-built joint creation failed: {name}")
            joint.name = name
        motion = adsk.fusion.RevoluteJointMotion.cast(joint.jointMotion)
        if motion is None or abs(motion.rotationValue) > 1e-7:
            raise RuntimeError(f"{name} did not preserve an undriven zero offset at assembled neutral")
        neutral = float(entry["neutral_angle_rad"])
        limits = entry.get("limits_rad")
        relative_limits = None
        if limits is not None:
            relative_limits = [float(v) - neutral for v in limits]
            motion.rotationLimits.minimumValue = relative_limits[0]
            motion.rotationLimits.maximumValue = relative_limits[1]
            motion.rotationLimits.isMinimumValueEnabled = True
            motion.rotationLimits.isMaximumValueEnabled = True
        reported_axis = motion.rotationAxisVector
        expected_axis = _world_axis(links[parent_name]["assembly_transform"], axis)
        raw_axis = [reported_axis.x, reported_axis.y, reported_axis.z] if reported_axis is not None else None
        expected_origin = _world_point(links[parent_name]["assembly_transform"], origin)
        measured_origin = joint.geometry.origin
        raw_origin = [measured_origin.x * 10, measured_origin.y * 10, measured_origin.z * 10]
        _progress(state, current_step=f"probing_motion_{name}")
        motion_probe = _probe_joint_motion(motion, child, parent, expected_origin, expected_axis, occurrences, links)
        state["pose_checks"] = _assert_poses(occurrences, links)
        records[child_name] = {
            "native_joint_name": name,
            "parent": parent_name,
            "child": child_name,
            "source_type": entry["type"],
            "source_neutral_angle_rad": neutral,
            "native_neutral_rotation_rad": float(motion.rotationValue),
            "source_limits_rad": limits,
            "native_limits_relative_to_neutral_rad": relative_limits,
            "origin_world_mm": expected_origin,
            "axis_world": expected_axis,
            "rotation_axis_vector_raw": raw_axis,
            "rotation_axis_reference": "oriented_parent_sketch_circle_joint_geometry_z_axis",
            "joint_geometry_origin_raw_mm": raw_origin,
            "axis_alignment_dot": motion_probe["axis_alignment_dot"],
            "motion_probe": motion_probe,
            "neutral_pose_restored": True,
        }
        _progress(state, current_step=f"created_{name}", joints=records)
        adsk.doEvents()
    if root.asBuiltJoints.count != EXPECTED_JOINTS:
        raise RuntimeError(f"Expected {EXPECTED_JOINTS} real as-built joints, got {root.asBuiltJoints.count}")
    _progress(state, current_step="joints_complete", native_revolute_count=root.asBuiltJoints.count, joints_complete=True)


def _entity_label(entity):
    return {"name": getattr(entity, "name", ""), "object_type": entity.objectType}


def _native_interferences(design, occurrences, state):
    _progress(state, current_step="native_interference_analysis")
    collection = adsk.core.ObjectCollection.create()
    for occurrence in occurrences.values():
        collection.add(occurrence)
    specification = design.createInterferenceInput(collection)
    specification.areCoincidentFacesIncluded = False
    result = design.analyzeInterference(specification)
    if result is None:
        raise RuntimeError("Native interference analysis returned no result")
    records = []
    for interference in result:
        volume = interference.interferenceBody.getPhysicalProperties(
            adsk.fusion.CalculationAccuracy.HighCalculationAccuracy
        ).volume * 1000
        if volume > 1e-6:
            records.append({
                "first": _entity_label(interference.entityOne),
                "second": _entity_label(interference.entityTwo),
                "volume_mm3": volume,
            })
    return {
        "status": "completed",
        "result_count": result.count,
        "positive_volume_result_count": len(records),
        "intersections": records,
        "interpretation": "Geometric intersections only. Hardware envelopes and intentional mating volumes need review; this is not a clearance certification.",
    }


def _inspect(design, links, state, interference=True):
    occurrences = _occurrences(design, links)
    measurements, all_bodies = {}, []
    for name, occurrence in occurrences.items():
        _progress(state, current_step=f"measuring_{name}")
        bodies = list(_bodies(occurrence))
        all_bodies.extend(bodies)
        volumes = [body.getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume * 1000 for body in bodies]
        measurements[name] = {
            "native_body_count": len(bodies),
            "all_bodies_closed": all(body.isSolid for body in bodies),
            "volume_mm3": sum(volumes),
            "body_volumes_mm3": volumes,
            "bounds_world_mm": _shape_bounds_mm(bodies),
            "assembly_transform_mm": _matrix_mm(occurrence.transform2),
        }
        if "volume_mm3" in links[name]:
            expected = float(links[name]["volume_mm3"])
            measurements[name]["source_volume_mm3"] = expected
            measurements[name]["volume_relative_error"] = abs(sum(volumes) - expected) / max(abs(expected), 1e-12)
    state["pose_checks"] = _assert_poses(occurrences, links)
    state.update({
        "native_link_count": len(occurrences),
        "native_body_count": len(all_bodies),
        "native_revolute_count": design.rootComponent.asBuiltJoints.count,
        "base_grounded": occurrences["base"].isGrounded,
        "assembly_bounds_world_mm": _shape_bounds_mm(all_bodies),
        "measurements": measurements,
        "native_geometry": "Editable imported BRep solids with history enabled for assembly joints; source modeling history was not recreated",
        "motion_validation": "Each recorded joint passed a bounded one-degree native drive with world datum and rotation checks; all neutral poses were restored",
    })
    if interference:
        try:
            state["native_interferences"] = _native_interferences(design, occurrences, state)
        except Exception as error:
            state["native_interferences"] = {"status": "unavailable", "error": str(error)}
    _progress(state, current_step="inspection_complete", inspection_complete=True)
    _write(DESTINATION / "native_inspection.json", {**state, "status": "inspection_completed"})


def _export(app, design, state):
    if (
        not state.get("joints_complete")
        or design.rootComponent.asBuiltJoints.count != EXPECTED_JOINTS
        or len(state.get("joints", {})) != EXPECTED_JOINTS
        or not all(record.get("motion_probe", {}).get("passed") for record in state.get("joints", {}).values())
    ):
        raise RuntimeError("Native export requires all 13 verified as-built joints to be complete")
    _progress(state, current_step="exporting_native_archive")
    manager = design.exportManager
    archive = DESTINATION / "quadruped_phone_native.f3d"
    step = DESTINATION / "quadruped_phone_native.step"
    if not manager.execute(manager.createFusionArchiveExportOptions(str(archive))):
        raise RuntimeError("Native Fusion archive export failed")
    _progress(state, current_step="exporting_native_step")
    if not manager.execute(manager.createSTEPExportOptions(str(step))):
        raise RuntimeError("Native Fusion STEP export failed")
    viewport = app.activeViewport
    camera = viewport.camera
    camera.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    camera.eye = adsk.core.Point3D.create(60, -75, 48)
    camera.target = adsk.core.Point3D.create(0, 0, 10)
    camera.upVector = adsk.core.Vector3D.create(0, 0, 1)
    camera.isFitView = True
    viewport.camera = camera
    viewport.fit()
    viewport.refresh()
    adsk.doEvents()
    preview = DESTINATION / "quadruped_phone_native.png"
    if not viewport.saveAsImageFile(str(preview), 1800, 1400):
        raise RuntimeError("Native viewport PNG export failed")
    state["exports"] = {"f3d": str(archive), "step": str(step), "preview": str(preview)}
    state["export_sha256"] = {key: hashlib.sha256(Path(path).read_bytes()).hexdigest() for key, path in state["exports"].items()}
    _progress(state, current_step="export_complete", export_complete=True)


def run(_context: str):
    """Execute one explicit stage; propagate failures after writing progress."""
    stage, interference = RUN_STAGE, True
    if isinstance(_context, str) and _context in ("import", "joints", "inspect", "export", "all"):
        stage = _context
    elif isinstance(_context, str) and _context.startswith("{"):
        options = json.loads(_context)
        stage, interference = options.get("stage", stage), options.get("interference", True)
    if stage not in ("import", "joints", "inspect", "export", "all"):
        raise ValueError("Stage must be import, joints, inspect, export or all")
    manifest, links, order, source_hashes, digest = _preflight()
    progress_path = DESTINATION / "progress.json"
    state = json.loads(progress_path.read_text()) if progress_path.exists() and stage not in ("import", "all") else {}
    if state and state.get("input_sha256") != digest:
        raise RuntimeError("Manifest or STEP bytes changed since native import")
    if state.get("error"):
        state.setdefault("previous_failures", []).append({
            "stage": state.get("stage"),
            "current_step": state.get("current_step"),
            "updated_utc": state.get("updated_utc"),
            "error": state.pop("error"),
        })
    state.update({
        "status": "running",
        "stage": stage,
        "input_sha256": digest,
        "source_manifest": str(MANIFEST),
        "source_step_sha256": source_hashes,
        "warnings": state.get("warnings", []),
    })
    _progress(state, current_step="preflight_complete")
    app = adsk.core.Application.get()
    try:
        if stage in ("import", "all"):
            document, design = _import(app, links, order, digest, state)
        else:
            document, design = _document_for_input(app, digest)
        state["document_name"] = document.name
        state["fusion_version"] = app.version
        if stage in ("joints", "all"):
            _joints(design, links, order, state)
        if stage in ("inspect", "all"):
            _inspect(design, links, state, interference=interference)
        if stage in ("export", "all"):
            _export(app, design, state)
        _progress(state, status="completed", current_step=stage + "_complete")
        if stage in ("export", "all"):
            _write(DESTINATION / "native_report.json", state)
        print(json.dumps({key: state.get(key) for key in ("status", "stage", "document_name", "native_link_count", "native_body_count", "native_revolute_count", "exports", "warnings")}))
        return state
    except Exception:
        _progress(state, status="failed", error=traceback.format_exc())
        raise
