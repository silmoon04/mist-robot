"""R4 fit fixtures generated from the promoted leg and shared C018 contract."""
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
CAD=HERE if (HERE/"leg.py").is_file() else HERE.parents[1]/"cad"
if str(CAD) not in sys.path:sys.path.insert(0,str(CAD))
import geom as g
import leg
import servo_contract as sc


def part(name,shape,rotation=(0,0,0),note="",mandatory=False,supports=False):
    if not g.valid(shape) or g.volume(shape)<=0:
        raise RuntimeError("Invalid coupon: "+name)
    return {"name":name,"shape":shape,"link":"coupon","material":"pla","printable":True,
            "print_rotation":rotation,"note":note,"assembly_note":note,
            "mandatory":mandatory,"supports_required":supports}


def datum_registration_plate():
    """Attach at the two X=9 clamp feet and register its actual metal horn."""
    z=sc.MAIN_HORN_OUTER_Z
    shape=g.fuse(g.cylinder(14,4,(0,0,z)),leg._b(4,14,-30,30,z,z+4))
    for sign in (-1,1):
        y0,y1=(16.9,30) if sign>0 else (-30,-16.9)
        shape=g.fuse(shape,leg._b(3,15,y0,y1,-29,-25),
                     g.box(6,6,z+25,(9,sign*26.5,(z-25)/2)))
        shape=g.cut(shape,g.cylinder(1.7,10,(9,sign*20,-33)),
                    g.cylinder(3.5,6,(9,sign*20,z-1)))
    shape=g.cut(shape,g.cylinder(3.5,6,(0,0,z-1)),
                *[g.cylinder(1.7,6,(x,y,z-1)) for x,y in ((7,0),(-7,0),(0,7),(0,-7))])
    return shape


def horn_fixture_cheeks():
    result=[]
    for side,y0 in (("main",19),("auxiliary",-23)):
        shape=leg._horn_holes_y(g.fuse(g.cylinder(14,4,(0,y0,0),(0,1,0)),
                                      leg._b(0,33,y0,y0+4,-7,7)))
        shape=g.cut(shape,leg._hole_y(29,0))
        if side=="auxiliary":shape=leg._aux_standoff_lands(shape)
        result.append(part("r4_horn_fixture_"+side,shape,
                           (-90,0,0) if side=="main" else (90,0,0),
                           "Use the actual supplied disc and its retainer washer. Assemble with the 38 mm bridge without forcing the disc stack.",True))
    bridge=g.cut(leg._b(25,33,-19,19,-7,7),leg._hole_y(29,0))
    result.append(part("r4_horn_fixture_bridge_38",bridge,(90,0,0),
                       "One M3x50, two OD7 by 0.5 mm washers and a plain 2.4 mm nut close the two cheeks. Check auxiliary free rotation.",True))
    return result


def build_coupons():
    coupons=[]
    for clearance in (.2,.3,.4):
        saddle,cap=leg.case_clamp(True,clearance)
        suffix=str(clearance).replace(".","p")
        coupons.extend([
            part("r4_case_datum_saddle_"+suffix,saddle,note=
                 "Includes the actual mounting feet. Use the registration plate to test case-to-shaft alignment while the actual servo is clamped.",mandatory=clearance==.3),
            part("r4_case_cap_"+suffix,cap,(90,0,0),
                 "The three caps are geometrically identical and can be reused across clearance variants.",clearance==.3)])
    coupons.append(part("r4_case_to_shaft_registration_plate",datum_registration_plate(),(180,0,0),
                        "Attach to X9/Y+20 and X9/Y-20 saddle feet with two M3x12 bolts, two nuts and four OD6 by 0.5 mm washers. Fit the actual main horn at the same time. Support the two offset feet when printing inverted.",True,True))
    coupons.extend(horn_fixture_cheeks())
    for length in (11.3,11.6,11.9):
        shape=g.cut(g.cylinder(2.9,length),g.cylinder(1.7,length+2,(0,0,-1)))
        coupons.append(part("r4_yaw_spacer_"+str(length).replace(".","p"),shape,note=
                             "Compare spacer lengths with the seated auxiliary disc and fixed-stub retainer. The nominal candidate is 11.6 mm; do not tighten away free rotation.",mandatory=length==11.6))
    strip=leg._b(-17,17,-7,7,0,4)
    strip=g.cut(strip,*[g.cylinder(d/2,6,(x,0,-1)) for x,d in ((-10,3.2),(0,3.4),(10,3.6))])
    coupons.append(part("r4_m3_clearance_3p2_3p4_3p6",strip,note="Left to right: 3.2, 3.4 and 3.6 mm holes.",mandatory=True))
    production={p["name"]:p["shape"] for p in leg.build_leg() if p["printable"]}
    for name,source,region,rotation in (
        ("r4_top_bridge_load_main","femur_main_and_knee_saddle",leg._b(57.9,72.1,-19.01,23.01,13.49,27.51),(-90,0,0)),
        ("r4_top_bridge_load_aux","femur_auxiliary_cheek",leg._b(57.9,72.1,-23.01,-18.99,13.49,27.51),(90,0,0)),
        ("r4_post_staggered_nut_section","coxa_upper_and_hip_saddle",leg._b(27.9,36.6,-11.6,11.6,-44,-28),(90,0,0)),
    ):
        coupons.append(part(name,leg._crop(production[source],region),rotation,
                             "Cropped from actual R4 production geometry. Use as a sacrificial section specimen in the recorded print orientation."))
    return coupons


if __name__=="__main__":
    for p in build_coupons():print(p["name"],g.volume(p["shape"]),g.bounds(p["shape"]),flush=True)
