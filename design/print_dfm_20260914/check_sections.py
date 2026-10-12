"""Screen selected net sections with explicitly assumed printed PLA allowables."""
from pathlib import Path
import sys,json,importlib.util
import numpy as np
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'
spec=importlib.util.spec_from_file_location('section_math',ROOT.parent/'hexapod_phone_quad_r5_20260912/manufacturing/strength/reassess_r5.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s);s.MESH=OUT/'assembly_mesh'

def main():
    rows=[]
    specs=[('coxa upper arm','coxa_upper_and_hip_saddle',0,20,None,0,20.5,12),
        ('coxa lower arm','coxa_lower_auxiliary_arm',0,20,None,0,20.5,12),
        ('post through lower nut','coxa_upper_and_hip_saddle',2,-40,[32,-12,45.1,12],1,140,12),
        ('post through upper nut','coxa_upper_and_hip_saddle',2,-36,[32,-12,45.1,12],1,140,12),
        ('femur bridge at nut slot','femur_main_and_knee_saddle',1,0,[57.99,13.49,72.01,27.51],0,90,4),
        ('tibia bridge at nut slots','tibia_curved_main_and_foot',1,0,[31.99,-7.01,48.01,7.01],0,75,4),
        ('tibia shank','tibia_curved_main_and_foot',0,80,None,0,25,12),
        ('ribbed bench rails','bench_mounting_plate',0,-65,None,0,345,12)]
    for label,name,axis,pos,region,zi,lever,allowable in specs:
        section=s.section(name,axis,pos,region);z=section['section_modulus_transverse_mm3'][zi]
        rows.append({'location':label,'section':section,'assumed_allowable_MPa':allowable,
            'screening_moment_arm_mm':lever,'stress_multiplier':4,
            'stress_MPa_per_1N_equivalent_tip_force':4*lever/z,
            'margin_at_1N_equivalent_tip_force':allowable/(4*lever/z),
            'margin_at_5N_equivalent_tip_force':allowable/(20*lever/z)})
    ring=s.section('femur_auxiliary_cheek',1,-20,[-10,-10,10,10]);polar=sum(ring['I_transverse_mm4'][:2])
    result={'rows':rows,'auxiliary_ring':{'section':ring,'polar_second_moment_mm4':polar,'assumed_shear_allowable_MPa':3,'stress_multiplier':4,'estimated_shear_MPa_at_1Nm':4*1000*9.9/polar},'minimum_margin_1N':min(r['margin_at_1N_equivalent_tip_force'] for r in rows),
        'minimum_margin_5N':min(r['margin_at_5N_equivalent_tip_force'] for r in rows),
        'method':'Net geometry section moduli with simple beam bending. Moment arms are conservative screening choices, not a solved load distribution. Multiplier 4 combines 2x stress concentration and 50 percent effective section.',
        'limits':'12 MPa in-plane and 4 MPa layer-sensitive allowables are unmeasured design assumptions. This screen does not establish part strength or capture screw preload, fatigue, torsion, joint compliance or impact. Begin with unloaded restrained articulation only.'}
    (OUT/'section_screen.json').write_text(json.dumps(result,indent=2));print(result)

if __name__=='__main__':main()
