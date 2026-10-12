"""Build matching process profiles and actual CuraEngine plate estimates."""
from pathlib import Path
import sys,json,zipfile,hashlib,gzip,concurrent.futures,importlib.util
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent.parent
OUT=ROOT/'output'
sys.path.insert(0,str(PROJECT/'design/hexapod_phone_quad_r5_20260912/manufacturing/slicing_r5'))
from engine_runner import slice_one
from deposition_properties import parse_gcode
sys.path.insert(0,str(PROJECT/'design/hexapod_phone_quad_r5_20260912/printing'))
from pack_prints import three_mf
spec=importlib.util.spec_from_file_location('profile_tools',PROJECT/'design/print_profiles_20260913/build_profile.py');pt=importlib.util.module_from_spec(spec);spec.loader.exec_module(pt)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def profile(support):
    values=json.loads((PROJECT/'design/third_fit_joints_20260913/third_fit_validation.json').read_text())['profile']['settings']
    values.update(layer_height=.28,layer_height_0=.28,infill_sparse_thickness=.28,
        top_bottom_thickness=1.4,top_thickness=1.4,bottom_thickness=1.4,top_layers=5,bottom_layers=5,
        infill_sparse_density=25,speed_print=65,speed_wall=55,speed_wall_0=40,speed_wall_x=65,speed_infill=65,speed_topbottom=40,
        support_enable=support,support_type='buildplate',support_structure='tree',support_angle=60,
        support_interface_enable=support,support_roof_enable=support,support_roof_density=40,support_interface_density=40,
        support_interface_height=.56,support_roof_height=.56,support_z_distance=.56,support_top_distance=.56,support_bottom_distance=.28,
        support_xy_distance=2.0,support_xy_overrides_z='xy_overrides_z',support_brim_enable=support,
        support_tree_angle=45,support_tree_angle_slow=30,support_tree_branch_diameter=2,support_tree_tip_diameter=.8,
        support_tree_branch_reach_limit=30,support_tree_rest_preference='buildplate',
        cool_fan_full_at_height=.84,brim_width=4,brim_line_count=10,brim_gap=.15)
    return values

def write_profile(support):
    values=profile(support);kind='Tree_Undersides' if support else 'No_Support'
    schema=pt.flatten(json.loads((pt.CURA/'share/cura/resources/definitions/fdmprinter.def.json').read_text())['settings'])
    gv={};ev={}
    for k,v in values.items():
        f=schema[k]
        if f['type']=='enum':assert v in f['options'],(k,v)
        (ev if f.get('settable_per_extruder',True) else gv)[k]=v
    pt.NAME='Single Leg R7 PLA 0.28 '+kind.replace('_',' ')
    path=OUT/(kind+'_R7_PLA_028.curaprofile')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('r7_'+kind+'_global',pt.serialize(gv,False));z.writestr('r7_'+kind+'_extruder_0',pt.serialize(ev,True))
    with zipfile.ZipFile(path) as z:assert z.testzip() is None
    return {'file':path.name,'sha256':sha(path),'settings':values}

def make_plate(name,names):
    manifest=json.loads((OUT/'manifest.json').read_text());by={p['name']:p for p in manifest['parts']}
    x=y=0.;height=0.;placed=[];rows=[]
    for n in names:
        p=by[n];m=trimesh.load_mesh(OUT/p['print_stl'],process=True)
        assert m.is_watertight and m.is_winding_consistent and m.volume>0,n
        assert np.allclose(m.extents,p['dimensions_mm'],atol=.05),n
        w,h=m.extents[:2]
        if x+w>195:x=0;y+=height+12;height=0
        assert y+h<=195,(name,n,y+h)
        m.apply_translation(-m.bounds[0]+[x,y,0]);placed.append((n,m));rows.append({'name':n,'source_sha256':p['stl_sha256'],'lower_corner_mm':[x,y,0]})
        x+=w+12;height=max(height,h)
    plate=trimesh.util.concatenate([m for n,m in placed]);shift=np.array([112.5,112.5,0])-np.r_[plate.bounds[:,:2].mean(axis=0),0]
    for n,m in placed:m.apply_translation(shift)
    plate=trimesh.util.concatenate([m for n,m in placed])
    path=OUT/'plates'/(name+'.stl');plate.export(path);three_mf(path.with_suffix('.3mf'),placed)
    return {'name':name,'stl':str(path.relative_to(OUT)),'three_mf':str(path.with_suffix('.3mf').relative_to(OUT)),
        'parts':rows,'bounds_mm':plate.bounds.tolist(),'sha256':sha(path)}

def slice_plate(row):
    supported=row['name'].startswith(('02','03','04'))
    r=slice_one(OUT/row['stl'],ROOT/'analysis_slices',row['name'],profile(supported))
    raw=Path(r['raw_temporary_path']);text=raw.read_text();data=parse_gcode(text,r['gcode_to_source_transform'],layer_height_mm=.28)
    with gzip.open(raw.with_name(row['name']+'.analysis_only.gcode.gz'),'wt',encoding='utf-8') as f:
        f.write('; ANALYSIS ONLY. Every command is disabled. Slice the supplied 3MF in Cura.\n')
        f.writelines(line if line.startswith(';') else '; DISABLED '+line for line in text.splitlines(keepends=True))
    raw.unlink()
    r['raw_file_disposition']='Consumed for analysis, all commands disabled, compressed, and original temporary file removed.'
    row.update(profile=('Tree_Undersides' if supported else 'No_Support')+'_R7_PLA_028.curaprofile',engine=r,deposition=data)
    print(row['name'],r['estimated_time_seconds'],flush=True)
    return row

def main():
    (OUT/'plates').mkdir(exist_ok=True)
    profiles=[write_profile(False),write_profile(True)]
    groups=[('01_ribbed_mount_and_caps',['bench_mounting_plate','case_cap_yaw','case_cap_hip']),
        ('02_coxa_and_saddle',['coxa_upper_and_hip_saddle','yaw_case_saddle']),
        ('03_femur_lower_arm_and_knee_cap',['femur_main_and_knee_saddle','coxa_lower_auxiliary_arm','case_cap_knee']),
        ('04_tibia_and_cheeks',['tibia_curved_main_and_foot','femur_auxiliary_cheek','tibia_auxiliary_cheek',*[f'yaw_auxiliary_spacer_{i}' for i in range(1,5)]])]
    rows=[make_plate(n,parts) for n,parts in groups]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(slice_plate,rows))
    result={'manifest_sha256':sha(OUT/'manifest.json'),'profiles':profiles,'plates':rows,
        'limits':'Engine estimates exclude printer heating and actual firmware motion differences. Supports and dimensions require physical evaluation.'}
    (OUT/'print_validation.json').write_text(json.dumps(result,indent=2))

if __name__=='__main__':main()
