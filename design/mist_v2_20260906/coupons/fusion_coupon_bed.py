"""Build the MIST fit coupons as editable Fusion sketches and features.

Run this script inside Fusion with coupon_recipe.json beside it. Each run creates
a new document and a separate folder below fusion_output. The F3D keeps the
timeline; STEP is an exchange copy. Existing documents and exports are untouched.

Recipe coordinates are millimetres. Box coordinates are lower corners. Cylinder
and cone x/y coordinates are centres; z is the bottom face. For a cone,
bottom_diameter is the bottom diameter and diameter is the top diameter.

Outside Fusion, validate the recipe with:
    python fusion_coupon_bed.py --validate [path/to/coupon_recipe.json]

API references:
https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExtrudeFeatureInput_setOneSideExtent.htm
https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/LoftSections_add.htm
https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExportManager_Sample.htm
"""

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import tempfile
import traceback


HERE = Path(__file__).resolve().parent
DEFAULT_RECIPE = HERE / "coupon_recipe.json"
OUTPUT_ROOT = HERE / "fusion_output"
SCHEMA_VERSION = 1


def _number(value, location, positive=False, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{location}: expected a number in millimetres")
    if not math.isfinite(value):
        raise ValueError(f"{location}: dimension must be finite")
    if positive and value <= 0:
        raise ValueError(f"{location}: dimension must be greater than zero")
    if nonnegative and value < 0:
        raise ValueError(f"{location}: dimension must not be negative")
    return float(value)


def validate_recipe(recipe):
    """Check recipe structure and dimensions without importing the Fusion API."""
    if not isinstance(recipe, dict) or not isinstance(recipe.get("parts"), list):
        raise ValueError("Recipe must contain a parts list")
    if not recipe["parts"]:
        raise ValueError("Recipe contains no parts")
    names = set()
    operation_count = 0
    kinds = {}
    for part_index, part in enumerate(recipe["parts"]):
        location = f"parts[{part_index}]"
        if not isinstance(part, dict):
            raise ValueError(f"{location}: expected an object")
        name = part.get("name")
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError(f"{location}: part name must be nonempty and unique")
        names.add(name)
        ops = part.get("ops")
        if not isinstance(ops, list) or not ops:
            raise ValueError(f"{location}: expected a nonempty ops list")
        for op_index, op in enumerate(ops):
            here = f"{location} ({name}), ops[{op_index}]"
            if not isinstance(op, dict):
                raise ValueError(f"{here}: expected an object")
            if op.get("op") not in ("add", "cut"):
                raise ValueError(f"{here}: op must be add or cut")
            if op_index == 0 and op["op"] != "add":
                raise ValueError(f"{here}: first operation must add material")
            kind = op.get("kind")
            if kind not in ("box", "cylinder", "cone", "polygon"):
                raise ValueError(f"{here}: unsupported kind {kind!r}")
            _number(op.get("z"), f"{here}.z")
            if kind != "polygon":
                for field in ("x", "y"):
                    _number(op.get(field), f"{here}.{field}")
            if kind == "box":
                for field in ("sx", "sy", "sz"):
                    _number(op.get(field), f"{here}.{field}", positive=True)
            else:
                _number(op.get("height"), f"{here}.height", positive=True)
            if kind == "cylinder":
                _number(op.get("diameter"), f"{here}.diameter", positive=True)
            elif kind == "cone":
                top = _number(op.get("diameter"), f"{here}.diameter", nonnegative=True)
                bottom = _number(op.get("bottom_diameter"), f"{here}.bottom_diameter", nonnegative=True)
                if top == 0 and bottom == 0:
                    raise ValueError(f"{here}: both cone diameters cannot be zero")
            elif kind == "polygon":
                points = op.get("points")
                if not isinstance(points, list) or len(points) < 3:
                    raise ValueError(f"{here}: polygon needs at least three points")
                for point_index, point in enumerate(points):
                    if not isinstance(point, (list, tuple)) or len(point) != 2:
                        raise ValueError(f"{here}.points[{point_index}]: expected [x, y]")
                    for value in point:
                        _number(value, f"{here}.points[{point_index}]")
                polygon = points[:-1] if points[0] == points[-1] else points
                if len(polygon) < 3:
                    raise ValueError(f"{here}: polygon needs three distinct corners")
                area2 = 0.0
                for a, b in zip(polygon, polygon[1:] + polygon[:1]):
                    if a == b:
                        raise ValueError(f"{here}: polygon contains a zero-length edge")
                    area2 += a[0] * b[1] - b[0] * a[1]
                if abs(area2) < 1e-10:
                    raise ValueError(f"{here}: polygon has zero signed area")
            operation_count += 1
            kinds[kind] = kinds.get(kind, 0) + 1
    return {"parts": len(names), "operations": operation_count, "kinds": kinds}


def load_recipe(path):
    raw = Path(path).read_bytes()
    recipe = json.loads(raw.decode("utf-8-sig"))
    summary = validate_recipe(recipe)
    return recipe, raw, summary


def _write_manifest(folder, manifest):
    manifest["updated_utc"] = datetime.now(timezone.utc).isoformat()
    (folder / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


class CouponBuilder:
    def __init__(self, api, design, manifest, output_folder):
        self.api = api
        self.design = design
        self.manifest = manifest
        self.output_folder = output_folder
        self.component = None
        self.planes = {}

    def point(self, x, y):
        return self.api.core.Point3D.create(float(x) / 10, float(y) / 10, 0)

    def distance(self, value):
        return self.api.core.ValueInput.createByString(f"{float(value):.12g} mm")

    def plane(self, z):
        key = float(z)
        if abs(key) < 1e-12:
            return self.component.xYConstructionPlane
        if key not in self.planes:
            planes = self.component.constructionPlanes
            plane_input = planes.createInput()
            if not plane_input.setByOffset(self.component.xYConstructionPlane, self.distance(z)):
                raise RuntimeError(f"Cannot define plane at z={z} mm")
            result = planes.add(plane_input)
            result.name = f"Z {z:g} mm"
            result.isLightBulbOn = False
            self.planes[key] = result
        return self.planes[key]

    def sketch(self, z, name):
        result = self.component.sketches.add(self.plane(z))
        result.name = name
        return result

    def profile(self, sketch):
        if sketch.profiles.count != 1:
            raise RuntimeError(
                f"{sketch.name}: expected one closed profile, got {sketch.profiles.count}"
            )
        return sketch.profiles.item(0)

    def circle_section(self, x, y, z, diameter, name):
        sketch = self.sketch(z, name)
        if diameter == 0:
            section = sketch.sketchPoints.add(self.point(x, y))
            section.isFixed = True
        else:
            circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
                self.point(x, y), float(diameter) / 20
            )
            circle.centerSketchPoint.isFixed = True
            dimension = sketch.sketchDimensions.addDiameterDimension(
                circle, self.point(x + diameter, y + diameter / 2)
            )
            dimension.parameter.expression = f"{float(diameter):.12g} mm"
            section = self.profile(sketch)
        return sketch, section

    def operation(self, op):
        operations = self.api.fusion.FeatureOperations
        if op["op"] == "cut":
            if not self.component.bRepBodies.count:
                raise RuntimeError("Cut has no body in this coupon")
            return operations.CutFeatureOperation
        if self.component.bRepBodies.count:
            return operations.JoinFeatureOperation
        return operations.NewBodyFeatureOperation

    def set_cut_participants(self, feature_input, op):
        if op["op"] == "cut":
            feature_input.participantBodies = [
                self.component.bRepBodies.item(index)
                for index in range(self.component.bRepBodies.count)
            ]

    def check_health(self, feature):
        states = self.api.fusion.FeatureHealthStates
        health = feature.healthState
        if health == states.ErrorFeatureHealthState:
            raise RuntimeError(f"{feature.name}: {feature.errorOrWarningMessage}")
        if health == states.WarningFeatureHealthState:
            warning = {
                "component": self.component.name,
                "feature": feature.name,
                "message": feature.errorOrWarningMessage,
            }
            if warning not in self.manifest["warnings"]:
                self.manifest["warnings"].append(warning)

    def primitive(self, op, op_index):
        name = f"{op_index + 1:04d} {op['op']} {op['kind']}"
        operation = self.operation(op)
        if op["kind"] == "cone":
            bottom_sketch, bottom = self.circle_section(
                op["x"], op["y"], op["z"], op["bottom_diameter"], name + " bottom"
            )
            top_sketch, top = self.circle_section(
                op["x"], op["y"], op["z"] + op["height"], op["diameter"], name + " top"
            )
            lofts = self.component.features.loftFeatures
            feature_input = lofts.createInput(operation)
            feature_input.isSolid = True
            feature_input.loftSections.add(bottom)
            feature_input.loftSections.add(top)
            self.set_cut_participants(feature_input, op)
            feature = lofts.add(feature_input)
            sketches = [bottom_sketch, top_sketch]
        else:
            height = op["sz"] if op["kind"] == "box" else op["height"]
            if op["kind"] == "cylinder":
                sketch, profile = self.circle_section(
                    op["x"], op["y"], op["z"], op["diameter"], name + " profile"
                )
            else:
                sketch = self.sketch(op["z"], name + " profile")
                lines = sketch.sketchCurves.sketchLines
                if op["kind"] == "box":
                    x, y = op["x"], op["y"]
                    width, depth = op["sx"], op["sy"]
                    rectangle = lines.addTwoPointRectangle(
                        self.point(x, y), self.point(x + width, y + depth)
                    )
                    rectangle.item(0).startSketchPoint.isFixed = True
                    horizontal = None
                    vertical = None
                    for line_index in range(rectangle.count):
                        line = rectangle.item(line_index)
                        a = line.startSketchPoint.geometry
                        b = line.endSketchPoint.geometry
                        if abs(a.y - b.y) < 1e-9:
                            horizontal = line
                        if abs(a.x - b.x) < 1e-9:
                            vertical = line
                    if horizontal is None or vertical is None:
                        raise RuntimeError(f"{name}: rectangle has no axis-aligned edges")
                    orientations = self.api.fusion.DimensionOrientations
                    width_dimension = sketch.sketchDimensions.addDistanceDimension(
                        horizontal.startSketchPoint, horizontal.endSketchPoint,
                        orientations.HorizontalDimensionOrientation,
                        self.point(x + width / 2, y - 1),
                    )
                    width_dimension.parameter.expression = f"{float(width):.12g} mm"
                    depth_dimension = sketch.sketchDimensions.addDistanceDimension(
                        vertical.startSketchPoint, vertical.endSketchPoint,
                        orientations.VerticalDimensionOrientation,
                        self.point(x + width + 1, y + depth / 2),
                    )
                    depth_dimension.parameter.expression = f"{float(depth):.12g} mm"
                else:
                    points = op["points"]
                    if points[0] == points[-1]:
                        points = points[:-1]
                    previous = None
                    first = None
                    for index, coordinate in enumerate(points):
                        following = points[(index + 1) % len(points)]
                        start = previous.endSketchPoint if previous else self.point(*coordinate)
                        end = first.startSketchPoint if index == len(points) - 1 else self.point(*following)
                        line = lines.addByTwoPoints(start, end)
                        if first is None:
                            first = line
                        previous = line
                profile = self.profile(sketch)
            extrudes = self.component.features.extrudeFeatures
            feature_input = extrudes.createInput(profile, operation)
            feature_input.isSolid = True
            extent = self.api.fusion.DistanceExtentDefinition.create(self.distance(height))
            direction = self.api.fusion.ExtentDirections.PositiveExtentDirection
            if not feature_input.setOneSideExtent(extent, direction):
                raise RuntimeError(f"{name}: cannot set extrusion extent")
            self.set_cut_participants(feature_input, op)
            feature = extrudes.add(feature_input)
            sketches = [sketch]
        if feature is None:
            raise RuntimeError(f"{name}: Fusion did not create a feature")
        feature.name = name
        self.check_health(feature)
        for sketch in sketches:
            sketch.isLightBulbOn = False
        if self.component.bRepBodies.count != 1:
            raise RuntimeError(
                f"{name}: coupon must remain one connected solid; "
                f"got {self.component.bRepBodies.count} bodies"
            )
        return feature

    def part(self, part, part_index, progress, completed):
        root = self.design.rootComponent
        start_index = self.design.timeline.count
        occurrence = root.occurrences.addNewComponent(self.api.core.Matrix3D.create())
        self.component = occurrence.component
        self.component.name = part["name"]
        self.planes = {}
        for op_index, op in enumerate(part["ops"]):
            self.api.doEvents()
            if progress.wasCancelled:
                raise InterruptedError("Coupon generation was cancelled")
            self.manifest["current_operation"] = {
                "part_index": part_index, "part": part["name"],
                "op_index": op_index, "recipe_operation": op,
            }
            progress.message = f"{part['name']}: operation {op_index + 1}/{len(part['ops'])} (%p%)"
            self.primitive(op, op_index)
            completed += 1
            progress.progressValue = completed
            with (self.output_folder / "run_log.jsonl").open("a", encoding="utf-8") as log:
                log.write(json.dumps({
                    "part": part["name"], "op_index": op_index, "status": "built"
                }) + "\n")
        body = self.component.bRepBodies.item(0)
        if not body.isSolid or body.volume <= 0:
            raise RuntimeError(f"{part['name']}: result has no solid volume")
        body.name = part["name"]
        bounds = body.boundingBox
        item = {
            "name": part["name"], "operations": len(part["ops"]),
            "solid_bodies": 1, "volume_mm3": body.volume * 1000,
            "bounds_mm": {
                "minimum": [bounds.minPoint.x * 10, bounds.minPoint.y * 10, bounds.minPoint.z * 10],
                "maximum": [bounds.maxPoint.x * 10, bounds.maxPoint.y * 10, bounds.maxPoint.z * 10],
            },
        }
        self.manifest["built_parts"].append(item)
        end_index = self.design.timeline.count - 1
        if end_index > start_index:
            group = self.design.timeline.timelineGroups.add(start_index, end_index)
            group.name = part["name"]
        _write_manifest(self.output_folder, self.manifest)
        return completed


def run(context):
    """Fusion script entry point; optional dict context can set recipe_path."""
    import adsk.core
    import adsk.fusion

    app = adsk.core.Application.get()
    ui = app.userInterface
    progress = None
    folder = None
    manifest = None
    options = context if isinstance(context, dict) else {}
    recipe_path = Path(options.get("recipe_path", DEFAULT_RECIPE)).resolve()
    show_dialog = options.get("show_dialog", True)
    try:
        recipe, raw, summary = load_recipe(recipe_path)
        digest = hashlib.sha256(raw).hexdigest()
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        prefix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + digest[:8] + "_"
        folder = Path(tempfile.mkdtemp(prefix=prefix, dir=str(OUTPUT_ROOT)))
        (folder / "used_recipe.json").write_bytes(raw)
        manifest = {
            "schema_version": SCHEMA_VERSION, "status": "building",
            "recipe_path": str(recipe_path), "recipe_sha256": digest,
            "units": "mm", "recipe_summary": summary,
            "construction": "native sketches, extrudes and lofts; parametric design",
            "built_parts": [], "warnings": [], "exports": [],
            "fusion_version": app.version,
        }
        _write_manifest(folder, manifest)
        document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        if design is None:
            raise RuntimeError("New document has no Fusion design product")
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        units = adsk.fusion.FusionUnitsManager.cast(design.unitsManager)
        units.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        document.name = f"MIST coupon bed {digest[:8]}"
        design.rootComponent.name = "MIST fit coupon bed"
        design.rootComponent.attributes.add("MISTCoupon", "recipe_sha256", digest)
        progress = ui.createProgressDialog()
        progress.isCancelButtonShown = True
        progress.show("Build MIST coupons", "Preparing sketches (%p%)", 0, summary["operations"], 1)
        builder = CouponBuilder(adsk, design, manifest, folder)
        completed = 0
        for part_index, part in enumerate(recipe["parts"]):
            completed = builder.part(part, part_index, progress, completed)
        design.computeAll()
        for component_index in range(design.allComponents.count):
            component = design.allComponents.item(component_index)
            builder.component = component
            for feature_index in range(component.features.count):
                builder.check_health(component.features.item(feature_index))
        progress.hide()
        progress = None
        manifest.pop("current_operation", None)
        manifest["timeline_entries"] = design.timeline.count
        manifest["status"] = "exporting"
        _write_manifest(folder, manifest)
        manager = design.exportManager
        exports = (
            ("coupon_bed.f3d", manager.createFusionArchiveExportOptions),
            ("coupon_bed.step", manager.createSTEPExportOptions),
        )
        for filename, create_options in exports:
            path = folder / filename
            export_options = create_options(str(path), design.rootComponent)
            if export_options is None or not manager.execute(export_options):
                raise RuntimeError(f"Fusion could not export {filename}")
            if not path.is_file() or path.stat().st_size == 0:
                raise RuntimeError(f"Fusion reported export success but {filename} is missing or empty")
            manifest["exports"].append({
                "path": str(path), "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
            _write_manifest(folder, manifest)
        manifest["status"] = "complete_with_warnings" if manifest["warnings"] else "complete"
        _write_manifest(folder, manifest)
        app.activeViewport.fit()
        app.log(f"MIST coupon exports: {folder}")
        if show_dialog:
            warning_text = f"\nFeature warnings: {len(manifest['warnings'])}. See manifest.json." if manifest["warnings"] else ""
            ui.messageBox(
                f"Created {summary['parts']} coupons in a new design.\n"
                f"F3D and STEP exported to:\n{folder}{warning_text}",
                "MIST fit coupons",
            )
        return manifest
    except Exception as error:
        if progress is not None:
            progress.hide()
        if manifest is not None and folder is not None:
            manifest["status"] = "cancelled" if isinstance(error, InterruptedError) else "failed"
            manifest["error"] = str(error)
            manifest["traceback"] = traceback.format_exc()
            _write_manifest(folder, manifest)
        app.log(traceback.format_exc())
        if show_dialog:
            location = f"\nRun details: {folder / 'manifest.json'}" if folder else ""
            ui.messageBox(f"Coupon generation stopped: {error}{location}", "MIST fit coupons")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a MIST coupon recipe without Fusion.")
    parser.add_argument("--validate", nargs="?", const=str(DEFAULT_RECIPE), required=True,
                        metavar="RECIPE_JSON")
    args = parser.parse_args()
    _, raw, summary = load_recipe(args.validate)
    summary["recipe_sha256"] = hashlib.sha256(raw).hexdigest()
    print(json.dumps(summary, indent=2))
