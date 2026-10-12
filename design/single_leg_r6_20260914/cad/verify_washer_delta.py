"""Transfer a sampled clearance result through a proven subtractive revision."""
from pathlib import Path
import json,numpy as np
import build,leg,geom as g
ROOT=build.ROOT;OUT=build.OUT;BASE=ROOT/'washer_baseline'

def main():
    old_manifest=json.loads((BASE/'manifest_before.json').read_text());old_check=json.loads((BASE/'verification_before.json').read_text());new=json.loads((OUT/'manifest.json').read_text())
    assert old_check['status']=='pass'
    assert old_check['manifest_sha256']==build.sha(BASE/'manifest_before.json')
    before={p['name']:p for p in old_manifest['parts']};after={p['name']:p for p in new['parts']}
    changed=[]
    for name,p in after.items():
        assert p['transform']==before[name]['transform']
        if p.get('stl_sha256')!=before[name].get('stl_sha256'):changed.append(name)
    baselines={'coxa_lower_auxiliary_arm':'lower_before.step','femur_auxiliary_cheek':'femur_aux_before.step','tibia_auxiliary_cheek':'tibia_aux_before.step'}
    assert set(changed)==set(baselines),changed
    parts,frames=build.load_assembly();subset=[]
    for name,file in baselines.items():
        current=next(p['shape'] for p in parts if p['name']==name);old=g.import_step(BASE/file)
        common=g.common_volume(old,current);added=g.volume(current)-common
        assert abs(added)<1e-5,'The change must only remove material'
        subset.append({'part':name,'new_geometry_outside_old_mm3':added,'removed_volume_mm3':g.volume(old)-g.volume(current)})
    hits=[]
    for x,y in ((7,0),(-7,0),(0,7),(0,-7)):
        washer=g.cut(g.cylinder(3.85,1,(x,y,-50.5)),g.cylinder(1.6,1.2,(x,y,-50.6)))
        head=g.cylinder(2.85,3,(x,y,-53.5));shaft=g.cylinder(1.5,20,(x,y,-50.5))
        for tag,shape in [('two OD7.7 washers',washer),('M20 head',head),('M20 shaft',shaft)]:
            for p in parts:
                if p['link']!='coxa' or not p['printable']:continue
                a,b=g.bounds(shape),g.bounds(p['shape'])
                if any(a[1][k]<=b[0][k] or b[1][k]<=a[0][k] for k in range(3)):continue
                v=g.common_volume(shape,p['shape'])
                if v>.01:hits.append({'part':p['name'],'hardware':tag,'mm3':v})
    def ring(point,axis=(0,0,1),thickness=.5):
        return g.cut(g.cylinder(3.85,thickness,point,axis),g.cylinder(1.6,thickness,point,axis))
    hardware=[]
    import servo_contract as sc
    from hip_revision import HIP_CLAMP_BOLT_XZ
    for link,bolts,xf in [('base_mount',sc.CLAMP_BOLT_XZ,lambda s:s),('coxa',HIP_CLAMP_BOLT_XZ,lambda s:leg._pitch(s,False,70)),('femur',sc.CLAMP_BOLT_XZ,lambda s:leg._pitch(s,False,90))]:
        for x,z in bolts:hardware.append((link,'case washer',xf(ring((x,16.365,z),(0,1,0)))))
    for x,y in ((7,0),(-7,0),(0,7),(0,-7)):hardware.append(('coxa','yaw main washer',ring((x,y,8.5))))
    hardware.append(('coxa','yaw centre washer',ring((0,0,-33.6))))
    for link in ('femur','tibia'):
        for x,z in ((7,0),(-7,0),(0,7),(0,-7)):
            hardware.append((link,'main washer',ring((x,23,z),(0,1,0))))
            hardware.append((link,'auxiliary washers',ring((x,-24,z),(0,1,0),1)))
        hardware.append((link,'auxiliary centre washer',ring((0,-19.1,0),(0,1,0))))
    for link,coords in [('femur',[(65,20.5)]),('tibia',[(36,0),(44,0)])]:
        for x,z in coords:hardware.append((link,'bridge washer',ring((x,-23.5,z),(0,1,0))))
    for y in (-4.5,4.5):hardware.append(('coxa','post washer',ring((28.5,y,-53.5))))
    for x,y in leg.CONSTANTS['mount_holes_xy']:
        hardware.append(('base_mount','bench head directly on foot',g.cylinder(2.85,3,(x,y,-29))))
        hardware.append(('base_mount','bench M18 shaft without top washer',g.cylinder(1.5,18,(x,y,-47))))
        hardware.append(('base_mount','bench bottom washer',ring((x,y,-39.5))))
    for link,tag,shape in hardware:
        for p in parts:
            if p['link']!=link:continue
            a,b=g.bounds(shape),g.bounds(p['shape'])
            if any(a[1][k]<=b[0][k]+1e-6 or b[1][k]<=a[0][k]+1e-6 for k in range(3)):continue
            v=g.common_volume(shape,p['shape'])
            if v>.01:hits.append({'part':p['name'],'hardware':tag,'mm3':v})
    print('Hardware intersections',hits,flush=True)
    assert not hits,hits
    report=dict(old_check);report.update(manifest_sha256=build.sha(OUT/'manifest.json'),
        baseline_manifest_sha256=build.sha(BASE/'manifest_before.json'),baseline_verification_sha256=build.sha(BASE/'verification_before.json'),
        washer_revision={'changed_parts':subset,
            'new_counterbore_diameter_mm':8.2,'auxiliary_centre_opening_diameter_mm':8.4,'washer_outer_diameter_envelope_mm':7.7,'new_hardware_intersections':hits,
            'bench_stack':'M18 heads bear directly on printed mounting feet; one flat washer per nut underneath. OD7.7 top washers collide with the servo clamp and must be omitted.',
            'reason':'All link transforms and other printed meshes are unchanged. Changed pieces are strict subsets of their collision-checked predecessors, so they cannot introduce a new rigid-body intersection at those poses. New washer/head/shaft envelopes were checked locally.'})
    (OUT/'verification.json').write_text(json.dumps(report,indent=2));print(report['washer_revision'])

if __name__=='__main__':main()
