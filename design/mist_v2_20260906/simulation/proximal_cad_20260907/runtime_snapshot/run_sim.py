"""Run reproducible contact dynamics with unmeasured actuator approximations.

No hardware interfaces. Failures remain failures in the saved report.
"""
import argparse
import copy
import hashlib
import json
import math
import platform
import tempfile
from collections import deque
from pathlib import Path
import numpy as np
import pybullet as pb
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from model import ROOT, build_urdf, coupling, fk, ik, load_parameters, neutral, total_mass


def smooth(t):
    t=np.clip(t,0,1)
    return t*t*(3-2*t)


def support_margin(points, point):
    pts=np.array(points)
    if len(pts)<3:
        return None
    try:
        hull=ConvexHull(pts[:,:2])
        distances=-(hull.equations[:,:2] @ np.array(point)[:2]+hull.equations[:,2])
        return float(np.min(distances))
    except Exception:
        return None


def deadzone(x,width):
    return np.sign(x)*np.maximum(abs(x)-width,0)


def scene_geometry(p,case):
    boxes=[{"name":"floor","size":[40,40,.1],"position":[0,0,-.05],"quaternion_xyzw":[0,0,0,1]}]
    if case in ["step_ascent","step_descent","obstacle_stop"]:
        h=.06 if case=="obstacle_stop" else p["environment"]["step_rise_m"]
        x=1.35 if case=="obstacle_stop" else .94
        boxes.append({"name":"obstacle" if case=="obstacle_stop" else "step","size":[1.4,1.2,h],"position":[x,0,h/2],"quaternion_xyzw":[0,0,0,1]})
    return {"schema_version":1,"boxes":boxes}


def evaluate_foot_trajectories(p,frames,names):
    clearances=[];tracking=[]
    radius=p["geometry"]["wheel_diameter_m"]/2
    halfwidth=p["geometry"]["wheel_width_m"]/2
    for frame in frames:
        actual=np.array(frame["q"]).reshape(4,4)[:,:3]
        target=np.array(frame["target_q"]).reshape(4,3)
        rot=np.array(pb.getMatrixFromQuaternion(frame["base_quaternion_xyzw"])).reshape(3,3)
        base=np.array(frame["base_position"])
        heights=[];errors=[]
        for i in range(4):
            f=fk(p,i,actual[i]);ref=fk(p,i,target[i])
            axis=rot @ f["wheel_axis"]
            axle=base+rot @ f["axle"]
            low=radius*np.sqrt(max(0,1-axis[2]**2))+halfwidth*abs(axis[2])
            heights.append(float(axle[2]-low))
            errors.append(float(np.linalg.norm(f["axle"]-ref["axle"])))
        clearances.append(heights);tracking.append(errors)
    return {"max_actual_wheel_clearance_m":np.max(clearances,axis=0).tolist(),
            "foot_tracking_rms_m":np.sqrt(np.mean(np.array(tracking)**2,axis=0)).tolist()}


