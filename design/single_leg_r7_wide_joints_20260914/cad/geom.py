"""Direct OpenCascade helpers. Geometry is in millimetres; angles are degrees."""

from __future__ import annotations

import math
from pathlib import Path

from OCP.BRep import BRep_Builder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_Transform,
)
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepPrimAPI import (
    BRepPrimAPI_MakeBox,
    BRepPrimAPI_MakeCylinder,
    BRepPrimAPI_MakePrism,
)
from OCP.Bnd import Bnd_Box
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Reader, STEPControl_Writer
from OCP.StlAPI import StlAPI_Writer
from OCP.TopoDS import TopoDS_Compound, TopoDS_Shape
from OCP.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec


def _xyz(value):
    result = tuple(float(v) for v in value)
    if len(result) != 3 or not all(math.isfinite(v) for v in result):
        raise ValueError("Expected three finite coordinates")
    return result


def _positive(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def _checked(builder, operation):
    shape = builder.Shape()
    if not builder.IsDone() or shape.IsNull():
        raise RuntimeError(f"{operation} did not produce a shape")
    return shape


def box(dx, dy, dz, center=(0, 0, 0)):
    """Return an axis-aligned solid centered at center."""
    dx, dy, dz = (_positive(v, n) for v, n in zip((dx, dy, dz), ("dx", "dy", "dz")))
    x, y, z = _xyz(center)
    return _checked(
        BRepPrimAPI_MakeBox(gp_Pnt(x - dx / 2, y - dy / 2, z - dz / 2), dx, dy, dz),
        "box",
    )


def cylinder(radius, height, base=(0, 0, 0), axis=(0, 0, 1)):
    """Return a cylinder from base along the normalized axis."""
    radius, height = _positive(radius, "radius"), _positive(height, "height")
    frame = gp_Ax2(gp_Pnt(*_xyz(base)), gp_Dir(*_xyz(axis)))
    return _checked(BRepPrimAPI_MakeCylinder(frame, radius, height), "cylinder")


def _prism(points, vector):
    polygon = BRepBuilderAPI_MakePolygon()
    vertices = [_xyz(point) for point in points]
    if vertices and vertices[-1] == vertices[0]:
        vertices.pop()
    if len(vertices) < 3:
        raise ValueError("A prism needs at least three polygon vertices")
    for point in vertices:
        polygon.Add(gp_Pnt(*point))
    polygon.Close()
    if not polygon.IsDone():
        raise ValueError("Could not close prism polygon")
    face = BRepBuilderAPI_MakeFace(polygon.Wire(), True)
    if not face.IsDone():
        raise ValueError("Prism polygon must be planar and nondegenerate")
    shape = _checked(BRepPrimAPI_MakePrism(face.Face(), gp_Vec(*vector)), "prism")
    if not valid(shape):
        raise ValueError("Prism polygon produced invalid geometry")
    return shape


def prism_xy(points, z0, height):
    """Extrude an ordered (x,y) polygon from z0 toward positive Z."""
    return _prism([(x, y, z0) for x, y in points], (0, 0, _positive(height, "height")))


def prism_xz(points, y0, thickness):
    """Extrude an ordered (x,z) polygon from y0 toward positive Y."""
    return _prism([(x, y0, z) for x, z in points], (0, _positive(thickness, "thickness"), 0))


def _boolean(operation, a, b, name):
    builder = operation(a, b)
    builder.Build()
    if not builder.IsDone():
        raise RuntimeError(f"{name} failed")
    builder.SimplifyResult(True, True)
    shape = builder.Shape()
    if shape.IsNull() or not valid(shape):
        raise RuntimeError(f"{name} produced invalid geometry")
    return shape


def fuse(*shapes):
    """Boolean union; disconnected solids remain a compound."""
    if not shapes:
        raise ValueError("fuse needs at least one shape")
    result = shapes[0]
    for shape in shapes[1:]:
        result = _boolean(BRepAlgoAPI_Fuse, result, shape, "fuse")
    return result


def cut(shape, *tools):
    """Subtract each tool from the shape."""
    result = shape
    for tool in tools:
        result = _boolean(BRepAlgoAPI_Cut, result, tool, "cut")
    return result


def translate(shape, xyz):
    motion = gp_Trsf()
    motion.SetTranslation(gp_Vec(*_xyz(xyz)))
    return _checked(BRepBuilderAPI_Transform(shape, motion, True), "translation")


def rotate(shape, axis, degrees, origin=(0, 0, 0)):
    """Rotate right-handed around an axis through origin."""
    angle = float(degrees)
    if not math.isfinite(angle):
        raise ValueError("Rotation angle must be finite")
    motion = gp_Trsf()
    motion.SetRotation(gp_Ax1(gp_Pnt(*_xyz(origin)), gp_Dir(*_xyz(axis))), math.radians(angle))
    return _checked(BRepBuilderAPI_Transform(shape, motion, True), "rotation")


def transform(shape, translation=(0, 0, 0), rpy_deg=(0, 0, 0)):
    """Apply Rz(yaw) Ry(pitch) Rx(roll), then world translation."""
    result = shape
    for axis, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), _xyz(rpy_deg)):
        if angle:
            result = rotate(result, axis, angle)
    return translate(result, translation)


