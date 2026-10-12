"""Video-derived direct-drive leg. All lengths are millimetres.

Each returned shape uses its owning link frame. X runs out along the leg;
Y is left and Z is up. Positive pitch about Y tips X down. Horn seating,
case fit and auxiliary axial float remain coupon measurements.
"""

from __future__ import annotations

import math

from geom import box, cylinder, prism_xy, prism_xz, fuse, cut, translate, rotate
from geom import bounds, valid, volume


CONSTANTS = {
    "case_x": (-32.73, 12.5),
    "case_width": 24.73,
    "case_main_depth": 29.0,
    "case_rear_profile_depth": 32.0,
    "case_end_clearance": 0.3,
    "split_cap_gap": 0.8,
    "main_horn_outer_plane": 4.5,
    "auxiliary_disc_outer_plane": -33.5,
    "pitch_main_face_y": 14.5,
    "pitch_auxiliary_face_y": -14.5,
    "pitch_main_cheek_inner_y": 19.0,
    "pitch_auxiliary_cheek_inner_y": -19.0,
    "cheek_thickness": 4.0,
    "horn_pcd": 14.0,
    "mount_holes_xy": [(-29.0, -20.0), (-29.0, 20.0), (9.0, -20.0), (9.0, 20.0)],
    "yaw_clamp_mount_z": -32.0,
    "yaw_lower_plate_z": (-53.0, -44.0),
    "yaw_auxiliary_spacer_length": 10.5,
    "yaw_auxiliary_counterbore_diameter": 6.2,
    "yaw_auxiliary_counterbore_depth": 2.5,
    "coxa_post_holes_xy": ((32.0,-4.5),(32.0,4.5)),
    "coxa_post_nut_z_ranges": ((-41.5,-38.9),(-37.5,-34.9)),
    "femur_bridge_bounds_xz": ((63.0,-23.0),(77.0,-9.0)),
    "femur_bridge_bolt_xz": ((70.0,-16.0),),
    "tibia_bridge_bounds_xz": ((44.0,13.0),(60.0,26.0)),
    "tibia_bridge_bolt_xz": ((48.0,19.5),(56.0,19.5)),
    "cheek_inward_rib_depth": 4.0,
    "cheek_edge_rib_height": 4.0,
    "auxiliary_rib_near_joint_depth": 1.0,
    "auxiliary_case_clamp_radial_relief": 44.5,
    "hip_joint_xyz": (50.0, 0.0, 0.0),
    "knee_joint_xyz": (90.0, 0.0, 0.0),
    "toe_center_xyz": (105.0, 0.0, 0.0),
    "toe_pad_width": 14.0,
    "toe_radius": 5.0,
    "toe_plane_below_center": 4.8,
    "toe_nominal_total_pitch_deg": 105.0,
}

PROVISIONAL_JOINT_LIMITS_DEG = {"yaw": (-25,25), "hip": (3,35), "knee": (30,100)}
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


def _hex_z(x, y, z, depth=2.6, across_flats=5.7):
    radius = across_flats / math.sqrt(3)
    return prism_xy([(x + radius*math.cos(math.radians(30+60*i)),
                      y + radius*math.sin(math.radians(30+60*i)))
                     for i in range(6)], z, depth)


def _hex_y(x, y, z, depth=2.6):
    shape = _hex_z(x, -z, 0, depth)
    return translate(rotate(shape, (1, 0, 0), -90), (0, y, 0))


def _hole_y(x, z, y0=-25, length=50, radius=1.7):
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
    """Stepped drawing envelope with two rear connector openings, no cable claim."""
    shape = fuse(_b(-32.73, 12.5, -12.365, 12.365, -29, 0),
                 _b(-32.73, -22, -12.365, 12.365, -32, -28.9),
                 cylinder(2.95, 3.4),
                 cylinder(3.0, 4.1, (0, 0, -29), (0, 0, -1)))
    return cut(shape, _b(-33, -27, -8, 8, -25, -14))


def main_horn():
    shape = fuse(cylinder(9.975, 2.5, (0, 0, 2)),
                 cylinder(4.5, 1.1, (0, 0, 0.9)))
    return cut(shape, cylinder(2.95, 5, (0, 0, 0)),
               *[cylinder(1.25, 5, (x, y, 0)) for x, y in ((7,0),(-7,0),(0,7),(0,-7))])


