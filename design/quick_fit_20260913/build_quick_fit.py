"""Split the first-fit plate into useful small jobs without changing its parts."""
from pathlib import Path
import configparser
import importlib.util
import json
import sys
import zipfile
import hashlib
import trimesh
import numpy as np

HERE=Path(__file__).resolve().parent
DESIGN=HERE.parent/'hexapod_phone_quad_r5_20260912'
sys.path.insert(0,str(HERE.parent/'print_profiles_20260913'))
import build_profile as original

NAME='HexQuad R5 - Quick Fit PLA - 0.20mm'
PROFILE=HERE/'Neptune4Pro_R5_QuickFit_PLA_020.curaprofile'
VALUES=dict(original.VALUES)
VALUES.update(speed_print=80,speed_wall=65,speed_wall_0=50,speed_wall_x=80,
    speed_infill=90,speed_topbottom=45,speed_roofing=35,
    speed_support=60,speed_support_infill=60,speed_support_interface=35,
    speed_support_roof=35,speed_support_bottom=35,
    speed_layer_0=25,speed_print_layer_0=25,skirt_brim_speed=25,
    acceleration_print=2500,acceleration_wall=1800,acceleration_wall_0=1200,
    acceleration_wall_x=2000,acceleration_infill=2500,
    acceleration_support=1800,acceleration_support_infill=1800,
    acceleration_travel=3000)
GROUPS={
    '01_servo_case_fit':[
        'r5_case_datum_saddle_0p3','r5_case_cap_0p3'],
    '02_alignment_and_horns':[
        'r5_case_to_shaft_registration_plate','r5_m3_clearance_3p2_3p4_3p6',
        'r5_horn_fixture_main','r5_horn_fixture_auxiliary','r5_horn_fixture_bridge_38',
        'r5_yaw_spacer_11p6','r5_top_bridge_load_aux'],
    '03_phone_fit':[
        'phone_fit_0p5_tray','phone_fit_0p5_clip_left','phone_fit_0p5_clip_right',
        'phone_usb_spine_6mm_coupon'],
    '04_pan_hub_and_bridge':[
        'phone_pan_horn_stack_fit','r5_top_bridge_load_main'],
}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    HERE.mkdir(parents=True,exist_ok=True)
    original.NAME=NAME
    schema=original.flatten(json.loads((original.CURA/'share/cura/resources/definitions/fdmprinter.def.json').read_text())['settings'])
    global_values={};extruder_values={}
    for key,value in VALUES.items():
        field=schema[key]
        if field['type']=='enum':assert value in field['options']
        elif field['type']=='bool':assert type(value)==bool
        else:assert isinstance(value,(int,float)) and not isinstance(value,bool)
        (extruder_values if field.get('settable_per_extruder',True) else global_values)[key]=value
    with zipfile.ZipFile(PROFILE,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('hexquad_r5_quick_fit_global',original.serialize(global_values,False))
        archive.writestr('hexquad_r5_quick_fit_extruder_0',original.serialize(extruder_values,True))
    with zipfile.ZipFile(PROFILE) as archive:
        assert archive.testzip() is None
        merged={}
        for name in archive.namelist():
            p=configparser.ConfigParser(interpolation=None);p.read_string(archive.read(name).decode())
            assert p['general']['name']==NAME
            assert p['metadata']['quality_type']=='Elegoo_layer_020'
            merged.update(p['values'])
        assert merged=={k:str(v) for k,v in VALUES.items()}
    spec=importlib.util.spec_from_file_location('pack',DESIGN/'printing/pack_prints.py')
    pack=importlib.util.module_from_spec(spec);spec.loader.exec_module(pack)
    manifest=DESIGN/'cad/output/assembly_manifest.json'
    data=json.loads(manifest.read_text());byname={p['name']:p for p in data['coupons']}
    old=json.loads((DESIGN/'printing/plate_manifest.json').read_text())['plates'][0]
    assert sorted(sum(GROUPS.values(),[]))==sorted(p['name'] for p in old['parts'])
    plates=[]
    for name,names in GROUPS.items():
        placed=[];x=y=0;row_height=0;members=[]
        for item in names:
            entry=byname[item];src=DESIGN/'cad/output'/entry['stl']
            mesh=trimesh.load_mesh(src,process=True)
            assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
            if mesh.extents[0]<mesh.extents[1]:
                mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,(0,0,1)))
            mesh.apply_translation(-mesh.bounds[0])
            w,h=mesh.extents[:2]
            if x+w>190:x=0;y+=row_height+9;row_height=0
            mesh.apply_translation((x,y,0));x+=w+9;row_height=max(row_height,h)
            placed.append((item,mesh));members.append({'name':item,'source_stl':str(src),'source_sha256':sha(src)})
        whole=trimesh.util.concatenate([p[1] for p in placed]);shift=np.array([112.5,112.5,0])-np.array([*whole.bounds.mean(axis=0)[:2],0])
        for _,mesh in placed:mesh.apply_translation(shift)
        whole=trimesh.util.concatenate([p[1] for p in placed])
        assert whole.bounds[0,0]>5 and whole.bounds[0,1]>5
        assert whole.bounds[1,0]<220 and whole.bounds[1,1]<220
        whole.export(HERE/(name+'.stl'));pack.three_mf(HERE/(name+'.3mf'),placed)
        reloaded=trimesh.load(HERE/(name+'.3mf'))
        assert len(reloaded.geometry)==len(names)
        plates.append({'name':name,'part_count':len(names),'parts':members,
            'bounds_mm':whole.bounds.tolist(),'stl_sha256':sha(HERE/(name+'.stl')),
            'model_3mf_sha256':sha(HERE/(name+'.3mf'))})
    report={'status':'geometry_and_profile_checks_pass','source_manifest_sha256':sha(manifest),
        'profile':PROFILE.name,'profile_sha256':sha(PROFILE),'profile_settings':VALUES,
        'plates':plates,'all_original_15_specimens_preserved':True,
        'parts_modified':False,'layer_height_mm':.2,
        'purpose':'Shorter staged print jobs. Start with the servo case saddle and cap, then check the shaft alignment and horn fixtures.',
        'limits':['Physical quality and fit cannot be guaranteed without printing.',
                  'Smaller first job defers horn, phone and load specimens; it does not replace their tests.']}
    (HERE/'quick_fit_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'profile':PROFILE.name,'plates':[(p['name'],p['part_count']) for p in plates]}))


if __name__=='__main__':main()
