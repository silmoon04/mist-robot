"""Package the full-size second trial and its support-disabled Cura profile."""
from pathlib import Path
import configparser
import hashlib
import importlib.util
import json
import sys
import zipfile
import trimesh
import numpy as np

HERE=Path(__file__).resolve().parent
DESIGN=HERE.parent/'hexapod_phone_quad_r5_20260912'
sys.path.insert(0,str(HERE.parent/'print_profiles_20260913'))
import build_profile as base


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    report=json.loads((HERE/'cad_checks.json').read_text())
    shapes=[];x=0;entries=[]
    for item in report['parts']:
        p=HERE/item['stl'];mesh=trimesh.load_mesh(p,process=True)
        assert sha(p)==item['stl_sha256']
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
        assert len(mesh.split())==1
        assert np.allclose(mesh.extents,item['dimensions_mm'],atol=.05)
        mesh.apply_translation(-mesh.bounds[0])
        mesh.apply_translation((x,0,0));x+=mesh.extents[0]+10
        shapes.append((item['name'],mesh));entries.append(item)
    combined=trimesh.util.concatenate([m for _,m in shapes])
    shift=[112.5-combined.bounds.mean(axis=0)[0],112.5-combined.bounds.mean(axis=0)[1],0]
    for _,m in shapes:m.apply_translation(shift)
    combined=trimesh.util.concatenate([m for _,m in shapes])
    combined.export(HERE/'Second_Print_Full_Clamp_NoSupports.stl')
    spec=importlib.util.spec_from_file_location('pack',DESIGN/'printing/pack_prints.py')
    pack=importlib.util.module_from_spec(spec);spec.loader.exec_module(pack)
    pack.three_mf(HERE/'Second_Print_Full_Clamp_NoSupports.3mf',shapes)
    scene=trimesh.load(HERE/'Second_Print_Full_Clamp_NoSupports.3mf')
    assert len(scene.geometry)==2
    prior=json.loads((HERE.parent/'quick_fit_20260913/infill_layer_options/comparison.json').read_text())
    values=dict(next(p['settings'] for p in prior['cases'] if p['name']=='028_5walls_15infill'))
    values.update(support_enable=False,support_interface_enable=False,
        support_roof_enable=False,support_bottom_enable=False,support_brim_enable=False,
        wall_overhang_angle=40,wall_overhang_speed_factors='[30, 25, 20]',
        cool_min_layer_time_overhang=12,cool_min_layer_time_overhang_min_segment_length=1,
        bridge_settings_enabled=True,bridge_wall_min_length=1,
        bridge_wall_speed=15,bridge_skin_speed=20,
        bridge_wall_material_flow=100,bridge_skin_material_flow=100,
        bridge_fan_speed=100,bridge_enable_more_layers=False,
        conical_overhang_enabled=False)
    schema=base.flatten(json.loads((base.CURA/'share/cura/resources/definitions/fdmprinter.def.json').read_text())['settings'])
    base.NAME='R5 Second Fit - No Supports - 0.28mm'
    glob={};ext={}
    for k,v in values.items():
        f=schema[k]
        if f['type']=='bool':assert type(v)==bool
        elif f['type']=='enum':assert v in f['options']
        elif f['type']=='[int]':assert all(type(x)==int and x>0 for x in json.loads(v))
        else:assert isinstance(v,(int,float)) and not isinstance(v,bool),(k,f['type'])
        (ext if f.get('settable_per_extruder',True) else glob)[k]=v
    profile=HERE/'Neptune4Pro_SecondFit_NoSupports_028.curaprofile'
    with zipfile.ZipFile(profile,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('r5_second_supportfree_global',base.serialize(glob,False))
        z.writestr('r5_second_supportfree_extruder0',base.serialize(ext,True))
    merged={}
    with zipfile.ZipFile(profile) as z:
        assert z.testzip() is None
        for name in z.namelist():
            p=configparser.ConfigParser(interpolation=None);p.read_string(z.read(name).decode());merged.update(p['values'])
    assert merged=={k:str(v) for k,v in values.items()}
    report['plate']={'3mf':'Second_Print_Full_Clamp_NoSupports.3mf',
        '3mf_sha256':sha(HERE/'Second_Print_Full_Clamp_NoSupports.3mf'),
        'stl':'Second_Print_Full_Clamp_NoSupports.stl','stl_sha256':sha(HERE/'Second_Print_Full_Clamp_NoSupports.stl'),
        'objects':2,'bounds_mm':combined.bounds.tolist(),'meshes_checked':True}
    report['profile']={'file':profile.name,'sha256':sha(profile),'name':base.NAME,
        'settings':values,'target':'Installed UltiMaker Cura 5.13, Neptune 4 Pro, 0.4 mm nozzle, PLA'}
    (HERE/'second_fit_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'profile':profile.name,'plate_objects':2,'bounds_mm':combined.bounds.tolist()}))


if __name__=='__main__':main()