def auxiliary_disc():
    shape = fuse(cylinder(9.975, 2.1, (0, 0, -33.5)),
                 cylinder(4.5, 1.0, (0, 0, -31.4)))
    return cut(shape, cylinder(3.025, 5, (0, 0, -34)),
               *[cylinder(1.25, 5, (x, y, -34)) for x, y in ((7,0),(-7,0),(0,7),(0,-7))])


def case_clamp(with_mount_feet=False, end_clearance=0.3):
    """Saddle and adjustable side cap; the 0.8 mm closure gap remains open.

    The fixed -Y and moving +Y rails contact the nominal case. End walls
    locate X with clearance. Shelves support the 29 mm case face while
    leaving the rear 32 mm profile and auxiliary shaft free. M3 bolts pass
    through exterior end walls, clear of the case and connector opening.
    """
    xlo, xhi = -32.73-end_clearance, 12.5+end_clearance
    saddle = fuse(_b(-40.5, 20.5, -16.365, -12.365, -32, -2),
                  _b(-40.5, xlo, -16.365, 11.565, -29, -2),
                  _b(xhi, 20.5, -16.365, 11.565, -29, -2),
                  _b(-18, 15, -12.365, -10.5, -32, -29),
                  _b(xhi, 16, -12.365, 11.565, -32, -28.9))
    # The wide aperture includes cable extraction through the open rear wall.
    saddle = cut(saddle, _b(-42, -30, -9, 9, -27, -9))
    cap = _b(-40.5, 20.5, 12.365, 16.365, -29, -2)
    bolt_tools = []
    # Three bolts avoid a transverse screw across the rear cable aperture.
    for x, z in ((-37,-5.5),(17,-23),(17,-7)):
        bolt_tools.append(_hole_y(x, z, -18, 38))
        saddle = cut(saddle, _hex_y(x, -16.5, z, 2.8))
    saddle = cut(saddle, *bolt_tools)
    cap = cut(cap, *bolt_tools)
    if with_mount_feet:
        feet = [_b(-40.5, -33.0, -25.5, 25.5, -32, -29),
                _b(12.8, 20.5, -25.5, 25.5, -32, -29)]
        for x, y in CONSTANTS["mount_holes_xy"]:
            feet.append(_b(x-6, x+6, y-6, y+6, -32, -29))
        saddle = fuse(saddle, *feet)
        saddle = cut(saddle, *[cylinder(1.7, 7, (x,y,-34))
                               for x,y in CONSTANTS["mount_holes_xy"]])
    return saddle, cap


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


def _cheek(profile, y0):
    return _horn_holes_y(fuse(cylinder(14, 4, (0, y0, 0), (0,1,0)),
                              prism_xz(profile, y0, 4)))


