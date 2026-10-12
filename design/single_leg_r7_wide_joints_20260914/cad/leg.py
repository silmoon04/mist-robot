"""Video-derived direct-drive leg. All lengths are millimetres.

Each returned shape uses its owning link frame. X runs out along the leg;
Y is left and Z is up. Positive pitch about Y tips X down. Horn seating,
case fit and auxiliary axial float remain coupon measurements.
"""

from __future__ import annotations

import math
import servo_contract as sc

from geom import box, cylinder, prism_xy, prism_xz, fuse, cut, translate, rotate
from geom import bounds, valid, volume


CONSTANTS = {
    "case_x": (sc.CASE_X_MIN,sc.CASE_X_MAX),
    "case_width": 24.73,
    "hip_servo_tail_out": False,
    "hip_clamp_bolt_xz": ((sc.CLAMP_REAR_BOLT_X,-27.5),(sc.CLAMP_FRONT_BOLT_X,-23.0),(sc.CLAMP_FRONT_BOLT_X,-7.0)),
    "case_main_depth": 29.0,
    "case_rear_profile_depth": 32.0,
    "case_end_clearance": 0.3,
    "split_cap_gap": 0.8,
    "main_horn_outer_plane": 4.5,
    "auxiliary_disc_outer_plane": sc.AUX_DISC_OUTER_Z,
    "pitch_main_face_y": 14.5,
    "pitch_auxiliary_face_y": -14.5,
    "pitch_main_cheek_inner_y": 19.0,
    "pitch_auxiliary_cheek_inner_y": -22.0,
    "cheek_thickness": 4.0,
    "auxiliary_center_access_diameter": 8.4,
    "horn_pcd": 14.0,
    "mount_holes_xy": [(-29.0, -20.0), (-29.0, 20.0), (9.0, -20.0), (9.0, 20.0)],
    "yaw_clamp_mount_z": -32.0,
    "yaw_lower_plate_z": (-53.0, -44.0),
    "yaw_auxiliary_spacer_length": 11.6,
    "yaw_auxiliary_counterbore_diameter": 8.2,
    "yaw_auxiliary_counterbore_depth": 3.5,
    "coxa_post_holes_xy": ((40.5,-4.5),(40.5,4.5)),
    "coxa_post_nut_z_ranges": ((-41.5,-38.8),(-37.5,-34.8)),
    "femur_bridge_bounds_xz": ((58.0,13.5),(72.0,27.5)),
    "femur_bridge_bolt_xz": ((65.0,20.5),),
    "tibia_bridge_bounds_xz": ((32.0,-7.0),(48.0,7.0)),
    "tibia_bridge_bolt_xz": ((36.0,0.0),(44.0,0.0)),
    "cheek_inward_rib_depth": 4.0,
    "cheek_edge_rib_height": 4.0,
    "auxiliary_rib_near_joint_depth": 1.0,
    "auxiliary_case_clamp_radial_relief": 44.5,
    "hip_joint_xyz": (82.0, 0.0, 0.0),
    "knee_joint_xyz": (90.0, 0.0, 0.0),
    "toe_center_xyz": (105.0, 0.0, 0.0),
    "toe_pad_width": 14.0,
    "toe_radius": 5.0,
    "toe_plane_below_center": 4.8,
    "toe_nominal_total_pitch_deg": 105.0,
}

PROVISIONAL_JOINT_LIMITS_DEG = {"yaw": (-55,55), "hip": (-30,65), "knee": (5,115)}
# Limits bound sampled checks. They are not a continuous collision proof.
PRINT_ROTATIONS = {
    "yaw_case_saddle": (0,0,0), "case_cap_yaw": (90,0,0),
    "coxa_upper_and_hip_saddle": (90,0,0),
    "coxa_lower_auxiliary_arm": (0,0,0),
    "case_cap_hip": (0,0,0), "case_cap_knee": (0,0,0),
    "femur_main_and_knee_saddle": (-90,0,0),
    "femur_auxiliary_cheek": (90,0,0),
    "tibia_curved_main_and_foot": (-90,0,0),
    "tibia_auxiliary_cheek": (90,0,0),
}