class ActuatorBank:
    """Servo shaft controller plus delay, rate limit, play, compliance and limits.

    The play operator removes command travel after reversals. Series compliance
    reduces effective stiffness; it does not integrate separate belt elastic modes.
    """
    def __init__(self,p,q0,dt):
        self.p,self.dt=p,dt
        self.A=coupling(p)
        self.ratios=np.array(p["transmission"]["ratios"])
        self.eta=np.array(p["transmission"]["efficiency"])
        self.s0=(self.A @ q0.T).T
        self.command=self.s0.copy()
        self.play=self.s0.copy()
        self.queue=deque([self.s0.copy()]*(max(1,round(p["servo"]["command_delay_s"]/dt))+1))
        self.filtered=np.zeros_like(self.s0)
        self.maxutil=0.
        self.saturated_steps=0
        self.travel_violations=0
        self.motor_torque=[]
        servo=p["servo"]; tr=p["transmission"]; sim=p["simulation"]
        self.voltage=servo["simulation_voltage_v"]/servo["nominal_voltage_v"]
        self.stall=servo["stall_torque_nm"]*self.voltage
        self.speed=servo["no_load_speed_rpm"]*2*np.pi/60*self.voltage
        self.peak=servo["peak_fraction_of_stall"]*self.stall
        self.continuous=min(servo["continuous_fraction_of_stall"]*self.stall,servo["rated_torque_nm"])
        self.backlash=np.radians(servo["gearbox_backlash_full_width_deg"]+np.array(tr["output_backlash_full_width_deg"])*self.ratios)/2
        self.kp=1/(1/sim["motor_kp_nm_per_rad"]+self.ratios**2/np.array(tr["output_stiffness_nm_per_rad"]))
        self.kd=sim["motor_kd_nm_s_per_rad"]
        self.deadband=np.radians(servo["deadband_deg"])
        self.step=0

    def update(self,q,qd,target):
        s=(self.A @ q.T).T; sd=(self.A @ qd.T).T
        ts=(self.A @ target.T).T
        period=max(1,round(self.p["servo"]["command_period_s"]/self.dt))
        if self.step%period==0:
            self.held_target=ts
        self.queue.append(self.held_target.copy())
        delayed=self.queue.popleft()
        self.command+=np.clip(delayed-self.command,-self.speed*self.dt,self.speed*self.dt)
        self.play=np.clip(self.play,self.command-self.backlash,self.command+self.backlash)
        err=deadzone(self.play-s,self.deadband)
        wanted=self.kp*err-self.kd*sd
        alpha=self.dt/(self.p["servo"]["response_time_constant_s"]+self.dt)
        self.filtered+=alpha*(wanted-self.filtered)
        # Linear four-quadrant DC envelope. Back-driving can retain stall braking
        # torque; same-direction motoring loses available torque with speed.
        same=np.sign(self.filtered)*sd
        speed_limit=self.stall*np.clip(1-same/self.speed,0,1)
        lim=np.minimum(speed_limit,self.peak)
        self.saturated_steps+=int(np.any(abs(self.filtered)>lim))
        torque=np.clip(self.filtered,-lim,lim)
        delta=np.degrees(s-self.s0)
        limits=np.array(self.p["transmission"]["motor_travel_limits_deg"])
        self.travel_violations+=int(np.any((delta<limits[:,0])|(delta>limits[:,1])))
        self.motor_torque.append(torque.copy())
        self.maxutil=max(self.maxutil,float(np.max(abs(torque))/self.continuous))
        self.step+=1
        joint=np.stack([self.A.T @ (self.eta*t) for t in torque])
        joint-=np.array(self.p["transmission"]["output_viscous_friction_nm_s_per_rad"])*qd
        return joint,torque


