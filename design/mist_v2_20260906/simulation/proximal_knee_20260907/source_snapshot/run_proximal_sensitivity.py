"""Same-mass reaction-frame comparison; not a fitted CAD or stair release."""
from pathlib import Path
import copy
import hashlib
import json
from model import ROOT,build_urdf,total_mass
from run_sim import run_case
from load_test import trial


def main():
    out=ROOT/'proximal_knee_20260907'
    out.mkdir(exist_ok=True)
    source=ROOT/'cad_mass_20260907/parameters_mass_only.json'
    p=json.loads(source.read_text())
    p['status']='same_mass_proximal_knee_reaction_frame_sensitivity_not_fitted_CAD'
    p['mass']['knee_servo_com_m']=[0,0,-.04]
    p['mass']['knee_servo_box_m']=[.02473,.035,.04523]
    p['transmission'].update(topology='proximal_femur_relative_knee',knee_motor_mount='femur',
        motor_coordinate_equation='s=[ry*q1,rh*q2,rk*q3]; knee motor housing moves with femur; other hardware masses held fixed for sensitivity')
    p['mass']['provenance']+=' The same physical 55 g knee servo moves from yaw to 40 mm down the femur. No hypothetical mass saving is applied. New mount mass and exact collision geometry are absent.'
    (out/'parameters_same_mass.json').write_text(json.dumps(p,indent=2))
    canonical=ROOT/'generated/mist_candidate.urdf'
    old=canonical.read_bytes() if canonical.exists() else None
    reports=[]
    loads=[]
    try:
        build_urdf(p,out/'same_mass_candidate.urdf')
        for case in ['stand','drive','crawl','step_ascent','step_descent']:
            result=run_case(copy.deepcopy(p),case,output_root=out/'outputs_same_mass')
            reports.append(result)
            print(json.dumps({k:result[k] for k in ['case','status','mass_kg','max_tilt_deg','joint_tracking_rms_deg','base_displacement_m']}),flush=True)
        for contacts,factor in [(3,1),(2,1.5)]:
            result=trial(copy.deepcopy(p),2,contacts,factor)
            (out/f'load_{contacts}contacts_{factor:g}factor.json').write_text(json.dumps(result,indent=2))
            loads.append({k:v for k,v in result.items() if k not in ['history','parameters_used']})
            print(json.dumps({k:result[k] for k in ['hip_ratio','status','force_n','hold_max_foot_error_m','hold_servo_rms_nm']}),flush=True)
        (out/'same_mass_summary.json').write_text(json.dumps(dict(
            status='sensitivity_not_selected_mechanism',source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            source_hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['model.py','run_sim.py','load_test.py','run_proximal_sensitivity.py']},
            mass_kg=total_mass(p),reports=reports,load_tests=loads),indent=2))
    finally:
        if old is not None:
            canonical.write_bytes(old)


if __name__=='__main__':
    main()