def build_leg():
    parts = []
    saddle, cap = case_clamp(True)
    parts.extend([_part("yaw_case_saddle", saddle, "base_mount"),
                  _part("case_cap_yaw", cap, "base_mount"),
                  _part("servo_yaw", servo_envelope(), "base_mount", "servo", False, mass_kg=0.055)])

    hip_saddle, hip_cap = case_clamp()
    coxa_plate = _horn_holes_z(fuse(cylinder(14, 4, (0,0,4.5)),
                                   prism_xy([(0,-14),(23,-14),(35,-10),(35,10),(23,14),(0,14)],4.5,4)))
    # Wider lower shoulders and staggered nut windows preserve the post neck.
    coxa_post = _prism_yz([(-11.5,-44),(-11.5,-34),(-8.5,-28),(-8.5,8.5),
                           (8.5,8.5),(8.5,-28),(11.5,-34),(11.5,-44)],28,8.5)
    for y,z0 in ((-4.5,-41.5),(4.5,-37.5)):
        coxa_post = cut(coxa_post,cylinder(1.7,15,(32,y,-45)),
                        _hex_z(32,y,z0,2.6),
                        _b(29.1,34.9,y if y>0 else -13,13 if y>0 else y,z0,z0+2.6))
    coxa = fuse(coxa_plate, coxa_post, _pitch(hip_saddle, True, 50))
    lower = _horn_holes_z(fuse(cylinder(14,9,(0,0,-53)),
                              prism_xy([(0,-11.5),(36.5,-11.5),(36.5,11.5),(0,11.5)],-53,9)))
    lower = cut(lower,*[cylinder(1.7,11,(32,y,-54)) for y in (-4.5,4.5)],
                 *[cylinder(3.1,2.6,(x,y,-53.1)) for x,y in ((7,0),(-7,0),(0,7),(0,-7))])
    parts.extend([_part("coxa_upper_and_hip_saddle", coxa, "coxa"),
                  _part("coxa_lower_auxiliary_arm", lower, "coxa"),
                  _part("case_cap_hip", _pitch(hip_cap,True,50), "coxa"),
                  _part("servo_hip", _pitch(servo_envelope(),True,50), "coxa", "servo", False, mass_kg=0.055),
                  _part("horn_yaw_main", main_horn(), "coxa", "metal", False),
                  _part("horn_yaw_auxiliary", auxiliary_disc(), "coxa", "metal", False)])
    for index,(x,y) in enumerate(((7,0),(-7,0),(0,7),(0,-7)),1):
        spacer = cut(cylinder(2.9,10.5,(x,y,-44)), cylinder(1.7,12,(x,y,-44.5)))
        parts.append(_part(f"yaw_auxiliary_spacer_{index}",spacer,"coxa"))

    knee_saddle, knee_cap = case_clamp()
    femur_profile = [(0,14),(20,15),(55,13),(79,10),(79,-20),
                     (77,-23),(63,-23),(53,-18),(44,-17),(0,-14)]
    femur_main = _cheek(femur_profile,19)
    femur_aux = _cheek(femur_profile,-23)
    femur_top=[(20,15),(55,13),(79,10)]
    femur_bottom=[(20,-15.363636),(44,-17),(53,-18),(63,-23),(77,-23)]
    for y0 in (15,-19):
        ribs=fuse(_edge_rib(femur_top,-1,y0),_edge_rib(femur_bottom,1,y0))
        ribs=cut(ribs,cylinder(11,12,(90,y0-1,0),(0,1,0)))
        if y0>0:femur_main=fuse(femur_main,ribs)
        else:
            ribs=cut(ribs,cylinder(44.5,3.1,(0,-18,0),(0,1,0)),
                     _b(69,78,-18,-14.9,-17,12.1),
                     _b(62.7,77.3,-19.1,-14.9,-23.3,-8.7))
            femur_aux=fuse(femur_aux,ribs)
    femur_main=cut(femur_main,cylinder(14.8,4,(90,19,0),(0,1,0)))
    femur_aux=cut(femur_aux,cylinder(14.8,4,(90,-23,0),(0,1,0)))
    # A web meets only the knee clamp's end wall, before the servo starts.
    femur_bridge = prism_xz([(63,-21),(65,-23),(75,-23),(77,-21),
                             (77,-11),(75,-9),(65,-9),(63,-11)],-19,42)
    femur_main = fuse(femur_main, femur_bridge, _pitch(knee_saddle,True,90))
    femur_main = cut(femur_main,_hole_y(70,-16,-25,52))
    femur_aux = cut(femur_aux,_hole_y(70,-16,-25,52))
    parts.extend([_part("femur_main_and_knee_saddle",femur_main,"femur"),
                  _part("femur_auxiliary_cheek",femur_aux,"femur"),
                  _part("case_cap_knee",_pitch(knee_cap,True,90),"femur"),
                  _part("servo_knee",_pitch(servo_envelope(),True,90),"femur","servo",False,mass_kg=0.055),
                  _part("horn_hip_main",_pitch(main_horn(),True),"femur","metal",False),
                  _part("horn_hip_auxiliary",_pitch(auxiliary_disc(),True),"femur","metal",False)])

    tibia_fork_profile = [(0,14),(16,17),(35,23),(42,27),(60,28),
                          (63,25),(63,16),(60,12),(45,8),(18,-3),(0,-14)]
    tibia_main = _cheek(tibia_fork_profile,19)
    tibia_aux = _cheek(tibia_fork_profile,-23)
    tibia_top=[(25,19.842105),(35,23),(42,27),(60,28)]
    tibia_bottom=[(25,-0.148148),(45,8),(60,12)]
    for y0 in (15,-19):
        ribs=fuse(_edge_rib(tibia_top,-1,y0),_edge_rib(tibia_bottom,1,y0))
        if y0>0:tibia_main=fuse(tibia_main,ribs)
        else:
            ribs=cut(ribs,cylinder(44.5,3.1,(0,-18,0),(0,1,0)),
                     _b(43.7,60.3,-19.1,-14.9,12.7,26.3))
            tibia_aux=fuse(tibia_aux,ribs)
    tibia_bridge = prism_xz([(44,14.5),(45.5,13),(58.5,13),(60,14.5),
                             (60,24.5),(58.5,26),(45.5,26),(44,24.5)],-19,42)
    # A small flat on a rounded toe tolerates stance changes without sharp
    # edge contact. At the 30 + 75 degree pose its depth is 4.8 mm.
    a = math.radians(CONSTANTS["toe_nominal_total_pitch_deg"])
    curved_profile = [(45,25.77),(49,27),(62,25),(76,20),(90,12),
                      (105,5),(105,-5),(99,-5),(85,1),
                      (71,7),(58,12),(45,13)]
    tibia_foot = fuse(prism_xz(curved_profile,-7,14),
                       cylinder(5,14,(105,-7,0),(0,1,0)))
    normal=(math.sin(a),-math.cos(a))
    tangent=(math.cos(a),math.sin(a))
    p=(105+4.8*normal[0],4.8*normal[1])
    outside=[(p[0]+u*tangent[0]+v*normal[0],p[1]+u*tangent[1]+v*normal[1])
             for u,v in ((100,0),(-100,0),(-100,100),(100,100))]
    tibia_foot=cut(tibia_foot,prism_xz(outside,-9,18))
    # A strap passes through this transverse slot to retain optional padding.
    tibia_foot = cut(tibia_foot,_b(98,102,-9,9,-0.5,2.5))
    tibia_main = fuse(tibia_main,tibia_bridge,tibia_foot)
    for x in (48,56):
        tibia_main = cut(tibia_main,_hole_y(x,19.5,-25,52))
        tibia_aux = cut(tibia_aux,_hole_y(x,19.5,-25,52))
    parts.extend([_part("tibia_curved_main_and_foot",tibia_main,"tibia"),
                  _part("tibia_auxiliary_cheek",tibia_aux,"tibia"),
                  _part("horn_knee_main",_pitch(main_horn(),True),"tibia","metal",False),
                  _part("horn_knee_auxiliary",_pitch(auxiliary_disc(),True),"tibia","metal",False)])
    return parts


