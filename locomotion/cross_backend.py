"""MuJoCo CPU import and independent fixed-leg comparison with Bullet."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pybullet as p
import mujoco
try:
    from .model import export_models,load_config,NEUTRAL,JOINT_NAMES
    from .kinematics import forward
    from .servo import ServoBank
except ImportError:
    from model import export_models,load_config,NEUTRAL,JOINT_NAMES
    from kinematics import forward
    from servo import ServoBank


def urdf_spec(path):
    root=ET.parse(path).getroot()
    for link in root.findall('link'):
        for item in list(link.findall('visual'))+list(link.findall('collision')):
            if item.get('name'):item.set('name',link.get('name')+'_'+item.get('name'))
    extension=ET.SubElement(root,'mujoco')
    ET.SubElement(extension,'compiler',fusestatic='false',discardvisual='true',inertiafromgeom='false')
    spec=mujoco.MjSpec.from_string(ET.tostring(root,encoding='unicode'))
    # MuJoCo permits contacts against a static world parent. Bullet excludes
    # adjacent links here, so preserve that explicit policy in the import.
    for joint in root.findall('joint'):
        spec.add_exclude(bodyname1=joint.find('parent').get('link'),bodyname2=joint.find('child').get('link'))
    spec.option.timestep=1/load_config()['simulation']['physics_hz']
    spec.option.gravity[:]=[0.,0.,-9.81]
    return spec


def import_urdf(path):
    return urdf_spec(path).compile()


def export_mjcf(directory):
    """Keep source inertials and proxy contacts; CAD visuals remain in URDF."""
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    source=export_models()
    leg=urdf_spec(source['single_leg']);leg.compile()
    leg_path=directory/'single_leg.xml'
    leg_path.write_text(leg.to_xml())
    leg_tree=ET.parse(leg_path)
    keys=ET.SubElement(leg_tree.getroot(),'keyframe')
    ET.SubElement(keys,'key',name='neutral',qpos=' '.join(map(str,NEUTRAL)))
    leg_tree.write(leg_path,encoding='utf-8',xml_declaration=True)
    quad=urdf_spec(source['quadruped']);quad.compile()
    quad_path=directory/'quadruped.xml'
    quad_path.write_text(quad.to_xml())
    tree=ET.parse(quad_path);root=tree.getroot();world=root.find('worldbody')
    body=world.find("body[@name='body']")
    if body is None:raise ValueError('MuJoCo import did not preserve the CAD body frame')
    height=json.loads(source['report'].read_text())['neutral_deck_height_m']+.004
    body.set('pos',f'0 0 {height}')
    ET.SubElement(body,'freejoint',name='root_free')
    friction=f'{load_config()["simulation"]["foot_friction"]} 0 0'
    ET.SubElement(world,'geom',name='floor',type='plane',size='3 3 .1',friction=friction)
    for geom in world.iter('geom'):geom.set('friction',friction)
    actuators=ET.SubElement(root,'actuator')
    cap=load_config()['actuator']['torque_limit_nm']
    for joint in JOINT_NAMES:
        ET.SubElement(actuators,'motor',name=joint+'_motor',joint=joint,gear='1',ctrllimited='true',ctrlrange=f'{-cap} {cap}')
    keys=ET.SubElement(root,'keyframe')
    ET.SubElement(keys,'key',name='standing',qpos=' '.join(map(str,np.r_[0.,0.,height,1.,0.,0.,0.,np.tile(NEUTRAL,4)])))
    ET.indent(root);tree.write(quad_path,encoding='utf-8',xml_declaration=True)
    free=mujoco.MjModel.from_xml_path(str(quad_path))
    if free.nq!=19 or free.nu!=12:raise ValueError('expected free base and twelve actuators')
    return {'single_leg':leg_path,'quadruped':quad_path}


def compare_leg(duration=3.,load_kg=.1):
    source=export_models()
    mj=import_urdf(source['single_leg']);data=mujoco.MjData(mj)
    if mj.nq!=3:raise ValueError('expected three single-leg joints')
    toe=mujoco.mj_name2id(mj,mujoco.mjtObj.mjOBJ_BODY,'toe')
    if toe<0:raise ValueError('toe frame missing')
    data.qpos[:]=NEUTRAL;mujoco.mj_forward(mj,data)
    analytic_error=float(np.linalg.norm(data.xpos[toe]-forward(NEUTRAL)))
    dt=mj.opt.timestep
    cid=p.connect(p.DIRECT)
    try:
        p.setGravity(0,0,-9.81,physicsClientId=cid);p.setTimeStep(dt,physicsClientId=cid)
        robot=p.loadURDF(str(source['single_leg']),useFixedBase=True,flags=p.URDF_USE_INERTIA_FROM_FILE,physicsClientId=cid)
        joints=[i for i in range(p.getNumJoints(robot,physicsClientId=cid)) if p.getJointInfo(robot,i,physicsClientId=cid)[2]==p.JOINT_REVOLUTE]
        foot=next(i for i in range(p.getNumJoints(robot,physicsClientId=cid)) if p.getJointInfo(robot,i,physicsClientId=cid)[12].decode()=='toe')
        for i,q in zip(joints,NEUTRAL):p.resetJointState(robot,i,q,physicsClientId=cid)
        p.setJointMotorControlArray(robot,joints,p.VELOCITY_CONTROL,forces=[0]*3,physicsClientId=cid)
        bullet_bank=ServoBank(np.tile(NEUTRAL,4),np.random.default_rng(0),False,dt=dt)
        mj_bank=ServoBank(np.tile(NEUTRAL,4),np.random.default_rng(0),False,dt=dt)
        bq,mq,targets=[],[],[]
        for step in range(round(duration/dt)):
            t=step*dt
            target=NEUTRAL+np.radians([10*np.sin(t*1.5),5*np.sin(t*1.5),8*np.sin(t*1.5)])*min(1,t)
            states=p.getJointStates(robot,joints,physicsClientId=cid)
            q=np.array([s[0] for s in states]);qd=np.array([s[1] for s in states])
            tau=bullet_bank.advance(np.tile(target,4),np.tile(q,4),np.tile(qd,4))[:3]
            p.setJointMotorControlArray(robot,joints,p.TORQUE_CONTROL,forces=tau.tolist(),physicsClientId=cid)
            point=p.getLinkState(robot,foot,computeForwardKinematics=True,physicsClientId=cid)[4]
            p.applyExternalForce(robot,foot,[0,0,-load_kg*9.81],point,p.WORLD_FRAME,physicsClientId=cid)
            data.qfrc_applied[:]=mj_bank.advance(np.tile(target,4),np.tile(data.qpos,4),np.tile(data.qvel,4))[:3]
            data.xfrc_applied[toe,:3]=[0,0,-load_kg*9.81]
            bq.append(q.copy());mq.append(data.qpos.copy());targets.append(target)
            p.stepSimulation(physicsClientId=cid);mujoco.mj_step(mj,data)
        bq,mq,targets=np.array(bq),np.array(mq),np.array(targets)
        expected=sum(float(link.find('inertial/mass').get('value')) for link in ET.parse(source['single_leg']).findall('link'))
        return {'mujoco_version':mujoco.__version__,'duration_s':duration,'load_kg':load_kg,'physics_dt_s':dt,
                'fk_error_m':analytic_error,'mujoco_mass_kg':float(mj.body_mass.sum()),'source_mass_kg':expected,
                'finite':bool(np.all(np.isfinite(bq)) and np.all(np.isfinite(mq))),
                'joint_trajectory_difference_rmse_rad':np.sqrt(np.mean((bq-mq)**2,axis=0)).tolist(),
                'bullet_tracking_rmse_rad':np.sqrt(np.mean((bq-targets)**2,axis=0)).tolist(),
                'mujoco_tracking_rmse_rad':np.sqrt(np.mean((mq-targets)**2,axis=0)).tolist(),
                'scope':'fixed-leg rigid-body comparison with adjacent-link contacts excluded; contact solver and real motor fidelity are not established'}
    finally:p.disconnect(cid)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=Path('runs/mujoco_comparison.json'))
    ap.add_argument('--duration',type=float,default=3.);args=ap.parse_args()
    if args.duration<=0:ap.error('duration must be positive')
    files=export_mjcf(Path(__file__).resolve().parent/'models'/'mujoco')
    result={'models':{key:str(path) for key,path in files.items()},'comparisons':[compare_leg(args.duration,load) for load in (0.,.1,.25)],
            'status':'independent CPU leg comparison and MJCF export; no GPU training port or hardware validation'}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
