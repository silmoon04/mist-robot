"""Native Fusion solids for the MIST mechanical study.

Public lengths and points use millimetres in the supplied component's local
coordinates. Direction vectors are dimensionless. Constructors return one
``adsk.fusion.BRepBody`` and require a parametric design. Build component geometry
with its occurrence at identity, then position the occurrence with ``transform2``.

Each part uses a sketch, extrusion and, when needed, a native Move feature. The
shape dimensions remain editable in the timeline. Numeric sketch coordinates and
placement matrices are generation-linked; editing a design-level user parameter
does not automatically regenerate them. The construction sketch stays on XY when
the resulting solid is moved. No mesh, temporary BRep or BaseFeature is used.

Failed features, disconnected joins and cuts that do not remove material raise
exceptions. A failed call can leave its construction features in the document;
the caller should discard or inspect that build rather than assume success.
"""

import itertools
import math

import adsk.core
import adsk.fusion


__all__ = [
    "polygon", "extruded_polygon", "capsule", "plate", "box", "cylinder",
    "annulus", "hole", "through_hole", "union", "subtract",
    "c018_reference", "bearing_reference",
]

_EPS = 1.0e-9


def _xyz(value, label="point"):
    result = tuple(float(v) for v in value)
    if len(result) != 3 or not all(math.isfinite(v) for v in result):
        raise ValueError("{} must contain three finite numbers".format(label))
    return result


