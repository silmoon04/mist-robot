"""Restrained single-leg load and tracking experiment, without hardware I/O."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pybullet as p
try:
    from .model import export_models, NEUTRAL, load_config
    from .servo import ServoBank
except ImportError:
    from model import export_models, NEUTRAL, load_config
    from servo import ServoBank


def run(load_kg, torque_cap=.588, duration=6.):
    cid=p.connect(p.DIRECT)
    try:
        model=export_models()['single_leg']
        p.setGravity(0,0,-9.81,physicsClientId=cid)
        dt=1/load_config()['simulation']['physics_hz']
        p.setTimeStep(dt,physicsClientId=cid)
        robot=p.loadURDF(str(model),useFixedBase=True,flags=p.URDF_USE_INERTIA_FROM_FILE,physicsClientId=cid)
        moving=[i for i in range(p.getNumJoints(robot,physicsClientId=cid)) if p.getJointInfo(robot,i,physicsClientId=cid)[2]==p.JOINT_REVOLUTE]
        toe=[i for i in range(p.getNumJoints(robot,physicsClientId=cid)) if p.getJointInfo(robot,i,physicsClientId=cid)[12].decode().endswith('toe')][0]
        p.setJointMotorControlArray(robot,moving,p.VELOCITY_CONTROL,forces=[0]*3,physicsClientId=cid)
        for i,q in zip(moving,NEUTRAL):p.resetJointState(robot,i,q,physicsClientId=cid)
        servos=ServoBank(np.tile(NEUTRAL,4),np.random.default_rng(0),False,torque_cap,dt)
        errors,saturations,angles=[],[],[]
        for step in range(round(duration/dt)):
            t=step*dt
            desired=NEUTRAL+np.radians([10*np.sin(t*1.5),5*np.sin(t*1.5),8*np.sin(t*1.5)])*min(1,t)
            state=p.getJointStates(robot,moving,physicsClientId=cid)
            q=np.array([s[0] for s in state]);qd=np.array([s[1] for s in state])
            tau=servos.advance(np.tile(desired,4),np.tile(q,4),np.tile(qd,4))[:3]
            p.setJointMotorControlArray(robot,moving,p.TORQUE_CONTROL,forces=tau.tolist(),physicsClientId=cid)
            toe_pos=p.getLinkState(robot,toe,computeForwardKinematics=True,physicsClientId=cid)[4]
            p.applyExternalForce(robot,toe,[0,0,-load_kg*9.81],toe_pos,p.WORLD_FRAME,physicsClientId=cid)
            p.stepSimulation(physicsClientId=cid)
            errors.append(q-desired);saturations.append(servos.saturation[:3]);angles.append(q)
        errors=np.asarray(errors)
        return {'toe_load_kg':load_kg,'torque_cap_nm':torque_cap,'duration_s':duration,
                'tracking_rmse_rad':np.sqrt(np.mean(errors**2,axis=0)).tolist(),
                'peak_error_rad':np.max(np.abs(errors),axis=0).tolist(),
                'saturation_fraction':np.mean(saturations,axis=0).tolist(),
                'finite':bool(np.all(np.isfinite(angles))),
                'qualification':'synthetic quasi-static toe force; no added load inertia; servo gains unmeasured'}
    finally:p.disconnect(cid)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=Path('runs/leg_check.json'));args=ap.parse_args()
    result={'status':'digital tracking screening, physical identification still required',
            'experiments':[run(load,cap) for cap in (.588,.981) for load in (0.,.10,.25)]}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