def load_world(p,case):
    cid=pb.connect(pb.DIRECT)
    pb.setGravity(0,0,-p["environment"]["gravity_m_s2"])
    dt=1/p["simulation"]["physics_hz"]
    pb.setTimeStep(dt)
    pb.setPhysicsEngineParameter(numSolverIterations=p["simulation"]["solver_iterations"],deterministicOverlappingPairs=1)
    terrain={}
    for box in scene_geometry(p,case)["boxes"]:
        shape=pb.createCollisionShape(pb.GEOM_BOX,halfExtents=np.array(box["size"])/2)
        terrain[box["name"]]=pb.createMultiBody(0,shape,basePosition=box["position"])
    q0=neutral(p)
    height=p["geometry"]["hip_to_wheel_axle_height_m"]+p["geometry"]["wheel_diameter_m"]/2+.001
    if case=="step_descent":
        height+=p["environment"]["step_rise_m"]
    base_x=1.42 if case=="step_descent" else 0
    # A run owns its input file. Concurrent experiments must not replace one
    # another's URDF or the saved baseline artifact between export and load.
    with tempfile.TemporaryDirectory(prefix="mist_sim_") as directory:
        urdf=build_urdf(p,Path(directory)/"candidate.urdf")
        robot=pb.loadURDF(str(urdf),[base_x,0,height],useFixedBase=case.startswith("single_leg"),
                          flags=pb.URDF_USE_INERTIA_FROM_FILE|pb.URDF_USE_SELF_COLLISION|pb.URDF_USE_SELF_COLLISION_EXCLUDE_PARENT)
    ids={pb.getJointInfo(robot,i)[1].decode():i for i in range(pb.getNumJoints(robot))}
    names=list(ids)
    legids=[[ids[name+s] for s in ["_q1_yaw","_q2_hip","_q3_knee"]] for name in p["geometry"]["leg_names"]]
    wheelids=[ids[n+"_wheel_drive"] for n in p["geometry"]["leg_names"]]
    for i in range(pb.getNumJoints(robot)):
        pb.setJointMotorControl2(robot,i,pb.VELOCITY_CONTROL,force=0)
        pb.enableJointForceTorqueSensor(robot,i,True)
        pb.changeDynamics(robot,i,linearDamping=0,angularDamping=0,jointDamping=0,
                          lateralFriction=p["environment"]["tire_friction_coefficient"],
                          rollingFriction=p["environment"]["rolling_friction_coefficient"] if i in wheelids else 0,
                          spinningFriction=.001,restitution=p["environment"]["contact_restitution"])
    # Adjacent geometry shares shaft envelopes. Adjacent collisions are excluded by
    # URDF flag; wheel carrier and tire additionally overlap in this coarse model.
    for i,w in enumerate(wheelids):
        pb.setCollisionFilterPair(robot,robot,legids[i][1],w,0)
    for i,row in enumerate(legids):
        for j,jid in enumerate(row):
            pb.resetJointState(robot,jid,q0[i,j])
    pb.changeDynamics(robot,-1,linearDamping=0,angularDamping=0)
    return cid,robot,legids,wheelids,names,q0,dt,np.array([base_x,0,height]),terrain