def _b(x0, x1, y0, y1, z0, z1):
    return box(x1-x0, y1-y0, z1-z0, ((x0+x1)/2, (y0+y1)/2, (z0+z1)/2))


def _prism_yz(points, x0, width):
    return rotate(prism_xz(points,-x0-width,width),(0,0,1),90)


def _crop(shape, region):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    operation=BRepAlgoAPI_Common(shape,region)
    operation.Build()
    if not operation.IsDone() or not valid(operation.Shape()):
        raise RuntimeError("Could not extract the representative strength section")
    return operation.Shape()


def _edge_rib(points, direction, y0):
    """Add a 4 mm inward flange within a cheek's top or bottom outline."""
    height=CONSTANTS["cheek_edge_rib_height"]
    polygon=points+[(x,z+direction*height) for x,z in reversed(points)]
    rib=prism_xz(polygon,y0,CONSTANTS["cheek_inward_rib_depth"])
    return cut(rib,cylinder(11,12,(0,-25 if y0<0 else 14,0),(0,1,0)))


def _hex_z(x, y, z, depth=2.6, across_flats=5.6):
    radius = across_flats / math.sqrt(3)
    return prism_xy([(x + radius*math.cos(math.radians(30+60*i)),
                      y + radius*math.sin(math.radians(30+60*i)))
                     for i in range(6)], z, depth)


def _hex_y(x, y, z, depth=2.6):
    shape = _hex_z(x, -z, 0, depth)
    return translate(rotate(shape, (1, 0, 0), -90), (0, y, 0))


def _hole_y(x, z, y0=-35, length=70, radius=1.7):
    return cylinder(radius, length, (x, y0, z), (0, 1, 0))


def _horn_holes_y(shape, x=0, z=0):
    return cut(shape, _hole_y(x, z, radius=3.5),
               *[_hole_y(x+dx, z+dz) for dx, dz in ((7,0),(-7,0),(0,7),(0,-7))])


def _horn_holes_z(shape):
    return cut(shape, cylinder(3.5, 80, (0, 0, -55)),
               *[cylinder(1.7, 80, (x, y, -55)) for x, y in ((7,0),(-7,0),(0,7),(0,-7))])


def _pitch(shape, tail_out=False, origin_x=0):
    if tail_out:
        shape = rotate(shape, (0, 0, 1), 180)
    return translate(rotate(shape, (1, 0, 0), -90), (origin_x, 14.5, 0))


def servo_envelope():
    return sc.supplier_case_reference()


def main_horn():
    shape = fuse(cylinder(9.975, 2.5, (0, 0, 2)),
                 cylinder(4.5, 1.1, (0, 0, 0.9)))
    return cut(shape, cylinder(2.95, 5, (0, 0, 0)),
               *[cylinder(1.25, 5, (x, y, 0)) for x, y in ((7,0),(-7,0),(0,7),(0,-7))])


def auxiliary_disc():
    shape = fuse(cylinder(9.975, 2.1, (0, 0, sc.AUX_DISC_OUTER_Z)),
                 cylinder(4.5, 1.0, (0, 0, sc.AUX_DISC_OUTER_Z+2.1)))
    return cut(shape, cylinder(3.025, 5, (0, 0, -34)),
               *[cylinder(1.25, 5, (x, y, -34)) for x, y in ((7,0),(-7,0),(0,7),(0,-7))])


