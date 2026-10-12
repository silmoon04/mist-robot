"""Bounded stance, rolling and supported-load checks with CAD inertials."""
import copy
import hashlib
import json
from model import ROOT
from run_sim import run_case
from load_test import trial


def main():
    output=ROOT/'proximal_cad_20260907'
    params=json.loads((output/'parameters_cad_inertials.json').read_text())
    snapshot=output/'runtime_snapshot'
    snapshot.mkdir(exist_ok=True)
    sources=['model.py','run_sim.py','load_test.py','run_proximal_cad_validation.py']
    hashes={}
    for name in sources:
        raw=(ROOT/name).read_bytes()
        (snapshot/name).write_bytes(raw)
        hashes[name]=hashlib.sha256(raw).hexdigest()
    reports=[]
    for case in ['stand','drive']:
        result=run_case(copy.deepcopy(params),case,output_root=output/'outputs')
        reports.append(result)
        print(json.dumps({key:result[key] for key in ['case','status','mass_kg','max_tilt_deg','max_servo_rms_nm','base_displacement_m']}),flush=True)
    load=trial(copy.deepcopy(params),2,3,1)
    (output/'load_three_contacts.json').write_text(json.dumps(load,indent=2))
    print(json.dumps({key:load[key] for key in ['status','force_n','hold_max_foot_error_m','hold_servo_rms_nm']}),flush=True)
    for name,expected in hashes.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            raise RuntimeError('Runtime source changed during the evaluation: '+name)
    summary=dict(status='completed_candidate_checks_not_hardware_release',reports=reports,
        load_test={key:value for key,value in load.items() if key not in ('history','parameters_used')},source_sha256=hashes)
    (output/'validation_summary.json').write_text(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