def target_at(p,case,t,q0,base0):
    target=q0.copy(); speed=0.; valid=True
    if case in ["drive","obstacle_stop"]:
        speed=.9*smooth((t-1)/2)
    if case=="stance_height":
        dz=.025*math.sin(2*math.pi*max(0,t-1)/4) if t>1 else 0
        for i in range(4):
            pos=fk(p,i,q0[i])["axle"].copy();pos[2]-=dz
            target[i],ok=ik(p,i,pos);valid &= ok
    if case=="single_leg_swing" and t>1:
        cycle=4.; phase=((t-1)%cycle)/cycle
        active=0
        pos=fk(p,active,q0[active])["axle"].copy()
        pos[0]+=.025*math.sin(2*math.pi*phase)
        pos[2]+=.055*math.sin(np.pi*phase)**2
        target[active],valid=ik(p,active,pos)
    if case=="crawl" and t>1:
        cycle=6.;phase=((t-1)%cycle)/cycle;active=int((t-1)//cycle)%4
        # Shift the body projection inside the remaining three wheel contacts
        # before lifting. Grounded wheel targets remain fixed in the nominal world.
        front=1 if active<2 else -1;side=1 if active%2==0 else -1
        shift=np.array([-front*.030,-side*.022,0])*min(smooth(phase/.2),smooth((1-phase)/.2))
        lift_phase=np.clip((phase-.22)/.56,0,1)
        completed=int((t-1)//cycle);body_advance=.060*(t-1)/(4*cycle)
        for i in range(4):
            steps=completed//4+int(i<active)
            foot_advance=.060*steps
            if i==active:foot_advance+=.060*smooth(lift_phase)
            pos=fk(p,i,q0[i])["axle"].copy()-shift
            pos[0]+=foot_advance-body_advance
            if i==active:
                pos[2]+=.045*math.sin(np.pi*lift_phase)**2
            target[i],ok=ik(p,i,pos);valid &= ok
    if case in ["step_ascent","step_descent"] and t>1:
        # One conservative scripted attempt. The free base is never teleported.
        # It exposes the endpoint/force challenge; it is not a validated planner.
        phase=max(0,min((t-2)/5,1.))
        active=0 if phase<.5 else 1
        u=phase*2 if phase<.5 else (phase-.5)*2
        height=p["environment"]["step_rise_m"]
        body_raise=.0475*smooth((t-1)/1) if case=="step_ascent" else -.12*smooth((t-1)/2)
        for i in range(4):
            pos=fk(p,i,q0[i])["axle"].copy()
            pos[2]-=body_raise
            if i<=active:
                local_u=u if i==active else 1.
                pos[0]+=.15*smooth(local_u)
                pos[2]+=(1 if case=="step_ascent" else -1)*height*smooth(local_u)
                pos[2]+=.035*math.sin(np.pi*local_u)**2
            target[i],ok=ik(p,i,pos);valid &= ok
        speed=.06 if t>6 else 0.
    return target,speed,bool(valid)


def world_com(robot):
    mass=[];positions=[]
    for j in range(-1,pb.getNumJoints(robot)):
        m=pb.getDynamicsInfo(robot,j)[0]
        pos=pb.getBasePositionAndOrientation(robot)[0] if j==-1 else pb.getLinkState(robot,j)[0]
        mass.append(m);positions.append(pos)
    return np.average(np.array(positions),axis=0,weights=mass)


def base_link_pose(robot):
    com,quat=pb.getBasePositionAndOrientation(robot)
    info=pb.getDynamicsInfo(robot,-1)
    local,local_quat=info[3],info[4]
    # PyBullet reports the centre-of-mass frame. With a full inertia tensor it
    # also rotates that frame to principal axes; undo both local transforms.
    rotation=Rotation.from_quat(quat)*Rotation.from_quat(local_quat).inv()
    pos=np.array(com)-rotation.apply(local)
    return pos.tolist(),rotation.as_quat().tolist()


def run_case(p,case,duration=None,output_root=None):
    out=Path(output_root or ROOT/"outputs")/case;out.mkdir(parents=True,exist_ok=True)
    cid,robot,legids,wheelids,names,q0,dt,base0,terrain=load_world(p,case)
    bank=ActuatorBank(p,q0,dt)
    duration=duration or (26 if case=="crawl" else p["simulation"]["duration_s"])
    frames=[];errors=[];tilts=[];margins=[];slips=[];forces=[];self_contacts=[];invalid=0;body_contacts=0;obstacle_contacts=0
    stop_latched=False;minimum_obstacle_gap=float("inf")
    wheel_positions=[0.]*4
    motor=p["wheel_motor"]; ratio=p["servo"]["simulation_voltage_v"]/motor["nominal_voltage_v"]
    wspeed=motor["no_load_speed_rpm"]*2*np.pi/60*ratio
    wstall=motor["stall_torque_nm"]*ratio
    istall=motor["stall_current_a"]*ratio
    current_torque=wstall*max(0,motor["current_limit_a"]-motor["no_load_current_a"])/max(.01,istall-motor["no_load_current_a"])
    stride=max(1,round(1/(p["simulation"]["record_hz"]*dt)))
    for step in range(round(duration/dt)):
        t=step*dt
        states=pb.getJointStates(robot,list(range(pb.getNumJoints(robot))))
        q=np.array([[states[j][0] for j in row] for row in legids]);qd=np.array([[states[j][1] for j in row] for row in legids])
        target,speed,valid=target_at(p,case,t,q0,base0)
        if case=="obstacle_stop":
            gap=.65-max(pb.getLinkState(robot,j)[0][0] for j in wheelids)-p["geometry"]["wheel_diameter_m"]/2
            minimum_obstacle_gap=min(minimum_obstacle_gap,gap)
            forward_speed=max(0,pb.getBaseVelocity(robot)[0][0])
            if gap<.08+forward_speed**2/(2*1.0):stop_latched=True
            if stop_latched:speed=0
        invalid+=int(not valid)
        torque,shaft_torque=bank.update(q,qd,target)
        for i,row in enumerate(legids):
            for k,j in enumerate(row):
                pb.setJointMotorControl2(robot,j,pb.TORQUE_CONTROL,force=float(torque[i,k]))
        for i,j in enumerate(wheelids):
            heading=fk(p,i,q[i])["heading"]
            requested=-math.cos(heading)*speed/(p["geometry"]["wheel_diameter_m"]/2)
            vel=states[j][1]
            if speed==0:
                wanted=.35*(wheel_positions[i]-states[j][0])-.03*vel
            else:
                wanted=.035*(requested-vel);wheel_positions[i]=states[j][0]
            limit=min(current_torque,wstall*np.clip(1-np.sign(wanted)*vel/wspeed,0,1))
            pb.setJointMotorControl2(robot,j,pb.TORQUE_CONTROL,force=float(np.clip(wanted,-limit,limit)))
        pb.stepSimulation()
        if step%stride==0:
            states=pb.getJointStates(robot,list(range(pb.getNumJoints(robot))))
            q=np.array([[states[j][0] for j in row] for row in legids])
            bpos,bquat=base_link_pose(robot)
            euler=pb.getEulerFromQuaternion(bquat)
            tilt=math.degrees(math.acos(np.clip(pb.getMatrixFromQuaternion(bquat)[8],-1,1)))
            grf=np.zeros(4);contacts=[];lateral=[]
            for c in pb.getContactPoints(bodyA=robot):
                if c[2]==robot:
                    if c[8]<-.001:
                        self_contacts.append([t,c[3],c[4],c[8]])
                    continue
                if c[2]==terrain.get("obstacle") and c[9]>.25:obstacle_contacts+=1
                if c[3] not in wheelids and c[9]>.25:
                    body_contacts+=1
                if c[3] in wheelids:
                    i=wheelids.index(c[3]);grf[i]+=c[9]
                    if c[9]>.25 and c[7][2]>.5:
                        contacts.append(c[5])
            for i,j in enumerate(wheelids):
                state=pb.getLinkState(robot,j,computeLinkVelocity=True)
                axis_local=np.array([0,-1,0])
                axis=np.array(pb.getMatrixFromQuaternion(state[1])).reshape(3,3) @ axis_local
                lateral.append(float(np.dot(state[6],axis)))
            com=world_com(robot);margin=support_margin(contacts,com)
            if margin is not None:margins.append(margin)
            errors.append(np.degrees(q-target));tilts.append(tilt);slips.append(lateral);forces.append(grf.tolist())
            frame={"t":round(t,4),"base_position":list(bpos),"base_quaternion_xyzw":list(bquat),
                   "q":[float(x[0]) for x in states],"target_q":target.flatten().tolist(),
                   "contact_normal_n":grf.tolist(),"com_world":com.tolist(),"tilt_deg":tilt,
                   "support_margin_m":margin,"wheel_lateral_velocity_m_s":lateral}
            frames.append(frame)
    final_position=np.array(base_link_pose(robot)[0])
    rms=float(np.sqrt(np.mean(np.array(errors)[min(len(errors)-1,50):]**2)))
    footmetrics=evaluate_foot_trajectories(p,frames,names)
    mt=np.array(bank.motor_torque)
    torque_rms=np.sqrt(np.mean(mt**2,axis=0))
    peak_tilt=max(tilts)
    criteria={"did_not_fall":peak_tilt<p["simulation"]["fall_tilt_deg"],
              "joint_tracking_rms":rms<p["simulation"]["joint_tracking_rms_limit_deg"],
              "continuous_motor_rms":bool(np.max(torque_rms)<bank.continuous),
              "reachable_targets":invalid==0,"motor_travel_limits":bank.travel_violations==0,
              "no_nonwheel_ground_support":body_contacts==0,
              "coarse_self_collision":len(self_contacts)==0}
    if case=="drive":criteria["forward_distance_2m"]=float(final_position[0]-base0[0])>2
    if case=="crawl":
        criteria["tilt_below_10deg"]=peak_tilt<10
        criteria["full_four_leg_cycle"]=duration>=25
        criteria["forward_distance_25mm"]=float(final_position[0]-base0[0])>.025
        criteria["all_feet_clear_15mm"]=min(footmetrics["max_actual_wheel_clearance_m"])>=p["environment"]["toe_clearance_m"]
        criteria["foot_tracking_rms"]=max(footmetrics["foot_tracking_rms_m"])<=p["simulation"]["step_tracking_rms_limit_m"]
    if case=="obstacle_stop":
        criteria["no_obstacle_contact"]=obstacle_contacts==0
        criteria["stopped_before_obstacle"]=stop_latched and minimum_obstacle_gap>.02 and abs(pb.getBaseVelocity(robot)[0][0])<.03
    if case in ["step_ascent","step_descent"]:
        criteria["all_wheels_changed_level"]=bool(all((pb.getLinkState(robot,j)[0][2]>
            p["environment"]["step_rise_m"]+.02) if case=="step_ascent" else
            (pb.getLinkState(robot,j)[0][2]<.09) for j in wheelids))
        criteria["body_traversed_edge"]=bool(final_position[0]>.5 if case=="step_ascent" else final_position[0]>1.85)
    report={"case":case,"status":"PASS_IN_MODEL" if all(criteria.values()) else "FAIL_IN_MODEL",
            "criteria":criteria,"mass_kg":total_mass(p),"duration_s":duration,"dt_s":dt,
            "base_displacement_m":(final_position-base0).tolist(),"max_tilt_deg":peak_tilt,
            "joint_tracking_rms_deg":rms,"max_servo_rms_nm":float(np.max(torque_rms)),
            "servo_continuous_limit_nm":bank.continuous,"servo_peak_limit_nm":bank.peak,
            "motor_saturation_fraction":bank.saturated_steps/bank.step,
            "unreachable_target_fraction":invalid/bank.step,"motor_travel_violation_fraction":bank.travel_violations/bank.step,
            "min_sampled_support_margin_m":min(margins) if margins else None,
            "max_wheel_normal_force_n":float(np.max(forces)),
            "wheel_lateral_velocity_rms_m_s":float(np.sqrt(np.mean(np.array(slips)**2))),
            "self_collision_samples":len(self_contacts),"self_collision_examples":self_contacts[:10],
            "base_contact_samples":body_contacts,"fixed_base":case.startswith("single_leg"),
            "limitations":["Unmeasured backlash, compliance, friction, servo dynamics, thermal duty and mass estimates.",
                           "Command play hysteresis and reduced series stiffness do not model true load-side gap engagement under force reversal. Rotor/reflected gearbox inertia omitted.",
                           "Simple boxes/cylinders, selected adjacent self collisions excluded; no printed-part stress or wire model.",
                           "Step test is a scripted challenge; a failure may concern controller and geometry, not a proof no controller exists.",
                           "No sensor perception, obstacle avoidance planner, stair-nose or tire deformation model."]}
    report.update(footmetrics)
    report["obstacle_contact_samples"]=obstacle_contacts
    report["minimum_obstacle_gap_m"]=minimum_obstacle_gap if case=="obstacle_stop" else None
    report["source_sha256"]={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ["run_sim.py","model.py"]}
    report["parameters_sha256"]=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()
    (out/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    (out/"trajectory.json").write_text(json.dumps({"schema_version":1,"case":case,"joint_names":names,"frames":frames}),encoding="utf-8")
    (out/"parameters_used.json").write_text(json.dumps(p,indent=2),encoding="utf-8")
    (out/"scene.json").write_text(json.dumps(scene_geometry(p,case),indent=2),encoding="utf-8")
    pb.disconnect(cid)
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--case",default="all",
        choices=["all","stand","single_leg_swing","stance_height","drive","crawl","step_ascent","step_descent","obstacle_stop"])
    parser.add_argument("--duration",type=float);parser.add_argument("--parameters",type=Path);parser.add_argument("--output",type=Path)
    args=parser.parse_args();p=load_parameters(args.parameters)
    cases=["stand","single_leg_swing","stance_height","drive","crawl","step_ascent","step_descent","obstacle_stop"] if args.case=="all" else [args.case]
    reports=[]
    for case in cases:
        r=run_case(copy.deepcopy(p),case,args.duration,args.output);reports.append(r)
        print(json.dumps({k:r[k] for k in ["case","status","max_tilt_deg","joint_tracking_rms_deg","base_displacement_m"]}),flush=True)
    manifest={"python":platform.python_version(),"pybullet_api":pb.getAPIVersion(),
              "parameters_sha256":hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest(),"reports":reports}
    destination=Path(args.output or ROOT/"outputs");destination.mkdir(exist_ok=True,parents=True)
    (destination/"summary.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")


if __name__=="__main__":main()
