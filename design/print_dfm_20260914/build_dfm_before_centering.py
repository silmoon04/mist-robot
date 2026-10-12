"""Localized coxa print improvements; preserve the fitted R7 interfaces."""
from pathlib import Path
import sys,json,shutil,hashlib,math
import numpy as np
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'single_leg_r7_wide_joints_20260914';OUT=ROOT/'output'
sys.path.insert(0,str(OLD/'cad'))
import build,leg,geom as g

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def roof_z(x,y,z,h,r):
    q=r/math.sqrt(2)
    return g.prism_xy([(x-q,y+q),(x,y+r*math.sqrt(2)),(x+q,y+q)],z,h)

def main():
    OUT.mkdir(exist_ok=True)
    for folder in ('print_stl','assembly_mesh','parts_step','links'):
        shutil.copytree(OLD/'output'/folder,OUT/folder,dirs_exist_ok=True)
    manifest=json.loads((OLD/'output/manifest.json').read_text());parts,frames=build.load_assembly();old={p['name']:p['shape'] for p in parts}
    polygon=[(-8,-17.5),(8,-17.5),(14,-11.5),(14,6),(6,14),(-6,14),(-14,6),(-14,-11.5)]
    changes=[];additions=[]
    for name,z,h in [('coxa_upper_and_hip_saddle',4.5,4),('coxa_lower_auxiliary_arm',-53,9)]:
        part=next(p for p in parts if p['name']==name);shape=g.fuse(part['shape'],g.prism_xy(polygon,z,h))
        if 'upper' in name:
            rail=[(0,-17.5),(33,-17.5),(36.5,-14),(36.5,-11.5),(0,-11.5)]
            shape=g.fuse(shape,g.prism_xy(rail,z,h))
            # A narrow bed-starting web supports the bottom of the post.
            # Reopen the driver channel and the lower nut's loading route.
            shape=g.fuse(shape,leg._b(36.5,39.0,-17.5,-11.5,-44,-34))
            shape=g.cut(shape,g.cylinder(4,42,(43.085,-13,-60)),
                        leg._b(37.6,43.4,-18,-4.5,-41.5,-38.8))
            # Fill the one-millimetre floating lip at the front saddle foot.
            shape=g.fuse(shape,leg._pitch(leg._b(17.115,18.115,-16.365,11.565,-32,-28.9),False,82))
        shape=leg._horn_holes_z(shape)
        # Flat-top hex retains the original 7 mm circular clearance and
        # replaces the steep circular ceiling with a short 4.04 mm bridge.
        radius=7/math.sqrt(3)
        shape=g.cut(shape,g.prism_xy([(radius*math.cos(i*math.pi/3),radius*math.sin(i*math.pi/3)) for i in range(6)],z-.1,h+.2))
        if 'lower' in name:
            shape=g.cut(shape,*[g.cylinder(4.1,3.6,(x,y,-53.1)) for x,y in ((7,0),(-7,0),(0,7),(0,-7))])
        for x,y in ((7,0),(-7,0),(0,7),(0,-7)):
            shape=g.cut(shape,roof_z(x,y,z-.1,h+.2,1.7))
        # The post screw centres remain shared with the matching lower arm.
        for y in (-4.5,4.5):shape=g.cut(shape,roof_z(40.5,y,-55,26,1.7))
        if 'upper' in name:
            for y,z0 in [(-4.5,-41.5),(4.5,-37.5)]:
                half=2.8;a=half/math.sqrt(3)
                shape=g.cut(shape,g.prism_xy([(40.5-half,y+a),(40.5,y+a+half),(40.5+half,y+a)],z0,2.7))
        assert g.valid(shape)
        additions.append((name,g.cut(shape,old[name])))
        part['shape']=shape
        entry=next(p for p in manifest['parts'] if p['name']==name)
        rotated=g.transform(shape,rpy_deg=entry['print_rotation']);lo,hi=g.bounds(rotated);rotated=g.translate(rotated,tuple(-v for v in lo))
        g.export_stl(rotated,OUT/entry['print_stl'],.04);g.export_stl(shape,OUT/entry['assembly_stl'],.04);g.export_step(shape,OUT/'parts_step'/(name+'.step'))
        entry.update(dimensions_mm=[hi[i]-lo[i] for i in range(3)],volume_mm3=g.volume(shape),com_mm=g.centroid(shape),solid_mass_kg=g.volume(shape)*.00000124,stl_sha256=sha(OUT/entry['print_stl']))
        changes.append({'part':name,'net_volume_change_mm3':g.volume(shape)-g.volume(old[name]),'added_material_mm3':g.volume(additions[-1][1])})
    # Preserve R7 clearance evidence by checking all added material at the
    # exact 39 previously checked poses. Subtractions cannot add collisions.
    previous=json.loads((OLD/'output/verification.json').read_text());assert previous['status']=='pass'
    assert previous['manifest_sha256']==sha(OLD/'output/manifest.json')
    hits=[];boolean_checks=0;bbox_checks=0
    corners={}
    for p in parts:
        lo,hi=g.bounds(p['shape']);corners[p['name']]=np.array([[x,y,z,1] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])])
    for pose in previous['pose_samples']:
        yaw,hip,knee=pose['angles_deg'];f={'base_mount':np.eye(4),'coxa':build.pose(rpy=(0,0,yaw))}
        f['femur']=f['coxa']@build.pose((82,0,0),(0,hip,0));f['tibia']=f['femur']@build.pose((90,0,0),(0,knee,0))
        for name,added in additions:
            a=build.shape_at(added,f['coxa']);aa=g.bounds(a)
            for p in parts:
                if p['name']==name:continue
                xyz=(corners[p['name']]@f[p['link']].T)[:,:3];bb=[xyz.min(axis=0),xyz.max(axis=0)];bbox_checks+=1
                if any(aa[1][i]<=bb[0][i]+1e-6 or bb[1][i]<=aa[0][i]+1e-6 for i in range(3)):continue
                b=build.shape_at(p['shape'],f[p['link']]);boolean_checks+=1;v=g.common_volume(a,b)
                if v>.01:hits.append({'pose':pose['angles_deg'],'added_part':name,'other':p['name'],'mm3':v})
    # The original circular hole envelopes remain open, including washer
    # counterbores. These tests cover the regions refilled by the flange union.
    for name,z,h in [('coxa_upper_and_hip_saddle',4.5,4),('coxa_lower_auxiliary_arm',-53,9)]:
        shape=next(p['shape'] for p in parts if p['name']==name)
        for x,y,r in [(0,0,3.5),(7,0,1.7),(-7,0,1.7),(0,7,1.7),(0,-7,1.7)]:
            assert g.common_volume(shape,g.cylinder(r,h,(x,y,z)))<.001
        if 'lower' in name:
            for x,y in ((7,0),(-7,0),(0,7),(0,-7)):assert g.common_volume(shape,g.cylinder(4.1,3.5,(x,y,-53)))<.001
        else:
            for y in (-20,-16,-12,-8,-4.5):
                assert g.common_volume(shape,leg._hex_z(40.5,y,-41,2.2,5.2))<.001
    assert not hits,hits
    g.export_step([p['shape'] for p in parts if p['link']=='coxa'],OUT/'links/coxa.step')
    g.export_step([build.shape_at(p['shape'],frames[p['link']]) for p in parts],OUT/'Assembly_DFM.step')
    manifest.update(revision='r7_coxa_dfm_20260914',baseline_manifest_sha256=sha(OLD/'output/manifest.json'),dfm_source_sha256=sha(__file__))
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    report={'status':'pass','changes':changes,'conservative_bounding_box_checks':bbox_checks,'added_material_collision_checks':boolean_checks,'sampled_poses':39,'intersections':hits,'original_circular_hole_and_counterbore_envelopes_clear':True,
        'baseline_verification_sha256':sha(OLD/'output/verification.json'),'manifest_sha256':sha(OUT/'manifest.json'),
        'limits':'Reuses R7 sampled clearance evidence plus explicit addition checks. This is not a new structural load qualification or a continuous collision proof.'}
    (OUT/'DFM_Check.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
    for n in ['prepare_prints.py','check_supports.py','check_sections.py']:
        shutil.copy2(OLD/n,ROOT/n)
    shutil.copy2(OLD/'output/Tree_Undersides_R7_PLA_028.curaprofile',OUT/'Tree_Undersides_R7_PLA_028.curaprofile')

if __name__=='__main__':main()
