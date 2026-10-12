"""R5 inward hip packaging candidates, using the established C018 frames."""
from pathlib import Path
import sys
import math
import json

sys.path.insert(0,str(Path(__file__).resolve().parent))
import leg
import servo_contract as sc
from geom import box,cylinder,prism_xy,fuse,cut,translate,rotate,volume,valid,bounds,common_volume,export_step


HIP_CLAMP_BOLT_XZ=((sc.CLAMP_REAR_BOLT_X,-27.5),
                   (sc.CLAMP_FRONT_BOLT_X,-23.0),(sc.CLAMP_FRONT_BOLT_X,-7.0))
SELECTED_COXA_LENGTH_MM=82.0
SELECTED_POST_X_MIN_MM=36.5
SELECTED_POST_X_MAX_MM=45.0
SELECTED_POST_WIDTH_MM=17.0
SELECTED_POST_HOLES_XY=((40.5,-4.5),(40.5,4.5))
SELECTED_POST_NUT_Z_RANGES=((-41.5,-38.8),(-37.5,-34.8))


def hip_clamp(end_clearance=.3):
    """Move the rear clamp-cap ear beside the post, clear of its load path."""
    b=leg._b
    xlo,xhi=sc.CASE_X_MIN-end_clearance,sc.CASE_X_MAX+end_clearance
    xmin,xmax=sc.CLAMP_X_MIN,sc.CLAMP_X_MAX
    saddle=fuse(b(xmin,xmax,-16.365,-12.365,-32,-2),
                b(xmin,xlo,-16.365,11.565,-29,-2),
                b(xmin,xlo,-16.365,11.565,-32,-28.9),
                b(xhi,xmax,-16.365,11.565,-29,-2),
                b(-4,4,-12.365,-11.5,-32,-29.4),
                b(xhi,xmax-1,-12.365,11.565,-32,-28.9))
    # Only the cap's rear end is narrowed. Its full case-contacting rail and
    # two front screws remain. The rear OD7 washer has a full flat seat.
    cap=fuse(b(xlo,xmax,12.365,16.365,-29,-2),
             b(xmin,xlo+.1,12.365,16.365,-32,-24))
    for x,z in HIP_CLAMP_BOLT_XZ:
        tool=leg._hole_y(x,z,-18,38)
        saddle=cut(saddle,tool,leg._hex_y(x,-16.5,z,2.8))
        cap=cut(cap,tool)
    import fastener_revision as fr
    return fr.revise_clamp(saddle,cap,HIP_CLAMP_BOLT_XZ,1,b)


def reopen_hip_clamp_access(shape,length):
    for x,z in HIP_CLAMP_BOLT_XZ:
        shape=cut(shape,leg._pitch(leg._hole_y(x,z,-20,40),False,length),
                  leg._pitch(leg._hex_y(x,-25,z,11.3),False,length))
    return shape


def build_coxa(length=SELECTED_COXA_LENGTH_MM,
               post_x=SELECTED_POST_X_MIN_MM,post_width=SELECTED_POST_WIDTH_MM):
    """Return the same ten coxa-owned parts, with an inward hip case.

    Length is the yaw-to-hip shaft spacing. The lower arm, horn seating,
    auxiliary spacers, clamp bolt hardware, and staggered nuts retain their
    R4 thicknesses. post_x is the inboard edge of the 8.5 mm radial section.
    """
    b=leg._b
    post_center=post_x+4.0
    end=post_x+8.5
    hip_saddle,hip_cap=hip_clamp()
    plate=leg._horn_holes_z(fuse(cylinder(14,4,(0,0,4.5)),
          prism_xy([(0,-14),(post_x-5,-14),(end,-post_width/2),
                    (end,post_width/2),(post_x-5,14),(0,14)],4.5,4)))
    neck=post_width/2
    post=leg._prism_yz([(-11.5,-44),(-11.5,-34),(-neck,-28),(-neck,8.5),
                         (neck,8.5),(neck,-28),(11.5,-34),(11.5,-44)],post_x,8.5)
    # A tapered inboard flange widens the bending section while preserving
    # the clearance swept by the yaw clamp at either steering limit.
    post=fuse(post,prism_xy([(post_x,-neck),(post_x-3,0),(post_x,neck)],-44,52.5))
    for y,z0 in ((-4.5,-41.5),(4.5,-37.5)):
        post=cut(post,cylinder(1.7,15,(post_center,y,-45)),
                 leg._hex_z(post_center,y,z0,2.7),
                 b(post_center-2.9,post_center+2.9,y if y>0 else -13,
                   13 if y>0 else y,z0,z0+2.7))
    upper=fuse(plate,post,leg._pitch(hip_saddle,False,length))
    upper=reopen_hip_clamp_access(upper,length)
    upper=cut(upper,cylinder(4,42,(length+sc.CLAMP_REAR_BOLT_X,-13,-60)))
    lower=leg._horn_holes_z(fuse(cylinder(14,9,(0,0,-53)),
          prism_xy([(0,-11.5),(end,-11.5),(end,11.5),(0,11.5)],-53,9)))
    lower=cut(lower,*[cylinder(1.7,11,(post_center,y,-54)) for y in (-4.5,4.5)],
              *[cylinder(4.1,3.6,(x,y,-53.1)) for x,y in ((7,0),(-7,0),(0,7),(0,-7))])
    # A small edge scallop admits the rear cap screw, OD7 washer, and driver
    # with the lower arm assembled. It stays away from the post screw pair.
    lower=cut(lower,cylinder(4,12,(length+sc.CLAMP_REAR_BOLT_X,-13,-54)))
    parts=[leg._part('coxa_upper_and_hip_saddle',upper,'coxa'),
           leg._part('coxa_lower_auxiliary_arm',lower,'coxa'),
           leg._part('case_cap_hip',leg._pitch(hip_cap,False,length),'coxa'),
           leg._part('servo_hip',leg._pitch(leg.servo_envelope(),False,length),
                     'coxa','servo',False,mass_kg=.055),
           leg._part('horn_yaw_main',leg.main_horn(),'coxa','metal',False),
           leg._part('horn_yaw_auxiliary',leg.auxiliary_disc(),'coxa','metal',False)]
    for index,(x,y) in enumerate(((7,0),(-7,0),(0,7),(0,-7)),1):
        spacer=cut(cylinder(2.9,11.6,(x,y,-44)),cylinder(1.7,13,(x,y,-44.5)))
        parts.append(leg._part(f'yaw_auxiliary_spacer_{index}',spacer,'coxa'))
    return parts


