"""Held-out locomotion matrix; exit nonzero when requested acceptance fails."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time
import numpy as np
try:
    from .mist_env import MistEnv
except ImportError:
    from mist_env import MistEnv

try:
    from .acceptance import COMMANDS, CRITERIA, VERSION, score, command_at
    from .provenance import verify_checkpoint, source_hashes, check_sources, identity
    from .sensor_sim import SimulatedIMU
except ImportError:
    from acceptance import COMMANDS, CRITERIA, VERSION, score, command_at
    from provenance import verify_checkpoint, source_hashes, check_sources, identity
    from sensor_sim import SimulatedIMU

def episode(command, terrain, payload, seed, steps=960, policy=None, randomize=True, video=None, sensor_mode="mpu6050", sensor_profile=None, command_name=None):
    frozen=source_hashes()
    env = MistEnv(command=command,terrain=terrain,payload=payload,randomize=randomize,max_steps=steps,sensor_mode=sensor_mode,sensor_profile=sensor_profile)
    obs,initial = env.reset(seed=seed)
    start = np.asarray(initial['position'])
    rows,frames = [],[]
    beginning = time.perf_counter()
    try:
        for i in range(steps):
            env.command=np.asarray(command_at(command_name,command,i,steps))
            action = np.zeros(12) if policy is None else policy.predict(obs,deterministic=True)[0]
            obs,reward,terminated,truncated,info = env.step(action)
            rows.append(info)
            if video and i%5==0:
                frames.append(env.render())
            if terminated or truncated:
                break
        if video and frames:
            import imageio.v2 as imageio
            imageio.mimsave(video,frames,fps=9.6)
        displacement = np.asarray(rows[-1]['position'])-start
        elapsed = rows[-1]['time_s']
        target = np.asarray(command)[:2]
        velocity = np.asarray([row['body_velocity'][:2] for row in rows])
        error = np.linalg.norm(velocity-target,axis=1)
        direction = target/np.linalg.norm(target) if np.linalg.norm(target)>0 else np.zeros(2)
        progress = float(displacement[:2]@direction)
        fell = rows[-1]['fell']
        acceptance=score(initial,rows,command,steps)
        passed=acceptance['passed']
        check_sources(frozen)
        return {'seed':seed,'terrain':terrain,'payload_kg':payload,'command':list(command),
                'acceptance':acceptance,'steps':len(rows),'duration_s':elapsed,'fell':fell,'passed':passed,
                'displacement_m':displacement.tolist(),'direction_progress_m':progress,
                'velocity_rmse_m_s':float(np.sqrt(np.mean(error**2))),
                'peak_tilt_deg':float(np.degrees(max(np.max(np.abs(row['rpy'][:2])) for row in rows))),
                'yaw_drift_deg':float(np.degrees(np.unwrap([initial['rpy'][2]]+[r['rpy'][2] for r in rows])[-1]-initial['rpy'][2])),
                'tracking_error_rad':rows[-1]['tracking_error_rad'],
                'ik_rejections':rows[-1]['ik_rejections'],
                'torque_saturation_fraction':rows[-1]['torque_saturation_fraction'],
                'wall_s':time.perf_counter()-beginning,'randomization':initial['randomization']}
    finally:
        env.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sensor-mode',choices=['mpu6050','phone','none'],default='mpu6050')
    ap.add_argument('--sensor-profile',type=json.loads)
    ap.add_argument('--policy',type=Path)
    ap.add_argument('--algo',choices=['ppo','sac'],default='ppo')
    ap.add_argument('--output',type=Path,default=Path('runs/evaluation.json'))
    ap.add_argument('--steps',type=int,default=960)
    ap.add_argument('--seeds',type=int,default=3)
    ap.add_argument('--seed-base',type=int,default=2000000)
    ap.add_argument('--terrains',nargs='+',default=['flat','low_friction','slope','rough'])
    ap.add_argument('--commands',nargs='+',choices=list(COMMANDS),default=list(COMMANDS))
    ap.add_argument('--nominal',action='store_true')
    ap.add_argument('--require-pass',action='store_true')
    ap.add_argument('--video',type=Path)
    args = ap.parse_args()
    if args.output.exists(): ap.error("final test output already exists; preserve prior evidence")
    if len(args.terrains)*2*len(args.commands)*args.seeds >= 100000: ap.error("test suite exceeds reserved seed block")
    if args.steps<1 or args.seeds<1:
        ap.error('--steps and --seeds must be positive')
    if args.seed_base != 2000000: ap.error('final test owns seed base 2000000')
    sensor=SimulatedIMU(args.sensor_mode,args.sensor_profile)
    args.sensor_profile=sensor.profile if args.sensor_mode!='none' else None
    frozen=source_hashes()
    policy = None
    if args.policy:
        verify_checkpoint(args.policy,args.algo,sensor_mode=args.sensor_mode,sensor_profile=args.sensor_profile)
        from stable_baselines3 import PPO,SAC
        policy = (PPO if args.algo=='ppo' else SAC).load(args.policy,device='cpu')
    result = {'controller':'ik_crawl' if policy is None else args.algo,'policy':str(args.policy),
              'status':'simulation screening; real transfer unvalidated',
              'criteria':CRITERIA,'acceptance_version':VERSION,'source_hashes':frozen,
              'suite_role':'untouched_final_test_not_for_selection',
              'episodes':[]}
    for terrain in args.terrains:
        for payload in ((.155,) if args.sensor_mode=='phone' else (0.,.155)):
            for name in args.commands:
                for j in range(args.seeds):
                    row = episode(COMMANDS[name],terrain,payload,args.seed_base+len(result['episodes']),args.steps,policy,
                                  not args.nominal,args.video if not result['episodes'] else None,args.sensor_mode,args.sensor_profile,name)
                    row['direction'] = name
                    result['episodes'].append(row)
                    print(name,terrain,payload,'PASS' if row['passed'] else 'FAIL',round(row['direction_progress_m'],4),flush=True)
    check_sources(frozen)
    result['suite_sha256']=identity([{k:r[k] for k in ('seed','terrain','payload_kg','command','direction')} for r in result['episodes']])
    result['pass_rate'] = float(np.mean([r['passed'] for r in result['episodes']]))
    result['fall_rate'] = float(np.mean([r['fell'] for r in result['episodes']]))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    if args.require_pass and result['pass_rate']<1.:
        raise SystemExit(1)


if __name__=='__main__':
    main()
