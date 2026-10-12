"""C018 hardware coordinates, with source and measurement limits explicit."""
from functools import lru_cache
from pathlib import Path
import sys

HARDWARE=Path(__file__).resolve().parent/"hardware"


def _geom():
    import geom
    return geom

CASE_LENGTH=45.23
CASE_WIDTH=24.73
SHAFT_FROM_CASE_CENTER=12.5
CASE_X_MIN=-CASE_LENGTH/2-SHAFT_FROM_CASE_CENTER
CASE_X_MAX=CASE_LENGTH/2-SHAFT_FROM_CASE_CENTER
CASE_HALF_WIDTH=CASE_WIDTH/2
MAIN_FACE_Z=0.0
AUX_FACE_Z=-29.0
MAIN_HORN_OUTER_Z=4.5
AUX_DISC_TOTAL=3.1
AUX_AXIAL_CLEARANCE=.3
AUX_DISC_OUTER_Z=AUX_FACE_Z-AUX_AXIAL_CLEARANCE-AUX_DISC_TOTAL
AUX_STUB_TIP_Z=AUX_FACE_Z-4.1
CHEEK_INNER_AUX_Z=-36.5
AUX_STANDOFF=CHEEK_INNER_AUX_Z*-1+AUX_DISC_OUTER_Z

# Supplier shell access region; these are not measured plug dimensions.
PORT_X=(-17.35,-11.65)
PORT_HALF_WIDTH=10.7
PORT_IN_PLANE_ALLOWANCE=1.0
# The user's approximately 35 mm unplugged profile and 1.5 mm added plug
# projection have no shaft datum. This maps that measurement provisionally
# to the supplier shell's measured -32.4 mm rear profile.
REFERENCE_REAR_PROFILE_Z=-32.4
USER_ADDED_PLUG_PROJECTION=1.5
USER_WIRE_CLEARANCE=2.0
PORT_CLEARANCE_OUTER_Z=(REFERENCE_REAR_PROFILE_Z-USER_ADDED_PLUG_PROJECTION-USER_WIRE_CLEARANCE)

END_CLEARANCE=.3
CLAMP_BOLT_OFFSET=3.8
CLAMP_END_LAND=4.2
CLAMP_REAR_BOLT_X=CASE_X_MIN-CLAMP_BOLT_OFFSET
CLAMP_FRONT_BOLT_X=CASE_X_MAX+CLAMP_BOLT_OFFSET
CLAMP_X_MIN=CLAMP_REAR_BOLT_X-CLAMP_END_LAND
CLAMP_X_MAX=CLAMP_FRONT_BOLT_X+CLAMP_END_LAND
CLAMP_BOLT_XZ=((CLAMP_REAR_BOLT_X,-5.5),(CLAMP_FRONT_BOLT_X,-23.0),(CLAMP_FRONT_BOLT_X,-7.0))


def box_bounds(x0,x1,y0,y1,z0,z1):
    return _geom().box(x1-x0,y1-y0,z1-z0,((x0+x1)/2,(y0+y1)/2,(z0+z1)/2))


def plugged_profile_reserve():
    """Provisional plugged-profile clearance, along auxiliary-face -Z."""
    return box_bounds(PORT_X[0]-PORT_IN_PLANE_ALLOWANCE,
                      PORT_X[1]+PORT_IN_PLANE_ALLOWANCE,
                      -PORT_HALF_WIDTH-PORT_IN_PLANE_ALLOWANCE,
                      PORT_HALF_WIDTH+PORT_IN_PLANE_ALLOWANCE,
                      PORT_CLEARANCE_OUTER_Z,AUX_FACE_Z+.5)


def supplier_to_servo(shape):
    geom=_geom()
    # Supplier output axis is X=-25.5,Z=0 and the main case face is Y=4.9.
    return geom.translate(geom.rotate(geom.rotate(shape,(0,1,0),180),(1,0,0),90),(-25.5,0,-4.9))


@lru_cache(maxsize=1)
def supplier_case_reference():
    """Compatible supplier exterior, excluding fitted horns and internals.

    The 2022 supplier STEP is not certified as the exact owned C018 build.
    Its footprint and shaft location agree with the C018 drawing within
    0.004 mm. Using its shell also retains the previously omitted steps.
    """
    geom=_geom()
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_SOLID,TopAbs_SHELL
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid
    from OCP.TopoDS import TopoDS
    reader=STEPControl_Reader()
    reader.ReadFile(str(HARDWARE/"ST3215.step"))
    reader.TransferRoots()
    solids=[]
    explorer=TopExp_Explorer(reader.OneShape(),TopAbs_SOLID)
    while explorer.More():
        solids.append(explorer.Current());explorer.Next()
    # The supplier rear solid contains seven invalidly nested tiny internal
    # void shells. Its exterior shell is independently valid. Filling those
    # 17.213290 mm3 of voids gives a conservative exterior collision solid.
    outer=TopExp_Explorer(solids[2],TopAbs_SHELL)
    rear=BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(outer.Current())).Solid()
    shells=[supplier_to_servo(solids[i]) for i in (0,1)]+[supplier_to_servo(rear)]
    return geom.fuse(*shells,geom.cylinder(2.95,3.4,(0,0,0)))
