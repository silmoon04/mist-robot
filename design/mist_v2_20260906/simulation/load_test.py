"""Supported-body single-leg load ramp; no physical hardware is accessed."""
import copy
import hashlib
import json
import numpy as np
import pybullet as pb
from model import ROOT,load_parameters,fk,total_mass
from run_sim import load_world,ActuatorBank,smooth,base_link_pose


def trial(p,hip_ratio,contacts,dynamic_factor):
    p=copy.deepcopy(p);p["transmission"]["ratios"][1]=hip_ratio
    cid,robot,legs,wheels,names,q0,dt,base,terrain=load_world(p,"single_leg_swing")
    pos,quat=pb.getBasePositionAndOrientation(robot)
    pb.resetBasePositionAndOrientation(robot,[pos[0],pos[1],pos[2]+.4],quat)
    bank=ActuatorBank(p,q0,dt)
    force=total_mass(p)*p["environment"]["gravity_m_s2"]/contacts*dynamic_factor
    history=[]
    for step in range(6000):
        t=step*dt
        load=force*smooth((t-1)/1.5)*(1-smooth((t-4.5)/.5))
        states=pb.getJointStates(robot,list(range(pb.getNumJoints(robot))))
        q=np.array([[states[j][0] for j in row] for row in legs]);qd=np.array([[states[j][1] for j in row] for row in legs])
        torque,tm=bank.update(q,qd,q0)
        for i,row in enumerate(legs):
            for k,j in enumerate(row):pb.setJointMotorControl2(robot,j,pb.TORQUE_CONTROL,force=float(torque[i,k]))
        wheelpos=pb.getLinkState(robot,wheels[0])[0]
        pb.applyExternalForce(robot,wheels[0],[0,0,load],wheelpos,pb.WORLD_FRAME)
        pb.stepSimulation()
        if step%20==0:
            states=pb.getJointStates(robot,list(range(pb.getNumJoints(robot))))
            q=np.array([[states[j][0] for j in row] for row in legs])
            err=np.linalg.norm(fk(p,0,q[0])["axle"]-fk(p,0,q0[0])["axle"])
            history.append({"t":t,"applied_vertical_force_n":load,"joint_angles_rad":q[0].tolist(),
                            "servo_torque_nm":tm[0].tolist(),"foot_error_m":float(err)})
    hold=[h for h in history if 3<=h["t"]<=4.4]
    peakerror=max(h["foot_error_m"] for h in hold)
    rmstorque=np.sqrt(np.mean(np.array([h["servo_torque_nm"] for h in hold])**2,axis=0))
    criteria={"foot_error_below_15mm":peakerror<.015,"motor_rms_below_continuous":float(max(rmstorque))<bank.continuous}
    result={"hip_ratio":hip_ratio,"contacts_equivalent":contacts,"load_multiplier":dynamic_factor,
            "force_n":force,"fixed_base":True,"status":"PASS_IN_MODEL" if all(criteria.values()) else "FAIL_IN_MODEL",
            "criteria":criteria,"hold_max_foot_error_m":peakerror,"hold_servo_rms_nm":rmstorque.tolist(),
            "motor_saturation_fraction":bank.saturated_steps/bank.step,"history":history,
            "parameters_used":p,"parameters_sha256":hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest(),
            "source_sha256":{x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in ["model.py","run_sim.py","load_test.py"]},
            "limitations":"Ideal external vertical force on one suspended wheel, body fixed. This is a loading fixture surrogate, not a gait or measured servo test. Uses the same command-play and compliance approximations as run_sim.py."}
    pb.disconnect(cid)
    return result


if __name__=="__main__":
    out=ROOT/"load_tests";out.mkdir(exist_ok=True)
    results=[]
    for ratio in [2,3.5]:
        for contacts,factor in [(3,1),(2,1.5)]:
            r=trial(load_parameters(),ratio,contacts,factor);results.append(r)
            (out/f"hip{ratio:g}_contacts{contacts}_factor{factor:g}.json").write_text(json.dumps(r,indent=2),encoding="utf-8")
            print(json.dumps({k:r[k] for k in ["hip_ratio","contacts_equivalent","status","force_n","hold_max_foot_error_m","hold_servo_rms_nm"]}),flush=True)
    (out/"summary.json").write_text(json.dumps([{k:v for k,v in r.items() if k not in ["history","parameters_used"]} for r in results],indent=2),encoding="utf-8")
