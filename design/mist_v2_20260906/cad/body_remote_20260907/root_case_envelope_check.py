"""Independent case-only packing example using the saved component bounds.

This is a static spatial lower bound, not a selected transmission layout.
There are no shafts, gears, moving carriers, frames or service paths in it.
"""
from itertools import combinations, product
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE=ROOT/'cad/leg_proximal_20260907/output_candidate/leg_geometry_report.json'


def box(name,bounds,role):
    return {'name':name,'kind':'box','bounds_mm':bounds,'role':role}


def center_box(name,center,size,role):
    return box(name,[[center[i]-size[i]/2 for i in range(3)],
                     [center[i]+size[i]/2 for i in range(3)]],role)


def intersects(a,b):
    aa=a['bounds_mm'];bb=b['bounds_mm']
    if min(aa[1][2],bb[1][2])-max(aa[0][2],bb[0][2])<=1e-8:
        return False
    if a['kind']=='box' and b['kind']=='box':
        return all(min(aa[1][i],bb[1][i])-max(aa[0][i],bb[0][i])>1e-8 for i in (0,1))
    if a['kind']=='cylinder' and b['kind']=='cylinder':
        return math.dist(a['center_xy_mm'],b['center_xy_mm'])<a['radius_mm']+b['radius_mm']-1e-8
    cylinder,rectangle=(a,b) if a['kind']=='cylinder' else (b,a)
    bounds=rectangle['bounds_mm'];xy=cylinder['center_xy_mm']
    d2=sum((xy[i]-min(max(xy[i],bounds[0][i]),bounds[1][i]))**2 for i in (0,1))
    return d2<(cylinder['radius_mm']-1e-8)**2


def run():
    saved=json.loads(SOURCE.read_text())
    rows={row['name']:row for row in saved['parts'] if row['group']=='body'}
    components=[]
    for level,z in enumerate((52.5,92.5,132.5)):
        for index,(x,y) in enumerate(product((-25.,25.),(-15.,15.))):
            components.append(center_box(f'STS_layer{level+1}_{index+1}',(x,y,z),(45.23,24.73,35.),'positional servo case only'))
    for index,(x,y) in enumerate(product((-50.,50.),repeat=2)):
        part=center_box(f'Wheel_motor_{index+1}',(x,y,65.5),(25.,25.,61.),'wheel motor housing only')
        part.update(kind='cylinder',center_xy_mm=[x,y],radius_mm=12.5)
        components.append(part)
    for name in ('H01_battery_HOOVO_3S_REFERENCE','H02_brain_phone_ENVELOPE','H03_face_phone_Mi9SE_REFERENCE'):
        bounds=[corner[:] for corner in rows[name]['bounds_partlocal_mm']]
        if name=='H02_brain_phone_ENVELOPE':
            for corner in bounds:
                corner[2]+=111.0
        components.append(box(name,bounds,'existing device envelope; brain phone shifted upward111mm'))
    inner_radius=90.-2.4
    for part in components:
        bb=part['bounds_mm']
        radial=(math.hypot(*part['center_xy_mm'])+part['radius_mm'] if part['kind']=='cylinder'
                else max(math.hypot(x,y) for x,y in product((bb[0][0],bb[1][0]),(bb[0][1],bb[1][1]))))
        part['minimum_radial_shell_gap_mm']=inner_radius-radial
        part['within_barrel']=radial<=inner_radius and bb[0][2]>=0 and bb[1][2]<=220
    collisions=[(a['name'],b['name']) for a,b in combinations(components,2) if intersects(a,b)]
    result={'status':'static_case_envelope_example','not_a_mechanism_or_service_fit':True,
        'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'units':'mm','frame':'body bottom, before assembly z offset',
        'barrel_outer_diameter_mm':180.,'barrel_inner_radius_mm':inner_radius,'barrel_height_mm':220.,
        'motor_case_count':16,'device_count':3,'pair_checks':len(components)*(len(components)-1)//2,
        'case_and_device_intersections':collisions,'all_case_envelopes_inside':all(p['within_barrel'] for p in components),
        'minimum_radial_gap_mm':min(p['minimum_radial_shell_gap_mm'] for p in components),
        'components':components,'changes':['Brain-phone envelope moved fromz64..74 toz175..185; its existing deck/frame must be redesigned.'],
        'excluded':['All output shafts/horns and their rotation','Reduction/transmission mechanisms and bearings',
                    'Existing interior decks, posts and core rings','Actuator mounting frames',
                    'Connectors and wire bend radii','Cooling and maintenance access','Any internal motor-carrier sweep'],
        'conclusion':'The bare component cases are not a geometric impossibility inside180mm. This does not demonstrate a workable drive package.'}
    (HERE/'root_case_envelope_check.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('components','source')},indent=2))
    return result


if __name__=='__main__':
    result=run()
    if result['case_and_device_intersections'] or not result['all_case_envelopes_inside']:
        raise SystemExit(1)
