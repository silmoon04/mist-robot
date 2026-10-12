"""Content-bound experiment contracts shared by every policy consumer."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CONTRACT = {'version': 2, 'observation': '47: body-down gravity3, body gyro3 rad/s, joint offsets12 rad, joint velocity12 rad/s, command3, previous residual12, phase sin/cos2',
            'action': '12 clipped residuals in [-1,1], scaled .10 rad; R7 joint order',
            'sensor': 'measurement age; bounded hold then latched episode stop; none explicit open-loop; reset required'}
REQUIRED = ('train.py','evaluate.py','sensitivity.py','mist_env.py','model.py','servo.py','gait.py','kinematics.py','sensor_sim.py','hardware/sensors.py','hardware/__init__.py','provenance.py','acceptance.py','config.json','requirements.lock.txt','validation_cases.json','profiles/r7_direct.json','design_profile.py','sim_remote.py','training_queue.json','machine_profiles.json','scripts/benchmark.py','scripts/run_job.py','scripts/setup_cpu.sh')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def identity(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def source_hashes():
    paths = [HERE / name for name in REQUIRED]
    cfg=json.loads((HERE/'config.json').read_text())
    for key in ('leg_urdf','leg_manifest','hub_report','hub_cad','component_inventory','mass_budget','phone_pose'):
        paths.append(REPO/cfg['sources'][key])
    urdf=REPO/cfg['sources']['leg_urdf']
    paths.extend(urdf.parent / m.get('filename') for m in ET.parse(urdf).iter('mesh'))
    manifest=json.loads((REPO/cfg['sources']['leg_manifest']).read_text())
    paths.extend(urdf.parent / part['assembly_stl'] for part in manifest['parts'])
    return {str(p.resolve().relative_to(REPO)):digest(p) for p in sorted(set(paths))}

def check_sources(expected):
    if source_hashes()!=expected:
        raise RuntimeError('Experiment source or CAD changed; start a new experiment')

def envelope(experiment=None):
    return {'schema':1,'sources':source_hashes(),'contract':CONTRACT,'experiment':experiment or {}}

def checkpoint_path(path):
    path=Path(path)
    return path if path.suffix=='.zip' else Path(str(path)+'.zip')

def bind_checkpoint(path, env, algorithm, status, replay=None, continuation_seed=None):
    path=checkpoint_path(path)
    check_sources(env['sources'])
    record={'envelope':env,'envelope_sha256':identity(env),'algorithm':algorithm,'status':status,
            'checkpoint_sha256':digest(path),'replay_sha256':digest(replay) if replay else None,
            'continuation_seed':continuation_seed,'hardware_qualified':False}
    sidecar=path.with_suffix('.provenance.json')
    sidecar.write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
    check_sources(env['sources'])
    return record

def verify_checkpoint(path, algorithm=None, expected_experiment=None, replay=None, sensor_mode=None, sensor_profile=None):
    path=checkpoint_path(path)
    record=json.loads(path.with_suffix('.provenance.json').read_text())
    env=record['envelope']
    if identity(env)!=record['envelope_sha256'] or digest(path)!=record['checkpoint_sha256']:
        raise ValueError('checkpoint or envelope content hash mismatch')
    check_sources(env['sources'])
    if env['contract']!=CONTRACT or (algorithm is not None and algorithm!=record['algorithm']):
        raise ValueError('policy contract or algorithm mismatch')
    if expected_experiment is not None and env['experiment']!=expected_experiment:
        raise ValueError('resume experiment mismatch; use a new explicit transfer experiment')
    sensor=env['experiment'].get('sensor',{})
    if sensor_mode is not None and (sensor_mode!=sensor.get('mode') or sensor_profile!=sensor.get('profile')):
        raise ValueError('policy sensor contract mismatch')
    if replay is not None and (not record['replay_sha256'] or digest(replay)!=record['replay_sha256']):
        raise ValueError('matching SAC replay artifact required')
    return record