def case_clamp(with_mount_feet=False, end_clearance=0.3, roof_up=1):
    """Saddle and adjustable side cap; the 0.8 mm closure gap remains open.

    The fixed -Y and moving +Y rails contact the nominal case. End walls
    locate X with clearance. Shelves support the 29 mm case face while
    leaving the rear 32 mm profile and auxiliary shaft free. M3 bolts pass
    through exterior end walls, clear of the case and connector opening.
    """
    xlo, xhi = sc.CASE_X_MIN-end_clearance,sc.CASE_X_MAX+end_clearance
    xmin,xmax=sc.CLAMP_X_MIN,sc.CLAMP_X_MAX
    saddle = fuse(_b(xmin,xmax,-16.365,-12.365,-32,-2),
                  _b(xmin,xlo,-16.365,11.565,-29,-2),
                  _b(xhi,xmax,-16.365,11.565,-29,-2),
                  _b(-4,4,-12.365,-11.5,-32,-29.4),
                  _b(xhi,xmax-1,-12.365,11.565,-32,-28.9))
    cap=_b(xmin,xmax,12.365,16.365,-29,-2)
    bolt_tools = []
    for x,z in sc.CLAMP_BOLT_XZ:
        bolt_tools.append(_hole_y(x, z, -18, 38))
        saddle = cut(saddle, _hex_y(x, -16.5, z, 2.8))
    saddle = cut(saddle, *bolt_tools)
    cap = cut(cap, *bolt_tools)
    if with_mount_feet:
        feet=[_b(xmin,xlo,-25.5,25.5,-32,-29),
              _b(xhi,xmax,-25.5,25.5,-32,-29)]
        for x, y in CONSTANTS["mount_holes_xy"]:
            half_x=7 if x<0 else 6
            feet.append(_b(x-half_x,x+half_x,y-6,y+6,-32,-29))
        saddle = fuse(saddle, *feet)
        saddle = cut(saddle, *[cylinder(1.7, 7, (x,y,-34))
                               for x,y in CONSTANTS["mount_holes_xy"]])
    import fastener_revision as fr
    return fr.revise_clamp(saddle,cap,sc.CLAMP_BOLT_XZ,roof_up,_b)


def _aux_standoff_lands(shape):
    # A continuous annular stand-off supports the wider fork without four
    # slender columns. Its OD19.8 stays inside the auxiliary disc face and
    # leaves the central fixed retainer and peripheral screw paths open.
    lands=[cylinder(9.9,sc.AUX_STANDOFF,(0,-22,0),(0,1,0))]
    return cut(_horn_holes_y(fuse(shape,*lands)),_hole_y(0,0,radius=4.2))


def _access_pocket_sweep(shape,tail_out,angles,origin_x=0):
    reserve=_pitch(sc.plugged_profile_reserve(),tail_out)
    tools=[translate(rotate(reserve,(0,1,0),-angle),(origin_x,0,0)) for angle in angles]
    return cut(shape,*tools)


def _reopen_clamp_access(shape,tail_out,origin_x):
    for x,z in sc.CLAMP_BOLT_XZ:
        shape=cut(shape,_pitch(_hole_y(x,z,-20,40),tail_out,origin_x),
                  _pitch(_hex_y(x,-25,z,11.3),tail_out,origin_x))
    return shape


def _part(name, shape, link, material="pla", printable=True, **kwargs):
    if not valid(shape) or volume(shape) <= 0:
        raise RuntimeError(f"Invalid leg part {name}")
    rotation = PRINT_ROTATIONS.get(name,(0,0,0))
    if name.startswith("coupon_case_cap"): rotation=(90,0,0)
    if name.startswith("coupon_case_saddle"): rotation=(0,0,0)
    if name=="coupon_horn_cheek_main": rotation=(-90,0,0)
    if name=="coupon_horn_cheek_auxiliary": rotation=(90,0,0)
    if name=="coupon_pitch_yoke_bridge_38": rotation=(90,0,0)
    if name=="coupon_femur_bridge_load_main": rotation=(-90,0,0)
    if name=="coupon_femur_bridge_load_aux": rotation=(90,0,0)
    if name=="coupon_coxa_staggered_nut_post": rotation=(90,0,0)
    return {"name": name, "shape": shape, "link": link, "material": material,
            "printable": printable, "print_rotation":rotation,
            "supports_required":name in ("coxa_upper_and_hip_saddle",
                                          "femur_main_and_knee_saddle",
                                          "tibia_curved_main_and_foot"), **kwargs}


