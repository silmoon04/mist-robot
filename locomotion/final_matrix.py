"""Parallel, content-bound final simulation tests; never selects a checkpoint."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import json
import os
from pathlib import Path
import time
import numpy as np
try:
    from .provenance import source_hashes,check_sources,digest,identity,verify_checkpoint
    from .sensitivity import plan_cases,run_case
    from .sensor_sim import SimulatedIMU
    from .acceptance import CRITERIA
except ImportError:
    from provenance import source_hashes,check_sources,digest,identity,verify_checkpoint
    from sensitivity import plan_cases,run_case
    from sensor_sim import SimulatedIMU
    from acceptance import CRITERIA


def worker(job):
    case,steps,checkpoint,algorithm,frozen=job
    check_sources(frozen)
    policy=None
    if checkpoint:
        import torch
        torch.set_num_threads(1)
        from stable_baselines3 import PPO,SAC
        verify_checkpoint(checkpoint,algorithm)
        policy=(PPO if algorithm=='ppo' else SAC).load(checkpoint,device='cpu')
    started=time.perf_counter()
    row=run_case(case,steps,policy)
    row['wall_s']=time.perf_counter()-started
    return row


def json_native(value):
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,np.ndarray):return value.tolist()
    raise TypeError(f'Unsupported final-test receipt type: {type(value).__name__}')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checkpoint',type=Path)
    ap.add_argument('--algo',choices=['ppo','sac'],default='ppo')
    ap.add_argument('--workers',type=int,default=4)
    ap.add_argument('--steps',type=int,default=960)
    ap.add_argument('--suite',choices=['core','all'],default='core')
    ap.add_argument('--sensor',choices=['mpu6050','phone','none'])
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    if args.workers<1 or args.steps<960:ap.error('positive workers and at least 960 steps required')
    if args.output.exists():ap.error('final-test output already exists; choose a new path')
    os.environ.setdefault('OMP_NUM_THREADS','1');os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
    frozen=source_hashes()
    cases=plan_cases()
    # Every case identity is moved into an untouched seed stream. Validation
    # uses its own >=1,000,000 range; development sensitivity starts9,100,000.
    for case in cases:
        case['seed']=6_000_000_000+int(identity(case)[:12],16)
    if args.suite=='core':
        cases=[case for case in cases if case['case_id'].startswith(('flat-','low_friction-','slope-','rough-'))
               and case['command_name'] in ('forward','backward','left','right','stop')]
    if args.sensor:cases=[case for case in cases if case['env_kwargs']['sensor_mode']==args.sensor]
    checkpoint=None;policy_record=None
    if args.checkpoint:
        checkpoint=args.checkpoint.resolve()
        policy_record=verify_checkpoint(checkpoint,args.algo)
    resolved=[]
    for case in cases:
        mode=case['env_kwargs']['sensor_mode']
        profile=SimulatedIMU(mode,case['env_kwargs'].get('sensor_profile')).profile
        declared=policy_record['envelope']['experiment']['sensor'] if policy_record else None
        resolved.append({**case,'steps':args.steps,'resolved_sensor_profile':profile,
                         'sensor_distribution_shift':bool(declared and (declared['mode']!=mode or declared['profile']!=profile))})
    manifest={'schema':1,'purpose':'untouched final simulation test; no checkpoint selection',
              'controller':args.algo if checkpoint else 'IK with model position bias',
              'checkpoint':str(checkpoint) if checkpoint else None,
              'checkpoint_sha256':digest(checkpoint) if checkpoint else None,
              'checkpoint_envelope_sha256':policy_record['envelope_sha256'] if policy_record else None,
              'wrapper_sha256':digest(__file__),'source_hashes':frozen,'criteria':CRITERIA,
              'steps':args.steps,'ordered_resolved_cases':resolved}
    manifest['suite_sha256']=identity({'criteria':CRITERIA,'cases':resolved,'steps':args.steps})
    started=time.perf_counter();results={}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(worker,(case,args.steps,checkpoint,args.algo,frozen)):case for case in cases}
        for future in as_completed(futures):
            case=futures[future]
            try:row=future.result()
            except Exception as exc:row={**case,'passed':False,'execution_error':str(exc)}
            results[case['case_id']]=row
            print(f"{len(results)}/{len(cases)} {case['case_id']} {'PASS' if row['passed'] else 'FAIL'}",flush=True)
    check_sources(frozen)
    if digest(__file__)!=manifest['wrapper_sha256']:raise RuntimeError('final-test wrapper changed during execution')
    if checkpoint:
        if digest(checkpoint)!=manifest['checkpoint_sha256']:raise RuntimeError('checkpoint changed during final test')
        verify_checkpoint(checkpoint,args.algo)
    manifest['wall_s']=time.perf_counter()-started
    manifest['results']=[results[case['case_id']] for case in cases]
    manifest['passed_cases']=sum(row['passed'] for row in manifest['results'])
    manifest['total_cases']=len(cases)
    manifest['status']='simulation screening only; physical transfer unvalidated'
    args.output.write_text(json.dumps(manifest,indent=2,allow_nan=False,default=json_native)+'\n')
    print(json.dumps({key:manifest[key] for key in ('passed_cases','total_cases','wall_s','suite_sha256')}),flush=True)


if __name__=='__main__':main()
