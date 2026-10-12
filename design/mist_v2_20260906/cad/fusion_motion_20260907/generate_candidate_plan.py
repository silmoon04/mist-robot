"""Generate an offline motion plan against a frozen snapshot of current inputs."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import sys
import traceback

HERE=Path(__file__).resolve().parent
CAD=HERE.parent
ROOT=CAD.parent
PROXIMAL=CAD/'leg_proximal_20260907'
for directory in (CAD,PROXIMAL,HERE):
    if str(directory) not in sys.path:sys.path.insert(0,str(directory))


def load(name,path,raw):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module


def run():
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=HERE/'integration_runs'/stamp
    output.mkdir(parents=True)
    files=[CAD/'leg_gears.py',CAD/'leg_native.py',CAD/'body_native.py',PROXIMAL/'retention_recipe.py',
           PROXIMAL/'proximal_leg.py',HERE/'motion.py',HERE/'reviewed_groups.py',PROXIMAL/'native_replay.py',
           PROXIMAL/'fusion_run.py',ROOT/'simulation/design_parameters_20260907.json']
    raw={p:p.read_bytes() for p in files}
    report=dict(status='started',native_execution=False,native_motion_verified=False,errors=[],
                input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(b).hexdigest() for p,b in raw.items()})
    for p,b in raw.items():
        dest=output/'source_snapshot'/p.relative_to(ROOT)
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
    try:
        modules={}
        for name,path in [('leg_gears',files[0]),('leg_native',files[1]),('body_native',files[2]),
                          ('retention_recipe',files[3]),('proximal_leg',files[4]),('motion',files[5]),('reviewed_groups',files[6])]:
            modules[name]=load(name,path,raw[path])
        params=json.loads(raw[files[-1]])
        params['status']='offline_motion_plan_for_native_proximal_candidate'
        params['transmission'].update(topology='proximal_femur_relative_knee',knee_motor_mount='femur',
            motor_coordinate_equation='s=[2*yaw,2*hip,2*knee]; normalized actuator directions require commissioning')
        specs=[modules['proximal_leg'].leg_spec(params,name) for name in params['geometry']['leg_names']]
        body=modules['body_native'].body_spec(params)
        params['mass']['knee_servo_com_m']=[v/1000 for v in specs[0]['knee_servo_com_femur_mm']]
        overrides=modules['reviewed_groups'].proximal_group_overrides(specs)
        plan=modules['motion'].build_motion_plan(params,body,specs,group_overrides=overrides)
        for p,b in raw.items():
            if p.read_bytes()!=b:raise RuntimeError('Source changed while generating plan: '+str(p))
        outputs={'parameters.json':params,'leg_specs.json':specs,'body_spec.json':body,
                 'group_overrides.json':overrides,'motion_plan.json':plan,
                 'assignment_audit.json':modules['reviewed_groups'].assignment_audit(specs,overrides)}
        for name,value in outputs.items():
            (output/name).write_text(json.dumps(value,indent=2,allow_nan=False))
        report.update(status='offline_plan_validated',part_count=len(plan['parts']),
                      structural_revolutes=len(plan['joints']),rigid_group_count=len(plan['groups']),
                      rotor_fixed_phase_attachment_count=len(plan['fixed_phase_rotor_attachments']),
                      explicit_override_count=len(overrides),plan_sha256=plan['plan_sha256'],
                      group_sizes={name:len(parts) for name,parts in plan['groups'].items()})
        (HERE/'current_integration.json').write_text(json.dumps(dict(directory=str(output),report='integration_report.json',
            plan='motion_plan.json',overrides='group_overrides.json',native_execution=False),indent=2))
    except Exception:
        report['status']='offline_plan_failed';report['errors'].append(traceback.format_exc())
    (output/'integration_report.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps(report,indent=2))
    if report['errors']:raise RuntimeError('Plan failed; see '+str(output/'integration_report.json'))
    return output


if __name__=='__main__':run()
