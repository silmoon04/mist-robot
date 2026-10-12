"""Independent solid, fastener envelope and sampled articulation checks."""
from pathlib import Path
import itertools,json,math
import numpy as np
import build,leg,geom as g,servo_contract as sc,fastener_revision as fr
from hip_revision import HIP_CLAMP_BOLT_XZ
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

OUT=build.OUT

def overlap(a,b):
    aa,bb=g.bounds(a),g.bounds(b)
    return all(min(aa[1][k],bb[1][k])-max(aa[0][k],bb[0][k])>1e-5 for k in range(3))

def main():
    source_hash=build.sha(OUT/'manifest.json')
    parts,initial=build.load_assembly();lookup={p['name']:p for p in parts}
    failures=[];checks=[];count=0
    def check(tag,tool,targets):
        nonlocal count
        for p in targets:
            if not overlap(tool,p['shape']):continue
            count+=1;v=g.common_volume(tool,p['shape'])
            if v>.01:failures.append({'check':tag,'part':p['name'],'intersection_mm3':v})
    solids={}
    for p in parts:
        e=TopExp_Explorer(p['shape'],TopAbs_SOLID);n=0
        while e.More():n+=1;e.Next()
        solids[p['name']]={'solid_count':n,'valid':g.valid(p['shape'])}
        if not g.valid(p['shape']) or (p['printable'] and n!=1):failures.append({'part':p['name'],'solid_count':n})
    # Model actual clearances independently of the hole-cutting tools. Threads
    # use nominal shaft diameter, nuts 5.2 AF x 2.2 thick, washers 0.5 thick.
    for tag,link,bolts,xf in [('yaw','base_mount',sc.CLAMP_BOLT_XZ,lambda s:s),
        ('hip','coxa',HIP_CLAMP_BOLT_XZ,lambda s:leg._pitch(s,False,82)),
        ('knee','femur',sc.CLAMP_BOLT_XZ,lambda s:leg._pitch(s,False,90))]:
        targets=[p for p in parts if p['link']==link]
        for i,(x,z) in enumerate(bolts):
            check(f'{tag} clamp {i} M30 shaft',xf(g.cylinder(1.5,30,(x,16.865,z),(0,-1,0))),targets)
            check(f'{tag} clamp {i} washer',xf(g.cut(g.cylinder(3.5,.5,(x,16.365,z),(0,1,0)),g.cylinder(1.6,.7,(x,16.3,z),(0,1,0)))),targets)
            check(f'{tag} clamp {i} head',xf(g.cylinder(2.85,3,(x,16.865,z),(0,1,0))),targets)
            check(f'{tag} clamp {i} nut insertion',xf(fr.hex_y(x,-23,z,13,5.2)),targets)
            check(f'{tag} clamp {i} driver',xf(g.cylinder(2.5,35,(x,19.865,z),(0,1,0))),targets)
    for link,coords in [('femur',[(65,20.5,27.5)]),('tibia',[(36,0,11.5),(44,0,11.5)])]:
        targets=[p for p in parts if p['link']==link]
        for x,z,top in coords:
            check(f'{link} bridge {x} M30 shaft',g.cylinder(1.5,30,(x,-27.5,z),(0,1,0)),targets)
            check(f'{link} bridge {x} head',g.cylinder(2.85,3,(x,-30.5,z),(0,1,0)),targets)
            check(f'{link} bridge {x} washer',g.cut(g.cylinder(3.5,.5,(x,-27.5,z),(0,1,0)),g.cylinder(1.6,.7,(x,-27.6,z),(0,1,0))),targets)
            for lift in (0,1,3,7,12):check(f'{link} bridge {x} nut insertion lift {lift}',fr.hex_y(x,-1.0,z+lift,2.2,5.2),targets)
            check(f'{link} bridge {x} driver',g.cylinder(2.5,35,(x,-65.5,z),(0,1,0)),targets)
    # Captive post nuts are loaded laterally before fitting the lower arm.
    for y,z0 in [(-4.5,-41.5),(4.5,-37.5)]:
        targets=[p for p in parts if p['link']=='coxa']
        check(f'post {y} M20 shaft',g.cylinder(1.5,20,(40.5,y,-53.5)),targets)
        for shift in (0,3,6,10):check(f'post {y} nut insertion {shift}',leg._hex_z(40.5,y+math.copysign(shift,y),z0+.5,2.2,5.2),targets)
    # Bench screws use the available M18 size, top and bottom flat washers.
    for x,y in leg.CONSTANTS['mount_holes_xy']:
        check(f'bench M18 {x},{y}',g.cylinder(1.5,18,(x,y,-47)),[p for p in parts if p['link']=='base_mount'])
    pose_rows=[];cache={}
    print('Fastener checks',count,'failures',json.dumps(failures),flush=True)
    angles=list(itertools.product((-55,0,55),(-30,30,65),(5,81,115)))
    angles+=list(itertools.product((-60,0,60),(-35,70),(0,120)))
    for yaw,hip,knee in angles:
        frames={'base_mount':np.eye(4),'coxa':build.pose(rpy=(0,0,yaw))}
        frames['femur']=frames['coxa']@build.pose((82,0,0),(0,hip,0));frames['tibia']=frames['femur']@build.pose((90,0,0),(0,knee,0))
        world=[dict(p,shape=build.shape_at(p['shape'],frames[p['link']])) for p in parts]
        row={'angles_deg':[yaw,hip,knee],'intersections':[]}
        for i,a in enumerate(world):
            for b in world[i+1:]:
                if a['link']==b['link'] or not overlap(a['shape'],b['shape']):continue
                relative=np.linalg.inv(frames[a['link']])@frames[b['link']]
                key=(a['name'],b['name'],tuple(relative.round(7).ravel()))
                if key not in cache:
                    count+=1;cache[key]=g.common_volume(a['shape'],b['shape'])
                v=cache[key]
                if v>.01:row['intersections'].append({'a':a['name'],'b':b['name'],'mm3':v})
        for tag,link,reserve in [('yaw','base_mount',sc.plugged_profile_reserve()),('hip','coxa',leg._pitch(sc.plugged_profile_reserve(),False,82)),('knee','femur',leg._pitch(sc.plugged_profile_reserve(),False,90))]:
            tool=build.shape_at(reserve,frames[link])
            for p in world:
                if not p['printable'] or not overlap(tool,p['shape']):continue
                relative=np.linalg.inv(frames[link])@frames[p['link']]
                key=(tag+' cable',p['name'],tuple(relative.round(7).ravel()))
                if key not in cache:
                    count+=1;cache[key]=g.common_volume(tool,p['shape'])
                v=cache[key]
                if v>.01:row['intersections'].append({'a':tag+' cable reserve','b':p['name'],'mm3':v})
        if row['intersections']:failures.append(row)
        pose_rows.append(row)
        print('pose',yaw,hip,knee,'hits',len(row['intersections']),flush=True)
    assert source_hash==build.sha(OUT/'manifest.json'),'Manifest changed during verification'
    report={'status':'pass' if not failures else 'fail','manifest_sha256':source_hash,
        'boolean_checks':count,'solid_checks':solids,'failures':failures,'pose_samples':pose_rows,
        'nut_assumption':{'across_flats_mm':5.2,'thickness_mm':2.2,'measured':True,'precision':'Approximate user caliper readings'},
        'fastener_assumptions':{'shaft_diameter_mm':3,'head_diameter_envelope_mm':5.7,'head_height_envelope_mm':3,'flat_washer_thickness_mm':.5},
        'scope':'Independent nominal fastener and insertion envelopes, valid single solids, 27 operating combinations and 12 guard combinations. Flexible cable bend and continuous swept collision are not proven.'}
    (OUT/'verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'status':report['status'],'failures':failures,'boolean_checks':count}),flush=True)

if __name__=='__main__':main()
