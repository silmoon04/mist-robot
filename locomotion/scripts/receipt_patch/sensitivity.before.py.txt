"""Reproducible simulation screening. Passing does not qualify physical hardware."""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
try:
    from .provenance import source_hashes,check_sources,verify_checkpoint
    from .acceptance import COMMANDS, CRITERIA as DEFAULT_CRITERIA, score, command_at
except ImportError:
    from provenance import source_hashes,check_sources,verify_checkpoint
    from acceptance import COMMANDS, CRITERIA as DEFAULT_CRITERIA, score, command_at

def plan_cases(spec=None):
    spec = spec or json.loads((HERE / 'validation_cases.json').read_text())
    cases = []
    for terrain, phone, direction, sensor in itertools.product(spec['terrains'], (False, True), COMMANDS, spec['sensors']):
        if sensor == 'phone' and not phone:
            continue
        name = f"{terrain}-{direction}-{'phone' if phone else 'bare'}-{sensor}"
        seed = spec['seed_base'] + int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)
        cases.append({'case_id': name, 'command_name':direction, 'seed': seed, 'status': 'ready',
                      'env_kwargs': {'terrain': terrain, 'command': list(COMMANDS[direction]),
                                     'payload': spec['phone_mass_kg'] if phone else 0.,
                                     'sensor_mode': sensor, 'randomize': True, 'pushes': False}})
    # Held-out corners run all commands on flat terrain with the nominal phone and MPU.
    for variation, direction in itertools.product(spec['held_out_variations'], COMMANDS):
        name = 'held-out-' + variation['name'] + '-' + direction
        cases.append({'case_id': name, 'command_name':direction, 'seed': spec['seed_base'] + int(hashlib.sha256(name.encode()).hexdigest()[:8],16),
                      'status': 'ready', 'env_kwargs': {'terrain': 'flat', 'command': list(COMMANDS[direction]),
                      'payload': spec['phone_mass_kg'], 'sensor_mode': 'mpu6050', 'randomize': False,
                      'pushes': False, 'scenario': variation['overrides']}})
    for name, override in [('delay',{'transport_delay_s':.08}),('dropout',{'dropout_probability':.15}),('bias',{'gyro_bias_rad_s':[.02,-.02,.01]})]:
        cases.append({'case_id':'sensor-'+name,'command_name':'forward','seed':spec['seed_base']+int(hashlib.sha256(name.encode()).hexdigest()[:8],16),'status':'ready','env_kwargs':{'terrain':'flat','command':list(COMMANDS['forward']),'payload':.155,'sensor_mode':'mpu6050','sensor_profile':override,'randomize':False,'pushes':False}})
    for mass in (.08,.25):
        cases.append({'case_id':f'phone-mass-{mass}','command_name':'forward','seed':spec['seed_base']+int(mass*100000),'status':'ready','env_kwargs':{'terrain':'flat','command':list(COMMANDS['forward']),'payload':mass,'sensor_mode':'mpu6050','randomize':False,'pushes':False}})
    return cases


def score_episode(initial, rows, command, criteria=None):
    if criteria is not None and criteria != DEFAULT_CRITERIA:
        raise ValueError('acceptance thresholds are versioned; arbitrary overrides cannot qualify')
    return score(initial,rows,command)


def run_case(case, steps=960, policy=None, criteria=None):
    if case['status'] != 'ready':
        return dict(case)
    import numpy as np
    import pybullet as p
    try:
        from .mist_env import MistEnv
    except ImportError:
        from mist_env import MistEnv
    frozen=source_hashes()
    env = MistEnv(**case['env_kwargs'], max_steps=steps)
    try:
        obs, initial = env.reset(seed=case['seed'])
        rows = []
        for step in range(steps):
            env.command=np.asarray(command_at(case.get("command_name"),case["env_kwargs"]["command"],step,steps))
            action = np.zeros(12) if policy is None else policy.predict(obs,deterministic=True)[0]
            obs, _, terminated, truncated, info = env.step(action)
            rows.append(info)
            if terminated or truncated:
                break
        result = score_episode(initial,rows,case['env_kwargs']['command'],criteria)
        check_sources(frozen)
        result['checks']['complete']=len(rows)==steps
        result['passed']=all(result['checks'].values())
        return {**case, **result, 'effective_assumptions': {'config': env.cfg, 'initial_info': initial},
                'samples': len(rows), 'source_hashes': frozen}
    finally:
        env.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',action='store_true',help='Execute after the reviewed source freeze')
    ap.add_argument('--case-id',action='append')
    ap.add_argument('--steps',type=int,default=960)
    ap.add_argument('--checkpoint',type=Path)
    ap.add_argument('--algo',choices=['ppo','sac'],default='ppo')
    ap.add_argument('--criteria',type=Path,help='JSON object of screening thresholds')
    ap.add_argument('--output',type=Path,required=True)
    args = ap.parse_args()
    if args.steps < 1:
        ap.error('--steps must be positive')
    cases = plan_cases()
    if args.case_id:
        if set(args.case_id)-{c['case_id'] for c in cases}:
            ap.error('Unknown case ID')
        cases = [c for c in cases if c['case_id'] in args.case_id]
    policy = None
    if args.run and args.checkpoint:
        from stable_baselines3 import PPO,SAC
        record=verify_checkpoint(args.checkpoint,args.algo)
        sensor=record['envelope']['experiment']['sensor']
        for case in cases:
            if case['env_kwargs']['sensor_mode']!=sensor['mode']: raise ValueError('policy sensor mismatch in sensitivity case')
            case['env_kwargs']['sensor_profile']=sensor['profile']
        policy = (PPO if args.algo == 'ppo' else SAC).load(args.checkpoint,device='cpu')
    criteria = json.loads(args.criteria.read_text()) if args.criteria else DEFAULT_CRITERIA
    result = {'scope': 'Software simulation screening; physical transfer remains unvalidated.',
              'controller': args.algo if args.checkpoint else 'baseline_crawl', 'criteria': criteria,
              'source_hashes': source_hashes(), 'checkpoint_sha256': hashlib.sha256(args.checkpoint.read_bytes()).hexdigest() if args.checkpoint else None,
              'cases': [run_case(c,args.steps,policy,criteria) for c in cases] if args.run else cases}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    if args.run and any(c.get('passed') is not True for c in result['cases']):
        raise SystemExit(1)

if __name__ == '__main__':
    main()
