"""Pack next-stage fixtures and check the matching no-support profile."""
from pathlib import Path
import configparser
import gzip
import hashlib
import importlib.util
import json
import math
import sys
import zipfile
import numpy as np
import trimesh

HERE=Path(__file__).resolve().parent
DESIGN=HERE.parent/'hexapod_phone_quad_r5_20260912'
sys.path.insert(0,str(HERE.parent/'quick_fit_20260913'))
from build_quick_fit import VALUES as QUICK_VALUES
sys.path.insert(0,str(HERE.parent/'print_profiles_20260913'))
import build_profile as base
sys.path.insert(0,str(DESIGN/'manufacturing/slicing_r5'))
from engine_runner import slice_one
from deposition_properties import parse_gcode


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    data=json.loads((HERE/'cad_manifest.json').read_text())
    items=[];overhang=[]
    for p in data['parts']:
        mesh=trimesh.load_mesh(HERE/p['stl'],process=True)
        assert sha(HERE/p['stl'])==p['sha256']
        assert mesh.is_watertight and mesh.is_winding_consistent and len(mesh.split())==1
        assert np.allclose(mesh.extents,p['dimensions_mm'],atol=.05)
        steep=(mesh.face_normals[:,2]<-math.cos(math.pi/4)-1e-5)&(mesh.triangles[:,:,2].max(axis=1)>.001)
        area=float(mesh.area_faces[steep].sum());assert area<.001,(p['name'],area)
        overhang.append({'name':p['name'],'non_bed_area_steeper_than45_mm2':area})
        if mesh.extents[0]<mesh.extents[1]:mesh.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,(0,0,1)))
        mesh.apply_translation(-mesh.bounds[0]);items.append((p,mesh))
    items.sort(key=lambda p:(-p[1].extents[1],-p[1].extents[0]))
    x=y=height=0.;placed=[];positions=[]
    for p,mesh in items:
        w,h=mesh.extents[:2]
        if x+w>195:x=0;y+=height+9;height=0
        mesh.apply_translation((x,y,0));placed.append((p['name'],mesh))
        positions.append({'name':p['name'],'bounds_mm':mesh.bounds.tolist()})
        x+=w+9;height=max(height,h)
    allmesh=trimesh.util.concatenate([m for _,m in placed]);shift=np.array([112.5,112.5,0])-np.r_[allmesh.bounds.mean(axis=0)[:2],0]
    for _,mesh in placed:mesh.apply_translation(shift)
    positions=[{'name':name,'bounds_mm':mesh.bounds.tolist()} for name,mesh in placed]
    allmesh=trimesh.util.concatenate([m for _,m in placed])
    assert np.all(allmesh.bounds[0,:2]>5) and np.all(allmesh.bounds[1,:2]<220)
    plate=HERE/'Third_Print_Joint_Interfaces.3mf';stl=plate.with_suffix('.stl')
    allmesh.export(stl)
    spec=importlib.util.spec_from_file_location('pack',DESIGN/'printing/pack_prints.py')
    pack=importlib.util.module_from_spec(spec);spec.loader.exec_module(pack)
    pack.three_mf(plate,placed);assert len(trimesh.load(plate).geometry)==len(data['parts'])
    values=dict(QUICK_VALUES)
    prior=json.loads((HERE.parent/'second_fit_supportfree_20260913/second_fit_validation.json').read_text())['profile']['settings']
    for key in ['support_enable','support_interface_enable','support_roof_enable','support_bottom_enable',
                'support_brim_enable','wall_overhang_angle','wall_overhang_speed_factors',
                'cool_min_layer_time_overhang','cool_min_layer_time_overhang_min_segment_length',
                'bridge_settings_enabled','bridge_wall_min_length','bridge_wall_speed','bridge_skin_speed',
                'bridge_wall_material_flow','bridge_skin_material_flow','bridge_fan_speed',
                'bridge_enable_more_layers','conical_overhang_enabled']:
        values[key]=prior[key]
    values['brim_gap']=.15
    base.NAME='R5 Third Fit - Joint Interfaces - 0.20mm'
    schema=base.flatten(json.loads((base.CURA/'share/cura/resources/definitions/fdmprinter.def.json').read_text())['settings'])
    glob={};ext={}
    for k,v in values.items():
        f=schema[k]
        if f['type']=='enum':assert v in f['options']
        elif f['type']=='bool':assert type(v)==bool
        elif f['type']=='[int]':assert all(type(i)==int for i in json.loads(v))
        else:assert isinstance(v,(int,float)) and not isinstance(v,bool)
        (ext if f.get('settable_per_extruder',True) else glob)[k]=v
    profile=HERE/'Neptune4Pro_ThirdFit_Joints_NoSupports_020.curaprofile'
    with zipfile.ZipFile(profile,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('r5_third_joint_fit_global',base.serialize(glob,False))
        z.writestr('r5_third_joint_fit_extruder0',base.serialize(ext,True))
    merged={}
    with zipfile.ZipFile(profile) as z:
        assert z.testzip() is None
        for name in z.namelist():
            p=configparser.ConfigParser(interpolation=None);p.read_string(z.read(name).decode());merged.update(p['values'])
    assert merged=={k:str(v) for k,v in values.items()}
    result=slice_one(stl,HERE/'analysis','third_joint_fit',values)
    raw=Path(result['raw_temporary_path']);text=raw.read_text(encoding='utf-8')
    parsed=parse_gcode(text,result['gcode_to_source_transform'],layer_height_mm=.2)
    support=parsed['properties']['support']['mass_g']
    peak=max(p.get('peak_nominal_deposition_flow_mm3_s',0) for p in parsed['properties'].values())
    assert support==0 and peak<8.1 and result['motion_inside_build_envelope']
    disabled='; ANALYSIS ONLY. DO NOT PRINT.\n'+'\n'.join(
        line if not line.strip() or line.lstrip().startswith(';') else '; DISABLED| '+line for line in text.splitlines())
    archived=HERE/'analysis/third_joint_fit.ANALYSIS_ONLY.gcode.gz';archived.write_bytes(gzip.compress(disabled.encode()))
    assert raw.resolve().parent==(HERE/'analysis').resolve();raw.unlink()
    data['plate']={'file':plate.name,'sha256':sha(plate),'stl':stl.name,'stl_sha256':sha(stl),
        'object_count':len(data['parts']),'bounds_mm':allmesh.bounds.tolist(),'positions':positions}
    data['mesh_checks']=overhang
    data['profile']={'file':profile.name,'sha256':sha(profile),'name':base.NAME,'settings':values}
    data['slice_trial']={'engine_version':result['engine_version'],'model_g':parsed['properties']['model']['mass_g'],
        'support_g':support,'adhesion_g':parsed['properties']['adhesion']['mass_g'],
        'estimated_hours':result['estimated_time_seconds']/3600,'peak_nominal_flow_mm3_s':peak,
        'motion_bounds_mm':result['motion_bounds_mm'],'within_bed':True,
        'method':'Process values applied to the explicit CuraEngine analysis stack. Actual Cura/printer results can differ.',
        'archived_inert_toolpath_sha256':sha(archived)}
    data['source_files_sha256']={str(p):sha(p) for p in [HERE/'build_joint_plate.py',HERE/'pack_and_slice.py',
        DESIGN/'cad/fit_coupons.py',DESIGN/'cad/leg.py',DESIGN/'cad/servo_contract.py']}
    data['status']='CAD, mesh, profile and engine checks pass; physical interface tests pending'
    (HERE/'third_fit_validation.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps({'plate':data['plate']['file'],'parts':len(data['parts']),'slice':data['slice_trial']}))


if __name__=='__main__':main()
