"""Run bounded mass sensitivity, preserving the original generated URDF."""
from pathlib import Path
import copy
import json
from model import ROOT, build_urdf
from run_sim import run_case
from load_test import trial

out=ROOT/'cad_mass_20260907'
p=json.loads((out/'parameters_mass_only.json').read_text())
canonical=ROOT/'generated/mist_candidate.urdf'
old=canonical.read_bytes() if canonical.exists() else None
reports=[]
try:
    build_urdf(p,out/'mass_only_candidate.urdf')
    for case in ['stand','drive','crawl']:
        r=run_case(copy.deepcopy(p),case,output_root=out/'outputs')
        reports.append(r)
        print(json.dumps({k:r[k] for k in ['case','status','mass_kg','max_tilt_deg','joint_tracking_rms_deg','base_displacement_m']}),flush=True)
    loads=[]
    for ratio,contacts,factor in [(2,3,1),(3.5,3,1)]:
        r=trial(copy.deepcopy(p),ratio,contacts,factor)
        (out/f'load_hip{ratio:g}.json').write_text(json.dumps(r,indent=2))
        loads.append({k:v for k,v in r.items() if k not in ['history','parameters_used']})
        print(json.dumps({k:r[k] for k in ['hip_ratio','status','force_n','hold_max_foot_error_m','hold_servo_rms_nm']}),flush=True)
    (out/'sensitivity_summary.json').write_text(json.dumps(dict(reports=reports,load_tests=loads),indent=2))
finally:
    if old is not None:canonical.write_bytes(old)