def _properties(shape):
    if shape.IsNull():
        raise ValueError("Cannot measure a null shape")
    properties = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, properties, True, False, False)
    return properties


def volume(shape):
    """Return signed solid volume in mm^3."""
    return float(_properties(shape).Mass())


def centroid(shape):
    """Return the volume centroid in millimetres."""
    properties = _properties(shape)
    if abs(properties.Mass()) < 1e-12:
        raise ValueError("A zero-volume shape has no volume centroid")
    p = properties.CentreOfMass()
    return (p.X(), p.Y(), p.Z())


def inertia(shape):
    """Return a 3x3 inertia matrix about the centroid at density 1, in mm^5."""
    properties = _properties(shape)
    if abs(properties.Mass()) < 1e-12:
        raise ValueError("A zero-volume shape has no volume inertia")
    matrix = properties.MatrixOfInertia()
    return tuple(tuple(matrix.Value(i, j) for j in (1, 2, 3)) for i in (1, 2, 3))


def bounds(shape):
    """Return ((xmin,ymin,zmin), (xmax,ymax,zmax)) in millimetres."""
    bb = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, bb, False, False)
    if bb.IsVoid() or bb.IsOpen():
        raise ValueError("Cannot bound an empty or unbounded shape")
    values = bb.Get()
    return (tuple(values[:3]), tuple(values[3:]))


def valid(shape):
    return not shape.IsNull() and bool(BRepCheck_Analyzer(shape).IsValid())


def common_volume(a, b):
    """Return intersection volume; face or edge contact returns zero."""
    builder = BRepAlgoAPI_Common(a, b)
    builder.Build()
    if not builder.IsDone():
        raise RuntimeError("Intersection failed")
    shape = builder.Shape()
    if shape.IsNull():
        return 0.0
    if not valid(shape):
        raise RuntimeError("Intersection produced invalid geometry")
    return max(0.0, volume(shape))


def compound(shapes):
    """Collect shapes without fusing or changing their individual geometry."""
    result = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(result)
    count = 0
    for shape in shapes:
        if shape.IsNull():
            raise ValueError("Cannot compound a null shape")
        builder.Add(result, shape)
        count += 1
    if not count:
        raise ValueError("compound needs at least one shape")
    return result


def export_step(shapes, path):
    """Write one shape or an iterable of separate shapes as a STEP file."""
    items = [shapes] if isinstance(shapes, TopoDS_Shape) else list(shapes)
    if not items:
        raise ValueError("STEP export needs at least one shape")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    Interface_Static.SetCVal_s("write.step.unit", "MM")
    writer = STEPControl_Writer()
    for shape in items:
        if not valid(shape) or writer.Transfer(shape, STEPControl_AsIs) != IFSelect_RetDone:
            raise RuntimeError("STEP shape transfer failed")
    if writer.Write(str(destination)) != IFSelect_RetDone:
        raise RuntimeError(f"STEP write failed: {destination}")
    return destination


def export_stl(shape, path, deflection=0.08):
    """Write binary STL using absolute deflection in mm and 0.25 rad angular tolerance."""
    if not valid(shape):
        raise ValueError("Cannot export invalid geometry")
    deflection = _positive(deflection, "deflection")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    mesh = BRepMesh_IncrementalMesh(shape, deflection, False, 0.25, False)
    mesh.Perform()
    if not mesh.IsDone():
        raise RuntimeError("STL tessellation failed")
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    if not writer.Write(shape, str(destination)):
        raise RuntimeError(f"STL write failed: {destination}")
    return destination


def import_step(path):
    """Read all STEP roots as one shape, converting length units to millimetres."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    reader = STEPControl_Reader()
    if reader.ReadFile(str(source)) != IFSelect_RetDone:
        raise RuntimeError(f"STEP read failed: {source}")
    reader.SetSystemLengthUnit(1.0)
    if reader.TransferRoots() < 1:
        raise RuntimeError(f"STEP contained no transferable roots: {source}")
    shape = reader.OneShape()
    if not valid(shape):
        raise RuntimeError(f"STEP import produced invalid geometry: {source}")
    return shape