def _positive(value, label):
    result = float(value)
    if not math.isfinite(result) or result <= _EPS:
        raise ValueError("{} must be a positive finite length in mm".format(label))
    return result


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _subtract(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _scale(a, value):
    return tuple(x * value for x in a)


def _unit(value, label="direction"):
    result = _xyz(value, label)
    length = math.sqrt(_dot(result, result))
    if length <= _EPS:
        raise ValueError("{} cannot be zero".format(label))
    return _scale(result, 1.0 / length)


def _basis(normal, x_axis=None):
    """Return a proper rotation; project the supplied X direction into the plane."""
    z = _unit(normal, "normal")
    if x_axis is None:
        x_axis = min(((1., 0., 0.), (0., 1., 0.), (0., 0., 1.)),
                     key=lambda candidate: abs(_dot(candidate, z)))
    candidate = _unit(x_axis, "x_axis")
    x = _unit(_subtract(candidate, _scale(z, _dot(candidate, z))),
              "x_axis projected into the plane")
    y = _unit(_cross(z, x))
    return x, y, z


def _point_mm(point):
    return adsk.core.Point3D.create(*(coordinate / 10.0 for coordinate in point))


def _length_mm(value):
    return adsk.core.ValueInput.createByString("{:.12g} mm".format(value))


def _collection(values):
    collection = adsk.core.ObjectCollection.create()
    for value in values:
        if not collection.add(value):
            raise RuntimeError("Could not add an entity to the Fusion collection")
    return collection


def _check_component(component):
    if component is None or not component.isValid:
        raise ValueError("A valid Fusion component is required")
    if component.parentDesign.designType != adsk.fusion.DesignTypes.ParametricDesignType:
        raise ValueError("native_parts requires a parametric Fusion design")


def _check_body(component, body):
    _check_component(component)
    if body is None or not body.isValid or not body.isSolid:
        raise ValueError("A valid solid body is required")
    if body.assemblyContext is not None or body.parentComponent != component:
        raise ValueError("Use native bodies belonging to the supplied component")


def _feature_body(feature, name):
    if feature is None or not feature.isValid:
        raise RuntimeError("{}: Fusion did not create a valid feature".format(name))
    feature.name = name
    if feature.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        raise RuntimeError("{}: {}".format(
            name, feature.errorOrWarningMessage or "feature is not healthy"))
    if feature.bodies.count != 1:
        raise RuntimeError("{}: expected one body, got {}".format(name, feature.bodies.count))
    body = feature.bodies.item(0)
    if not body.isValid or not body.isSolid or body.volume <= 0:
        raise RuntimeError("{}: result is not a non-empty solid".format(name))
    return body


def _sketch(component, name):
    _check_component(component)
    sketch = component.sketches.add(component.xYConstructionPlane)
    if sketch is None:
        raise RuntimeError("{}: Fusion did not create the sketch".format(name))
    sketch.name = name + " profile"
    return sketch


def _profile(sketch, name, loops=1):
    matches = [sketch.profiles.item(i) for i in range(sketch.profiles.count)
               if sketch.profiles.item(i).profileLoops.count == loops]
    if len(matches) != 1:
        raise RuntimeError("{}: expected one profile with {} loop(s), got {}".format(
            name, loops, len(matches)))
    return matches[0]


def _extrude(component, sketch, profile, length, name):
    extrudes = component.features.extrudeFeatures
    feature_input = extrudes.createInput(
        profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    if feature_input is None:
        raise RuntimeError("{}: could not define extrusion".format(name))
    extent = adsk.fusion.DistanceExtentDefinition.create(_length_mm(length))
    if extent is None or not feature_input.setOneSideExtent(
            extent, adsk.fusion.ExtentDirections.PositiveExtentDirection):
        raise RuntimeError("{}: could not set extrusion extent".format(name))
    body = _feature_body(extrudes.add(feature_input), name + " extrusion")
    sketch.isVisible = False
    body.name = name
    return body


def _place(component, body, origin, normal, x_axis, name):
    origin = _xyz(origin, "origin")
    axes = _basis(normal, x_axis)
    matrix = adsk.core.Matrix3D.create()
    vectors = [adsk.core.Vector3D.create(*axis) for axis in axes]
    if not matrix.setWithCoordinateSystem(_point_mm(origin), *vectors):
        raise RuntimeError("{}: could not construct placement matrix".format(name))
    if matrix.isEqualTo(adsk.core.Matrix3D.create()):
        return body
    moves = component.features.moveFeatures
    feature_input = moves.createInput2(_collection([body]))
    if feature_input is None or not feature_input.defineAsFreeMove(matrix):
        raise RuntimeError("{}: could not define native move".format(name))
    result = _feature_body(moves.add(feature_input), name + " placement")
    result.name = name
    return result


def polygon(component, name, points_xy, thickness, origin=(0, 0, 0),
            normal=(0, 0, 1), x_axis=None):
    """Extrude a closed XY polygon from ``origin`` along ``normal``.

    ``points_xy`` are 2D offsets from origin. X follows ``x_axis`` projected into
    the plane, Y completes a right-handed basis. The first point may be repeated
    at the end. The caller supplies a simple, non-self-intersecting contour.
    """
    thickness = _positive(thickness, "thickness")
    points = [tuple(float(v) for v in point) for point in points_xy]
    if any(len(point) != 2 or not all(math.isfinite(v) for v in point) for point in points):
        raise ValueError("points_xy must contain finite pairs")
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    if len(points) < 3 or len(set(points)) != len(points):
        raise ValueError("A polygon needs at least three distinct vertices")
    pairs = list(zip(points, points[1:] + points[:1]))
    if any(math.hypot(a[0] - b[0], a[1] - b[1]) <= _EPS for a, b in pairs):
        raise ValueError("A polygon cannot contain zero-length edges")
    if abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in pairs)) <= _EPS:
        raise ValueError("A polygon must have non-zero area")
    _xyz(origin, "origin")
    _basis(normal, x_axis)
    sketch = _sketch(component, name)
    sketch.isComputeDeferred = True
    try:
        lines = sketch.sketchCurves.sketchLines
        first = _point_mm((*points[0], 0))
        previous = first
        first_entity = None
        for index, point in enumerate(points[1:]):
            line = lines.addByTwoPoints(previous, _point_mm((*point, 0)))
            if line is None:
                raise RuntimeError("{}: could not add polygon edge".format(name))
            if index == 0:
                first_entity = line.startSketchPoint
            previous = line.endSketchPoint
        if lines.addByTwoPoints(previous, first_entity) is None:
            raise RuntimeError("{}: could not close polygon".format(name))
    finally:
        sketch.isComputeDeferred = False
    body = _extrude(component, sketch, _profile(sketch, name), thickness, name)
    return _place(component, body, origin, normal, x_axis, name)


