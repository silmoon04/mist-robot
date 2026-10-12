"""Pack only the three replacement pieces needed for M3x30 bridge screws."""
from pathlib import Path
import importlib.util,sys,json,gzip,hashlib,shutil,math
import trimesh,numpy as np
HERE=Path(__file__).resolve().parent
DESIGN=HERE.parent/'hexapod_phone_quad_r5_20260912'
THIRD=HERE.parent/'third_fit_joints_20260913'
sys.path.insert(0,str(DESIGN/'manufacturing/slicing_r5'))
from engine_runner import slice_one
from deposition_properties import parse_gcode

def main():
    entries=[]
    for name,file,xy in [('M3x30 replacement bridge','bridge_M3x30.stl',(82,90)),
                         ('8mm outer spacer A','bridge_spacer_8mm.stl',(108,100)),
                         ('8mm outer spacer B','bridge_spacer_8mm.stl',(126,100))]:
        m=trimesh.load_mesh(HERE/file);assert m.is_watertight and m.is_winding_consistent and len(m.split())==1
        mask=(m.face_normals[:,2]<-math.cos(math.pi/4)-1e-5)&(m.triangles[:,:,2].max(axis=1)>.001)
        assert m.area_faces[mask].sum()<.001,(name,m.area_faces[mask].sum())
        m.apply_translation(-m.bounds[0]);m.apply_translation((*xy,0));entries.append((name,m))
    mesh=trimesh.util.concatenate([m for _,m in entries]);stl=HERE/'M3x30_Bridge_Adapter_Plate.stl';mesh.export(stl)
    spec=importlib.util.spec_from_file_location('pack',DESIGN/'printing/pack_prints.py');pack=importlib.util.module_from_spec(spec);spec.loader.exec_module(pack)
    pack.three_mf(HERE/'M3x30_Bridge_Adapter_Plate.3mf',entries)
    assert len(trimesh.load(HERE/'M3x30_Bridge_Adapter_Plate.3mf').geometry)==3
    old=json.loads((THIRD/'third_fit_validation.json').read_text());values=old['profile']['settings']
    shutil.copy2(THIRD/old['profile']['file'],HERE/old['profile']['file'])
    result=slice_one(stl,HERE/'analysis','m30_adapter',values)
    raw=Path(result['raw_temporary_path']);text=raw.read_text();p=parse_gcode(text,result['gcode_to_source_transform'])
    assert p['properties']['support']['mass_g']==0 and result['motion_inside_build_envelope']
    inert='; ANALYSIS ONLY. DO NOT PRINT.\n'+'\n'.join(s if not s.strip() or s.lstrip().startswith(';') else '; DISABLED| '+s for s in text.splitlines())
    (HERE/'analysis/m30_adapter.ANALYSIS_ONLY.gcode.gz').write_bytes(gzip.compress(inert.encode()));raw.unlink()
    report={'status':'pass','parts':3,'same_third_fit_profile':True,'profile_sha256':hashlib.sha256((HERE/old['profile']['file']).read_bytes()).hexdigest(),
        'estimated_minutes':result['estimated_time_seconds']/60,'model_g':p['properties']['model']['mass_g'],
        'support_g':p['properties']['support']['mass_g'],'bed_fit':True,
        'scope':'Replacement bridge and two spacers only. Existing printed cheeks remain unchanged; physical fastener fit pending.'}
    (HERE/'adapter_print_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

if __name__=='__main__':main()