def _overlap_bounds(a,b):
    aa=bounds(a);bb=bounds(b)
    return all(min(aa[1][i],bb[1][i])-max(aa[0][i],bb[0][i])>1e-5 for i in range(3))


def audit_candidate(length,post_x,post_width):
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_SOLID
    parts=build_coxa(length,post_x,post_width)
    saddle,cap=leg.case_clamp(True)
    fixed=[('yaw_case_saddle',saddle),('case_cap_yaw',cap),('servo_yaw',leg.servo_envelope())]
    tests=[]; clashes=[]
    for i,p in enumerate(parts):
        for q in parts[i+1:]:
            if not _overlap_bounds(p['shape'],q['shape']):continue
            v=common_volume(p['shape'],q['shape'])
            tests.append((p['name'],q['name'],v))
            if v>.001:clashes.append(tests[-1])
    for angle in (-22,-15,0,15,22):
        for p in parts:
            s=rotate(p['shape'],(0,0,1),angle)
            for name,q in fixed:
                if not _overlap_bounds(s,q):continue
                v=common_volume(s,q)
                tests.append((f"{p['name']}@{angle}",name,v))
                if v>.001:clashes.append(tests[-1])
    # Hip plug reserve belongs to the fixed case and must clear the bracket.
    plug=leg._pitch(sc.plugged_profile_reserve(),False,length)
    for p in parts:
        if not p['printable']:continue
        v=common_volume(p['shape'],plug)
        tests.append((p['name'],'hip_plug_reserve',v))
        if v>.001:clashes.append(tests[-1])
    # External hardware and straight access cylinders include the washers,
    # not only the narrow screw bores. Intended head/washer face contact is
    # zero volume. The cap is installed before the screw enters its bore.
    for index,(x,z) in enumerate(HIP_CLAMP_BOLT_XZ):
        washer=leg._pitch(cut(cylinder(3.5,.5,(x,16.365,z),(0,1,0)),
                   cylinder(1.6,.7,(x,16.3,z),(0,1,0))),False,length)
        head=leg._pitch(cylinder(2.75,3,(x,16.865,z),(0,1,0)),False,length)
        path=leg._pitch(cylinder(3.75,42,(x,19.865,z),(0,1,0)),False,length)
        for tag,tool in (('washer',washer),('head',head),('extraction',path)):
            for p in parts:
                if not p['printable']:continue
                v=common_volume(p['shape'],tool)
                tests.append((p['name'],f'hip_{index}_{tag}',v))
                if v>.001:clashes.append(tests[-1])
    solids={}
    for p in parts:
        e=TopExp_Explorer(p['shape'],TopAbs_SOLID); n=0
        while e.More():n+=1;e.Next()
        solids[p['name']]=n
    return {'length_mm':length,'post_x_min':post_x,'post_width_mm':post_width,
            'coxa_post_holes_xy':[[post_x+4,-4.5],[post_x+4,4.5]],
            'boolean_checks':len(tests),'clashes':clashes,'solid_counts':solids,
            'printed_volume_mm3':sum(volume(p['shape']) for p in parts if p['printable']),
            'all_valid':all(valid(p['shape']) for p in parts)}


if __name__=='__main__':
    out=Path(__file__).resolve().parent.parent/'manufacturing'/'hip_revision'
    out.mkdir(parents=True,exist_ok=True)
    row=audit_candidate(SELECTED_COXA_LENGTH_MM,SELECTED_POST_X_MIN_MM,SELECTED_POST_WIDTH_MM)
    print(json.dumps(row),flush=True)
    (out/'packaging_candidate_final.json').write_text(json.dumps(row,indent=2)+'\n')