def capsule(component, name, start, end, width, thickness, normal=(0, 0, 1)):
    """Create a round-ended plate with endpoint arc centers at start and end.

    Both points lie on the bottom face. Thickness extends along normal; width
    extends equally on either side of the centerline. Width and center distance
    have native driving sketch dimensions.
    """
    start, end = _xyz(start, "start"), _xyz(end, "end")
    direction = _subtract(end, start)
    length = _positive(math.sqrt(_dot(direction, direction)), "center distance")
    width, thickness = _positive(width, "width"), _positive(thickness, "thickness")
    if abs(_dot(_unit(direction), _unit(normal))) > 1.0e-8:
        raise ValueError("Capsule centerline must be perpendicular to normal")
    sketch = _sketch(component, name)
    geometry = sketch.addCenterToCenterSlot(
        _point_mm((0, 0, 0)), _point_mm((length, 0, 0)),
        _length_mm(width), True, _length_mm(length))
    if not geometry:
        raise RuntimeError("{}: could not create capsule sketch".format(name))
    body = _extrude(component, sketch, _profile(sketch, name), thickness, name)
    return _place(component, body, start, normal, direction, name)


def box(component, name, center, size):
    """Create an axis-aligned box; center is its volume center and size is XYZ."""
    center, size = _xyz(center, "center"), _xyz(size, "size")
    sx, sy, sz = (_positive(value, "size") for value in size)
    return polygon(component, name,
                   [(-sx / 2, -sy / 2), (sx / 2, -sy / 2),
                    (sx / 2, sy / 2), (-sx / 2, sy / 2)], sz,
                   origin=(center[0], center[1], center[2] - sz / 2))


def _circle(sketch, radius, label):
    circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
        _point_mm((0, 0, 0)), radius / 10.0)
    if circle is None:
        raise RuntimeError("{}: could not create circle".format(label))
    dimension = sketch.sketchDimensions.addDiameterDimension(
        circle, _point_mm((radius * 1.2, radius * 1.2, 0)))
    if dimension is None:
        raise RuntimeError("{}: could not dimension circle".format(label))
    dimension.parameter.expression = "{:.12g} mm".format(radius * 2.0)
    return circle


def cylinder(component, name, start, end, radius):
    """Create a cylinder between the centers of its two flat ends."""
    start, end = _xyz(start, "start"), _xyz(end, "end")
    direction = _subtract(end, start)
    length = _positive(math.sqrt(_dot(direction, direction)), "cylinder length")
    radius = _positive(radius, "radius")
    sketch = _sketch(component, name)
    _circle(sketch, radius, name)
    body = _extrude(component, sketch, _profile(sketch, name), length, name)
    return _place(component, body, start, direction, None, name)


def annulus(component, name, start, end, outer_radius, inner_radius):
    """Create a ring with exact circular faces; radii are not diameters."""
    start, end = _xyz(start, "start"), _xyz(end, "end")
    direction = _subtract(end, start)
    length = _positive(math.sqrt(_dot(direction, direction)), "ring length")
    outer_radius = _positive(outer_radius, "outer_radius")
    inner_radius = _positive(inner_radius, "inner_radius")
    if inner_radius >= outer_radius:
        raise ValueError("inner_radius must be smaller than outer_radius")
    sketch = _sketch(component, name)
    _circle(sketch, outer_radius, name + " outside")
    _circle(sketch, inner_radius, name + " bore")
    body = _extrude(component, sketch, _profile(sketch, name, loops=2), length, name)
    return _place(component, body, start, direction, None, name)


