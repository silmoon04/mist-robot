"""Expand the unprinted third-fit plate using the same Cura profile bytes."""
from pathlib import Path
import configparser
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import shutil
import sys
import zipfile
import numpy as np
import trimesh

HERE=Path(__file__).resolve().parent
THIRD=HERE.parent/'third_fit_joints_20260913'
DESIGN=HERE.parent/'hexapod_phone_quad_r5_20260912'
sys.path.insert(0,str(DESIGN/'manufacturing/slicing_r5'))
from engine_runner import slice_one
from deposition_properties import parse_gcode


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    HERE.mkdir(exist_ok=True)
    old=json.loads((THIRD/'third_fit_validation.json').read_text())
    cad=json.loads((DESIGN/'cad/output/assembly_manifest.json').read_text())
    entries=[]
    for p in old['parts']:
        entries.append(dict(p,source=str(THIRD/p['stl']),source_sha256=p['sha256'],
            extra=False,additional_print_rotation_x_deg=0))
    for sku in ['coxa_lower_auxiliary_arm']+[f'pan_cover_spacer_{i}' for i in range(1,5)]:
        p=next(p for p in cad['print_parts'] if p['sku']==sku)
        name='08_lower_yaw_support_arm' if sku=='coxa_lower_auxiliary_arm' else '09_'+sku
        path=DESIGN/'cad/output'/p['stl']
        entries.append(dict(name=name,source=str(path),source_sha256=sha(path),sku=sku,
            extra=True,additional_print_rotation_x_deg=180 if sku=='coxa_lower_auxiliary_arm' else 0,
            purpose='Fit to the supplied auxiliary disc with the four nominal yaw spacers.' if sku=='coxa_lower_auxiliary_arm' else
                    'Reserve this 4 mm spacer for a phone-pan mounting foot later. It is not a yaw or gauge spacer.'))
    items=[];mesh_checks=[]
    for p in entries:
        path=Path(p['source']);assert sha(path)==p['source_sha256']
        mesh=trimesh.load_mesh(path,process=True)
        assert mesh.is_watertight and mesh.is_winding_consistent and len(mesh.split())==1
        source_volume=float(mesh.volume)
        angle=p['additional_print_rotation_x_deg']
        if angle:mesh.apply_transform(trimesh.transformations.rotation_matrix(math.radians(angle),(1,0,0)))
        if mesh.extents[0]<mesh.extents[1]:mesh.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,(0,0,1)))
        mesh.apply_translation(-mesh.bounds[0])
        mask=(mesh.face_normals[:,2]<-math.cos(math.pi/4)-1e-5)&(mesh.triangles[:,:,2].max(axis=1)>.001)
        steep=float(mesh.area_faces[mask].sum());assert steep<.001,(p['name'],steep)
        assert abs(mesh.volume-source_volume)<1e-6
        p['dimensions_mm']=mesh.extents.tolist();p['print_stl']=p['name']+'.stl'
        mesh.export(HERE/p['print_stl']);p['print_stl_sha256']=sha(HERE/p['print_stl'])
        mesh_checks.append({'name':p['name'],'watertight_single_component':True,
            'non_bed_area_steeper_than45_mm2':steep,'source_volume_preserved':True})
        items.append((p,mesh))
    items.sort(key=lambda p:(-p[1].extents[1],-p[1].extents[0]))
    x=y=height=0.;placed=[]
    for p,mesh in items:
        w,h=mesh.extents[:2]
        if x+w>195:x=0;y+=height+9;height=0
        mesh.apply_translation((x,y,0));placed.append((p['name'],mesh));x+=w+9;height=max(height,h)
    combined=trimesh.util.concatenate([m for _,m in placed])
    shift=np.array([112.5,112.5,0])-np.r_[combined.bounds.mean(axis=0)[:2],0]
    for _,m in placed:m.apply_translation(shift)
    combined=trimesh.util.concatenate([m for _,m in placed])
    assert np.all(combined.bounds[0,:2]>5) and np.all(combined.bounds[1,:2]<220)
    positions=[{'name':name,'bounds_mm':m.bounds.tolist()} for name,m in placed]
    plate=HERE/'Expanded_Joint_Plate_3to4h.3mf';stl=plate.with_suffix('.stl');combined.export(stl)
    spec=importlib.util.spec_from_file_location('pack',DESIGN/'printing/pack_prints.py')
    pack=importlib.util.module_from_spec(spec);spec.loader.exec_module(pack)
    pack.three_mf(plate,placed)
    assert len(trimesh.load(plate).geometry)==19
    profile=HERE/old['profile']['file'];shutil.copy2(THIRD/old['profile']['file'],profile)
    assert sha(profile)==old['profile']['sha256']
    values=old['profile']['settings'];merged={}
    with zipfile.ZipFile(profile) as z:
        assert z.testzip() is None
        for n in z.namelist():
            p=configparser.ConfigParser(interpolation=None);p.read_string(z.read(n).decode());merged.update(p['values'])
    assert merged=={k:str(v) for k,v in values.items()}
    result=slice_one(stl,HERE/'analysis','expanded_joint_plate',values)
    raw=Path(result['raw_temporary_path']);text=raw.read_text(encoding='utf-8')
    parsed=parse_gcode(text,result['gcode_to_source_transform'],layer_height_mm=.2)
    peak=max(p.get('peak_nominal_deposition_flow_mm3_s',0) for p in parsed['properties'].values())
    assert result['motion_inside_build_envelope'] and parsed['properties']['support']['mass_g']==0 and peak<8.1
    inert='; ANALYSIS ONLY. DO NOT PRINT.\n'+'\n'.join(line if not line.strip() or line.lstrip().startswith(';') else '; DISABLED| '+line for line in text.splitlines())
    archive=HERE/'analysis/expanded_joint_plate.ANALYSIS_ONLY.gcode.gz';archive.write_bytes(gzip.compress(inert.encode()))
    assert raw.resolve().parent==(HERE/'analysis').resolve();raw.unlink()
    trial={'estimated_hours':result['estimated_time_seconds']/3600,
        'model_g':parsed['properties']['model']['mass_g'],'support_g':parsed['properties']['support']['mass_g'],
        'brim_g':parsed['properties']['adhesion']['mass_g'],'peak_nominal_flow_mm3_s':peak,
        'motion_bounds_mm':result['motion_bounds_mm'],'within_bed':True,
        'method':'Existing profile process values on the explicit CuraEngine analysis stack; live Cura and printer times can differ.'}
    report={'status':'mesh_profile_and_slice_checks_pass','parts':entries,'mesh_checks':mesh_checks,
        'source_cad_manifest_sha256':sha(DESIGN/'cad/output/assembly_manifest.json'),
        'original_third_plate_validation_sha256':sha(THIRD/'third_fit_validation.json'),
        'plate':{'file':plate.name,'sha256':sha(plate),'stl':stl.name,'stl_sha256':sha(stl),
                 'object_count':19,'positions':positions,'bounds_mm':combined.bounds.tolist()},
        'profile':{'file':profile.name,'sha256':sha(profile),'name':old['profile']['name'],'unchanged':True},
        'slice_trial':trial,
        'selection_reason':'Add a standard-interface lower yaw arm and four simple phone-pan foot spacers. Avoid committing to more complete legs before horn and shaft tests.',
        'limits':['The added pieces are lower-risk candidates, not physically guaranteed fits.',
            'The lower arm is flipped to put its recessed screw seats upward during printing. Preserve the supplied orientation.',
            'Fit the lower arm only after the auxiliary disc and centre retainer are installed. This is an unloaded interface test.',
            'The four phone-pan foot spacers are for later assembly, not the current horn fixture.']}
    (HERE/'expanded_plate_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with (HERE/'PARTS.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['name','added_now','purpose','source_sha256']);w.writerows((p['name'],p['extra'],p['purpose'],p['source_sha256']) for p in entries)
    print(json.dumps({'count':19,'profile_unchanged':True,'trial':trial}),flush=True)
    assert 3<=trial['estimated_hours']<=4


if __name__=='__main__':main()
