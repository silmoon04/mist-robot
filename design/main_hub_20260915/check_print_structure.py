"""Mesh/manufacturing checks and limited beam-section strength screening."""
from pathlib import Path
import importlib.util,json,hashlib
import numpy as np,trimesh
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'
spec=importlib.util.spec_from_file_location('sections',ROOT.parent/'hexapod_phone_quad_r5_20260912/manufacturing/strength/reassess_r5.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s);s.MESH=OUT

def main():
    mesh=trimesh.load_mesh(OUT/'Main_Hub_4Leg.stl');assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
    downside=(mesh.face_normals[:,2]<-.707)&(mesh.triangles[:,:,2].min(axis=1)>.05)
    area=float(mesh.area_faces[downside].sum());assert area<.01
    rows=[]
    for axis,position in [(0,0.01),(0,20),(0,40),(1,0.01),(1,20),(1,40)]:
        section=s.section('Main_Hub_4Leg',axis,position);z=section['section_modulus_transverse_mm3'][0]
        # Comparison screen only: 1Nm plus 2x concentration and 50% section.
        stress=4*1000/z
        rows.append({'section':section,'screening_moment_Nm':1,'stress_multiplier':4,'estimated_bending_MPa':stress,'assumed_PLA_allowable_MPa':12,'margin':12/stress})
    result={'status':'mesh and support-free geometry checks pass','stl_sha256':hashlib.sha256((OUT/'Main_Hub_4Leg.stl').read_bytes()).hexdigest(),
        'watertight':True,'winding_consistent':True,'downward_overhang_area_above_bed_mm2':area,'beam_screen':rows,
        'limits':'Selected gross mesh sections and assumed12MPa printed PLA allowable. This is not FEA or proof of local tab strength, fatigue, bolt preload, impacts or complete loaded robot performance. First hub is an assembly and restrained-load-test article.'}
    (OUT/'Print_Structure_Check.json').write_text(json.dumps(result,indent=2));print('No-support area',area,'margins',[r['margin'] for r in rows])

if __name__=='__main__':main()