def _combine(component, target, tools, name, operation):
    _check_body(component, target)
    tools = list(tools)
    if not tools:
        raise ValueError("A combine requires at least one tool body")
    for tool in tools:
        _check_body(component, tool)
        if tool == target:
            raise ValueError("Target body cannot also be a tool")
    before_volume = target.volume
    combines = component.features.combineFeatures
    feature_input = combines.createInput(target, _collection(tools))
    if feature_input is None:
        raise RuntimeError("{}: could not define combine".format(name))
    feature_input.operation = operation
    feature_input.isKeepToolBodies = False
    feature_input.isNewComponent = False
    result = _feature_body(combines.add(feature_input), name)
    after_volume = result.volume
    if operation == adsk.fusion.FeatureOperations.CutFeatureOperation:
        if not after_volume < before_volume - max(1.0e-10, before_volume * 1.0e-10):
            raise RuntimeError("{}: cut did not remove measurable material".format(name))
    elif after_volume < before_volume - max(1.0e-10, before_volume * 1.0e-10):
        raise RuntimeError("{}: join unexpectedly reduced target volume".format(name))
    result.name = name
    return result


def union(component, target, tools, name):
    """Join touching or overlapping native solids; consume tools and return one body."""
    return _combine(component, target, tools, name,
                    adsk.fusion.FeatureOperations.JoinFeatureOperation)


def subtract(component, target, tools, name):
    """Cut only target, consume tools and require one remaining non-empty solid."""
    return _combine(component, target, tools, name,
                    adsk.fusion.FeatureOperations.CutFeatureOperation)


def hole(component, body, name, start, end, radius):
    """Cut a finite cylindrical bore between start and end; radius is in mm.

    ``name`` labels the cut feature; the target body's name is preserved. For a
    through bore, choose endpoints outside both target faces or use through_hole,
    which computes endpoints from the target bounding box.
    """
    _check_body(component, body)
    body_name = body.name
    cutter = cylinder(component, name + " cutter", start, end, radius)
    result = subtract(component, body, [cutter], name)
    result.name = body_name
    return result


def through_hole(component, body, name, center, axis, radius, margin=1.0):
    """Cut along a line through center, extending beyond the body's bounding box."""
    _check_body(component, body)
    center, axis = _xyz(center, "center"), _unit(axis, "axis")
    margin = _positive(margin, "margin")
    bounds = body.boundingBox
    minimum = (bounds.minPoint.x * 10, bounds.minPoint.y * 10, bounds.minPoint.z * 10)
    maximum = (bounds.maxPoint.x * 10, bounds.maxPoint.y * 10, bounds.maxPoint.z * 10)
    corners = itertools.product(*zip(minimum, maximum))
    distances = [_dot(_subtract(corner, center), axis) for corner in corners]
    start = _add(center, _scale(axis, min(distances) - margin))
    end = _add(center, _scale(axis, max(distances) + margin))
    return hole(component, body, name, start, end, radius)


def c018_reference(component, name, origin, normal=(0, 0, 1),
                   x_axis=None, size=(45.2, 24.7, 35.0)):
    """Create the C018 case envelope, centered on its bottom face at origin.

    Local X/Y/Z follow case length/width/height. This is a packaging reference,
    with no mounting ears, screw locations, horn, cable or spline implied. The
    default case dimensions come from the C018 specification cited in
    ../mechanical_audit.md; measure the delivered actuator before mount release.
    """
    sx, sy, sz = (_positive(value, "case size") for value in _xyz(size, "size"))
    body = polygon(component, name,
                   [(-sx / 2, -sy / 2), (sx / 2, -sy / 2),
                    (sx / 2, sy / 2), (-sx / 2, sy / 2)], sz,
                   origin, normal, x_axis)
    body.attributes.add("mist_v2", "role", "reference_case_envelope")
    return body


def bearing_reference(component, name, start, axis, od, id, width):
    """Create a bearing's nominal OD/ID/width envelope from its first face.

    The ring represents packaging only. It has no modeled rolling elements,
    preload, fits, chamfers or load-rating claim.
    """
    start, axis = _xyz(start, "start"), _unit(axis, "axis")
    width = _positive(width, "bearing width")
    body = annulus(component, name, start, _add(start, _scale(axis, width)),
                   _positive(od, "bearing OD") / 2.0,
                   _positive(id, "bearing ID") / 2.0)
    body.attributes.add("mist_v2", "role", "reference_bearing_envelope")
    return body


extruded_polygon = polygon
plate = capsule