def build_coupons():
    coupons = []
    for clearance in (0.2,0.3,0.4):
        saddle, cap = case_clamp(False,clearance)
        tag = str(clearance).replace(".","p")
        coupons.extend([_part(f"coupon_case_saddle_endgap_{tag}",saddle,"coupon"),
                        _part(f"coupon_case_cap_endgap_{tag}",cap,"coupon")])
    for name,y0 in (("main",19),("auxiliary",-23)):
        coupon = _horn_holes_y(fuse(cylinder(14,4,(0,y0,0),(0,1,0)),
                                   _b(0,33,y0,y0+4,-7,7)))
        coupon = cut(coupon,_hole_y(29,0))
        if name=="main": coupon=cut(coupon,_hex_y(29,19.9,0,3.2))
        coupons.append(_part(f"coupon_horn_cheek_{name}",coupon,"coupon"))
    bridge=cut(_b(25,33,-19,19,-7,7),_hole_y(29,0))
    coupons.append(_part("coupon_pitch_yoke_bridge_38",bridge,"coupon"))
    strip = _b(-17,17,-7,7,0,4)
    strip = cut(strip,*[cylinder(d/2,6,(x,0,-1)) for x,d in ((-10,3.2),(0,3.4),(10,3.6))])
    coupons.append(_part("coupon_m3_clearance_3p2_3p4_3p6",strip,"coupon"))
    for length in (10.2,10.5,10.8):
        spacer = cut(cylinder(2.9,length),cylinder(1.7,length+2,(0,0,-1)))
        coupons.append(_part("coupon_yaw_spacer_"+str(length).replace(".","p"),spacer,"coupon"))
    # These are cropped production sections, retaining the actual hole lands,
    # layer directions and nut windows. Use the complete lower yaw arm with
    # the post coupon to test its counterbores and supported disc stack.
    production={p["name"]:p["shape"] for p in build_leg() if p["printable"]}
    for name,source,region in (
        ("coupon_femur_bridge_load_main","femur_main_and_knee_saddle",
         _b(62.9,77.1,-19.01,23.01,-23.01,-8.99)),
        ("coupon_femur_bridge_load_aux","femur_auxiliary_cheek",
         _b(62.9,77.1,-23.01,-18.99,-23.01,-8.99)),
        ("coupon_coxa_staggered_nut_post","coxa_upper_and_hip_saddle",
         _b(27.9,36.6,-11.6,11.6,-44,-28)),
    ):
        coupons.append(_part(name,_crop(production[source],region),"coupon",
                              note="Actual R3 production section for sacrificial fixture tests."))
    return coupons


if __name__ == "__main__":
    for part in build_leg()+build_coupons():
        print(part["name"], part["link"], round(volume(part["shape"]),2), bounds(part["shape"]), flush=True)