def _cheek(profile, y0, thickness=4):
    return _horn_holes_y(fuse(cylinder(14, thickness, (0, y0, 0), (0,1,0)),
                              prism_xz(profile, y0, thickness)))


def build_leg():
    parts = []
    saddle, cap = case_clamp(True)
    parts.extend([_part("yaw_case_saddle", saddle, "base_mount"),
                  _part("case_cap_yaw", cap, "base_mount"),
                  _part("servo_yaw", servo_envelope(), "base_mount", "servo", False, mass_kg=0.055)])

    from hip_revision import build_coxa
    parts.extend(build_coxa())

    knee_saddle, knee_cap = case_clamp(roof_up=-1)
    femur_profile = [(0,14),(20,15),(44,16),(54,26),(58,29.5),(72,29.5),
                     (76,25),(79,10),(79,-17),(44,-17),(0,-14)]
    femur_main = _cheek(femur_profile,19)
    femur_aux = _cheek(femur_profile,-27,5)
    femur_top=[(20,15),(44,16),(54,26),(58,29.5),(72,29.5),(76,25),(79,10)]
    femur_bottom=[(20,-15.363636),(44,-17),(79,-17)]
    for y0 in (15,):
        ribs=fuse(_edge_rib(femur_top,-1,y0),_edge_rib(femur_bottom,1,y0))
        ribs=cut(ribs,cylinder(11,12,(90,y0-1,0),(0,1,0)))
        ribs=cut(ribs,cylinder(38,2.7,(0,15,0),(0,1,0)),
                 cylinder(38,2.7,(90,15,0),(0,1,0)))
        femur_main=fuse(femur_main,ribs)
    femur_main=cut(femur_main,cylinder(28,8,(90,15,0),(0,1,0)))
    femur_aux=cut(femur_aux,cylinder(28,5,(90,-27,0),(0,1,0)))
    # The top bridge joins the fixed rail above the inward case and leaves
    # the separate lower cap and its three vertical screw paths accessible.
    femur_bridge = prism_xz([(58,15),(59.5,13.5),(70.5,13.5),(72,15),
                             (72,26),(70.5,27.5),(59.5,27.5),(58,26)],-22,45)
    femur_main = fuse(femur_main, femur_bridge, _pitch(knee_saddle,False,90))
    femur_main=_reopen_clamp_access(femur_main,False,90)
    femur_main = cut(femur_main,_hole_y(65,20.5,-30,60))
    import fastener_revision as fr
    femur_main = fr.bridge_nut(femur_main,65,20.5,27.5,_b)
    femur_aux = cut(femur_aux,_hole_y(65,20.5,-30,60))
    femur_aux=_aux_standoff_lands(femur_aux)
    femur_main=cut(femur_main,cylinder(28,8,(90,15,0),(0,1,0)))
    femur_aux=cut(femur_aux,_pitch(sc.plugged_profile_reserve(),False,90))
    parts.extend([_part("femur_main_and_knee_saddle",femur_main,"femur"),
                  _part("femur_auxiliary_cheek",femur_aux,"femur"),
                  _part("case_cap_knee",_pitch(knee_cap,False,90),"femur"),
                  _part("servo_knee",_pitch(servo_envelope(),False,90),"femur","servo",False,mass_kg=0.055),
                  _part("horn_hip_main",_pitch(main_horn(),False),"femur","metal",False),
                  _part("horn_hip_auxiliary",_pitch(auxiliary_disc(),False),"femur","metal",False)])

    import sys
    from tibia_revision import build_tibia_parts
    parts.extend(build_tibia_parts(sys.modules[__name__]))
    return parts


def build_coupons():
    from fit_coupons import build_coupons as make_fixtures
    return make_fixtures()


if __name__ == "__main__":
    for part in build_leg()+build_coupons():
        print(part["name"], part["link"], round(volume(part["shape"]),2), bounds(part["shape"]), flush=True)
