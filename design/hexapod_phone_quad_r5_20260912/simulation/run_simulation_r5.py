"""R5 mass-bound rigid-body runs with configurable coxa geometry."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import sys

import numpy as np
import pybullet as p

from export_urdf import DESIGN, HERE, digest, export, load_manifest
from kinematics import FOOT_RADIUS, LEGS, SETTINGS, SETTINGS_PATH, TIBIA, crawl_plan, inverse_world, nominal_stance, sample_phase, support_margin
from statics import loads, solve_pose
from control_uncertainty import describe_case, feedback_deadband


def plain(value):
    if isinstance(value, np.ndarray): return value.tolist()
    if isinstance(value, np.generic): return value.item()
    if isinstance(value, dict): return {k:plain(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [plain(v) for v in value]
    return value


def evaluate(args):
    if not 0 < args.effort <= 0.8:
        raise ValueError("This screening workflow permits effort caps only up to 0.8 Nm")
    uncertainty=describe_case(args.torque_gain_scale,args.torque_damping_scale,args.feedback_deadband_deg)
    if args.controller!="torque":
        raise ValueError("R5 uncertainty cases require the finite torque controller so every declared proxy is active")
    args.output.mkdir(parents=True, exist_ok=True)
    urdf = args.output / "quadruped.urdf"
    manifest_input_hash=digest(args.manifest)
    if args.expected_manifest_sha256 and manifest_input_hash.lower()!=args.expected_manifest_sha256.lower():
        raise ValueError("Selected manifest bytes do not match the frozen R5 identity")
    manifest = load_manifest(args.manifest)
    if manifest.get("revision")!=SETTINGS.get("revision") or not str(manifest.get("revision","")).startswith("hex_quad_r5"):
        raise ValueError("R5 requires a matching R5 manifest and shared settings; stale releases are not accepted")
    if not isinstance(manifest.get("mass_model"),dict) or not manifest["mass_model"].get("kind"):
        raise ValueError("R5 requires explicit mass_model.kind metadata, including the manufacturing or solid-CAD mass basis")
    receipt = export(args.manifest, urdf, args.effort)
    if receipt["manifest_sha256"]!=manifest_input_hash:
        raise ValueError("Manifest changed between mass loading and URDF export")
    receipt["mass_model"]=manifest["mass_model"]
    receipt["inertial_source"]="Masses, centers of mass and inertia tensors from the selected explicit manifest. No fallback mass and no independently added fastener allowance."
    (args.output/"urdf_receipt.json").write_text(json.dumps(plain(receipt),indent=2)+"\n",encoding="utf-8")
    source_hashes={f.name:digest(f) for f in [Path(__file__),HERE/"kinematics.py",HERE/"statics.py",HERE/"export_urdf.py",HERE/"control_uncertainty.py"]}
    settings_hash=digest(SETTINGS_PATH)
    if digest(args.manifest)!=receipt["manifest_sha256"]:
        raise ValueError("CAD manifest changed while loading the run")
    neutral = np.radians([0,args.hip,args.knee])
    initial_base, initial_feet = nominal_stance(neutral)
    plan = crawl_plan(args.stride/1000,args.shift/1000,args.lower/1000,args.lift/1000,neutral)
    static_samples = []
    static_failure = None
    try:
        for phase_index,phase in enumerate(plan):
            for t in np.linspace(0,1,41):
                b,f = sample_phase(phase,float(t))
                support = [leg for leg in LEGS if not (phase["kind"]=="swing" and leg==phase["leg"])]
                result = loads(manifest,b,f,support)
                static_samples.append({"phase":phase_index,"fraction":float(t),"torques":result["torques"],"normal_forces":result["normal_forces"],"support_margin_m":result["support_margin_m"],"joint_deg":{k:np.degrees(v) for k,v in result["angles"].items()}})
    except ValueError as error:
        static_failure = str(error)
    static_peak = {name:max(abs(s["torques"][name]) for s in static_samples) for name in receipt["joint_names"] if name!="phone_pan"} if static_samples else {}
    client = p.connect(p.DIRECT)
    p.setGravity(0,0,-9.81)
    timestep = 1/240
    p.setTimeStep(timestep)
    p.setPhysicsEngineParameter(numSolverIterations=150, deterministicOverlappingPairs=1, enableConeFriction=1)
    plane_shape=p.createCollisionShape(p.GEOM_BOX,halfExtents=[2,2,0.01])
    floor=p.createMultiBody(baseMass=0,baseCollisionShapeIndex=plane_shape,basePosition=[0,0,-0.01])
    p.changeDynamics(floor,-1,lateralFriction=args.friction,restitution=0)
    robot=p.loadURDF(str(urdf),basePosition=initial_base, useFixedBase=False,flags=p.URDF_USE_INERTIA_FROM_FILE)
    joint_map={p.getJointInfo(robot,i)[1].decode():i for i in range(p.getNumJoints(robot))}
    link_map={p.getJointInfo(robot,i)[12].decode():i for i in range(p.getNumJoints(robot))}
    ordered=list(receipt["joint_names"])
    indices=[joint_map[k] for k in ordered]
    base_inertial_inverse=p.invertTransform(p.getDynamicsInfo(robot,-1)[3],p.getDynamicsInfo(robot,-1)[4])
    masses={-1:p.getDynamicsInfo(robot,-1)[0],**{i:p.getDynamicsInfo(robot,i)[0] for i in indices}}
    for index in [-1]+indices:
        p.changeDynamics(robot,index,lateralFriction=args.friction,spinningFriction=0.002,rollingFriction=0,restitution=0,linearDamping=0.02,angularDamping=0.02)
    for leg in LEGS:
        for kind,q in zip(("yaw","hip","knee"),neutral):
            p.resetJointState(robot,joint_map[f"{kind}_{leg}"],q)
    p.resetJointState(robot,joint_map["phone_pan"],0)
    p.setJointMotorControlArray(robot,indices,p.VELOCITY_CONTROL,forces=[0]*len(indices))
    trajectory=[]
    metrics=[]
    failure=None
    step_count=0
    initial_observed=None
    end_stand=None
    command_angles={f"{kind}_{leg}":float(q) for leg in LEGS for kind,q in zip(("yaw","hip","knee"),neutral)}
    command_angles["phone_pan"]=0.0
    commanded_torques={name:0.0 for name in ordered}
    finite_kp={"yaw":3.0*args.torque_gain_scale,"hip":8.0*args.torque_gain_scale,"knee":6.0*args.torque_gain_scale,"phone":0.8*args.torque_gain_scale}
    finite_kd={"yaw":0.25*args.torque_damping_scale,"hip":0.4*args.torque_damping_scale,"knee":0.15*args.torque_damping_scale,"phone":0.03*args.torque_damping_scale}

    def state():
        base_com,inertial_quat=p.getBasePositionAndOrientation(robot)
        base,quat=p.multiplyTransforms(base_com,inertial_quat,*base_inertial_inverse)
        base=np.array(base)
        positions={-1:np.array(base_com)}
        toes={}
        for name,index in link_map.items():
            linkstate=p.getLinkState(robot,index,computeForwardKinematics=True)
            positions[index]=np.array(linkstate[0])
            if name.startswith("tibia"):
                lr=np.array(p.getMatrixFromQuaternion(linkstate[5])).reshape(3,3)
                toes[name.split("_")[1]]=np.array(linkstate[4])+lr@np.array([TIBIA,0,0])
        com=sum(masses[i]*positions[i] for i in masses)/sum(masses.values())
        contacts=p.getContactPoints(robot,floor)
        toe_contact_extent=math.hypot(FOOT_RADIUS,0.007)+0.0015
        valid_toe={leg:[c for c in contacts if c[3]==link_map[f"tibia_{leg}"] and np.linalg.norm(np.asarray(c[5])-toes[leg])<=toe_contact_extent] for leg in LEGS}
        foot_contacts={leg:sum(c[9] for c in values) for leg,values in valid_toe.items()}
        foot_forces={leg:sum((np.asarray(c[7])*c[9]+np.asarray(c[11])*c[10]+np.asarray(c[13])*c[12] for c in values),np.zeros(3)) for leg,values in valid_toe.items()}
        valid_contacts=[c for values in valid_toe.values() for c in values]
        xy=[c[6][:2] for c in valid_contacts if c[9]>0.01]
        bad_contacts=[c for c in contacts if c[9]>0.1 and c not in valid_contacts]
        joints=p.getJointStates(robot,indices)
        return base,np.array(quat),np.array(p.getEulerFromQuaternion(quat)),com,toes,foot_contacts,support_margin(com[:2],xy),bad_contacts,joints,foot_forces

    def advance(target, phase_name, phase_fraction, planned_feet, swing=None, feedforward=None):
        nonlocal step_count, failure
        before=p.getJointStates(robot,indices)
        for name,index,joint_state in zip(ordered,indices,before):
            if args.controller=="position":
                p.setJointMotorControl2(robot,index,p.POSITION_CONTROL,targetPosition=target[name],targetVelocity=0,force=args.effort,positionGain=args.kp,velocityGain=1,maxVelocity=1.0)
            else:
                delta=float(np.clip(target[name]-command_angles[name],-timestep,timestep))
                command_angles[name]+=delta
                desired_velocity=delta/timestep
                kind=name.split("_")[0]
                position_error=feedback_deadband(command_angles[name]-joint_state[0],math.radians(args.feedback_deadband_deg))
                torque=(feedforward or {}).get(name,0.0)+finite_kp[kind]*position_error+finite_kd[kind]*(desired_velocity-joint_state[1])
                torque=float(np.clip(torque,-args.effort,args.effort))
                if abs(joint_state[1])>1 and torque*joint_state[1]>0:
                    torque=0.0
                commanded_torques[name]=torque
                p.setJointMotorControl2(robot,index,p.TORQUE_CONTROL,force=torque)
        p.stepSimulation()
        step_count+=1
        if step_count%12:
            return True
        base,quat,euler,com,toes,contacts,margin,bad,joints,foot_forces=state()
        stance=[leg for leg in LEGS if leg!=swing]
        slip=max(float(np.linalg.norm(toes[leg][:2]-planned_feet[leg][:2])) for leg in stance)
        measured_torques={name:j[3] for name,j in zip(ordered,joints)} if args.controller=="position" else commanded_torques.copy()
        entry={"time_s":step_count*timestep,"phase":phase_name,"phase_fraction":phase_fraction,"swing_leg":swing,"base_m":base,"base_quat_xyzw":quat,"rpy_deg":np.degrees(euler),"com_m":com,"support_margin_m":margin,"foot_normal_n":contacts,"foot_force_world_n":foot_forces,"toe_m":toes,"stance_error_m":slip,"nonfoot_contact":bool(bad),"joint_rad":{name:j[0] for name,j in zip(ordered,joints)},"joint_velocity_rad_s":{name:j[1] for name,j in zip(ordered,joints)},"joint_target_rad":target.copy(),"joint_torque_nm":measured_torques}
        metrics.append(entry)
        trajectory.append(entry)
        if np.max(np.abs(euler[:2]))>math.radians(30) or base[2]<0.045:
            failure=f"Free base fell during {phase_name} at {step_count*timestep:.2f}s"
            return False
        return True

    stand_target={f"{kind}_{leg}":float(q) for leg in LEGS for kind,q in zip(("yaw","hip","knee"),neutral)}
    stand_target["phone_pan"]=0.0
    stand_ff=loads(manifest,initial_base,initial_feet,list(LEGS),correct_com=False)["torques"]
    for index in range(4*240):
        if not advance(stand_target,"stand",index/(4*240),initial_feet,feedforward=stand_ff): break
    if failure is None:
        end_stand=state()
        initial_observed=end_stand[0].copy()
        for index in range(24*240):
            fraction=index/(24*240-1)
            stand_target["phone_pan"]=2*math.pi*(fraction*fraction*(3-2*fraction))
            if not advance(stand_target,"phone_pan",fraction,initial_feet,feedforward=stand_ff): break
    if failure is None:
        # Planner uses every CAD link COM when positioning the body over support.
        for phase_index,phase in enumerate(plan):
            duration=int(phase["seconds"]*240)
            phase_name=f"{phase_index:02d}_{phase['kind']}"+(f"_{phase['leg']}" if "leg" in phase else "")
            for index in range(duration):
                frac=index/max(1,duration-1)
                b,f=sample_phase(phase,frac)
                try:
                    support=[leg for leg in LEGS if not(phase["kind"]=="swing" and leg==phase["leg"])]
                    desired=loads(manifest,b,f,support)
                    angles,feedforward=desired["angles"],desired["torques"]
                except ValueError as error:
                    failure=f"Mass-corrected IK failed in {phase_name}: {error}"
                    break
                target={f"{kind}_{leg}":float(q) for leg in LEGS for kind,q in zip(("yaw","hip","knee"),angles[leg])}
                target["phone_pan"]=2*math.pi
                if not advance(target,phase_name,frac,f,phase.get("leg"),feedforward): break
            if failure: break
    if failure is None:
        for index in range(3*240):
            if not advance(target,"settle",index/(3*240),f,feedforward=feedforward): break
    final=state()
    # A reproducible camera preview is supplementary, never a physics pass criterion.
    try:
        from PIL import Image
        view=p.computeViewMatrixFromYawPitchRoll(final[3].tolist(),0.65,35,-24,0,2)
        proj=p.computeProjectionMatrixFOV(45,1.5,0.01,10)
        rgba=p.getCameraImage(1200,800,view,proj,renderer=p.ER_TINY_RENDERER)[2]
        Image.fromarray(np.asarray(rgba,dtype=np.uint8).reshape(800,1200,4)[:,:,:3]).save(args.output/"simulation.png")
    except ImportError:
        pass
    p.disconnect(client)
    standing=[m for m in metrics if m["phase"]=="stand" and m["time_s"]>=3]
    pan_metrics=[m for m in metrics if m["phase"]=="phone_pan"]
    crawling=[m for m in metrics if m["phase"] not in ("stand","phone_pan")]
    swing_mid=[m for m in crawling if "swing" in m["phase"] and 0.15<m["phase_fraction"]<0.85]
    torque_peaks={name:max(abs(m["joint_torque_nm"][name]) for m in metrics) for name in ordered}
    saturation={name:sum(abs(m["joint_torque_nm"][name])>=0.98*args.effort for m in metrics)/max(1,len(metrics)) for name in ordered}
    advance_x=float(final[0][0]-initial_observed[0]) if initial_observed is not None else 0.0
    stand_ok=bool(standing) and all(np.max(np.abs(m["rpy_deg"][:2]))<5 and all(n>0.1 for n in m["foot_normal_n"].values()) and m["support_margin_m"] is not None and m["support_margin_m"]>0.01 and not m["nonfoot_contact"] for m in standing)
    pan_ok=bool(pan_metrics) and pan_metrics[-1]["phase_fraction"]>0.99 and all(abs(m["joint_rad"]["phone_pan"]-m["joint_target_rad"]["phone_pan"])<math.radians(5) and np.max(np.abs(m["rpy_deg"][:2]))<5 and all(n>0.1 for n in m["foot_normal_n"].values()) and not m["nonfoot_contact"] for m in pan_metrics)
    stepping={}
    for leg in LEGS:
        samples=[m for m in swing_mid if m["swing_leg"]==leg]
        stepping[leg]={"samples":len(samples),"peak_clearance_mm":max((m["toe_m"][leg][2]-FOOT_RADIUS)*1000 for m in samples) if samples else 0,"airborne_fraction":sum(m["foot_normal_n"][leg]<0.1 for m in samples)/max(1,len(samples)),"three_support_fraction":sum(all(m["foot_normal_n"][other]>0.1 for other in LEGS if other!=leg) for m in samples)/max(1,len(samples))}
    true_steps=all(s["peak_clearance_mm"]>=10 and s["airborne_fraction"]>=0.9 and s["three_support_fraction"]>=0.9 for s in stepping.values())
    contact_margin_ok=bool(swing_mid) and all(m["support_margin_m"] is not None and m["support_margin_m"]>=0.005 for m in swing_mid)
    stance_ok=bool(crawling) and max(m["stance_error_m"] for m in crawling)<0.010
    crawl_ok=failure is None and advance_x>=args.minimum_advance/1000 and true_steps and contact_margin_ok and stance_ok and bool(crawling) and max(np.max(np.abs(m["rpy_deg"][:2])) for m in crawling)<8 and all(not m["nonfoot_contact"] for m in crawling)
    static_ok=static_failure is None and bool(static_peak) and max(static_peak.values())<=args.effort and all(min(s["normal_forces"].values())>=0 for s in static_samples)
    input_unchanged=digest(args.manifest)==receipt["manifest_sha256"] and digest(SETTINGS_PATH)==settings_hash and digest(urdf)==receipt["urdf_sha256"] and all(digest(item["resolved_mesh"])==item["mesh_sha256"] for item in manifest["links"].values()) and all(digest(HERE/name)==value for name,value in source_hashes.items())
    summary={
        "created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "status":("bounded_simulation_pass" if args.effort<=0.588 else "experimental_rated_torque_pass") if stand_ok and pan_ok and crawl_ok and static_ok and input_unchanged else "not_validated",
        "failure":failure,"static_failure":static_failure,
        "gates":{"standing":stand_ok,"phone_full_pan":pan_ok,"crawl":crawl_ok,"actual_foot_steps":true_steps,"mid_swing_support_margin":contact_margin_ok,"stance_position":stance_ok,"quasi_static_torque":static_ok,"sustained_torque_screen":bool(static_peak) and max(static_peak.values())<=0.588,"physical_fit":False,"hardware_walking":False,"printed_material_strength":False},
        "inputs":{"manifest_sha256":receipt["manifest_sha256"],"urdf_sha256":receipt["urdf_sha256"],"settings_sha256":settings_hash,"source_sha256":source_hashes,"unchanged_during_run":input_unchanged},
        "mass_kg":receipt["total_mass_kg"],
        "design_revision":manifest["revision"],
        "mass_model":manifest["mass_model"],
        "uncertainty_case":uncertainty,
        "sampled_ground_loads":{"sampling_hz":20,"maximum_horizontal_force_per_foot_n":max(float(np.linalg.norm(force[:2])) for m in metrics for force in m["foot_force_world_n"].values()),"maximum_resultant_force_per_foot_n":max(float(np.linalg.norm(force)) for m in metrics for force in m["foot_force_world_n"].values()),"scope":"Sampled level-floor contact forces for this motion only. Not an impact, structural-strength or fatigue qualification."},
        "stepping_evidence":stepping,
        "controller_tracking":{"maximum_joint_speed_rad_s":max(abs(v) for m in metrics for v in m["joint_velocity_rad_s"].values()),"maximum_phone_error_deg":max(abs(m["joint_rad"]["phone_pan"]-m["joint_target_rad"]["phone_pan"])*180/math.pi for m in pan_metrics) if pan_metrics else None,"phone_travel_deg":(pan_metrics[-1]["joint_rad"]["phone_pan"]-pan_metrics[0]["joint_rad"]["phone_pan"])*180/math.pi if pan_metrics else 0},
        "parameters":{"gravity_m_s2":9.81,"timestep_s":timestep,"solver_iterations":150,"friction":args.friction,"effort_cap_nm":args.effort,"command_speed_cap_rad_s":1.0,"actual_velocity_hard_limited":False,"controller":args.controller,"finite_kp_nm_rad":finite_kp,"finite_kd_nm_s_rad":finite_kd,"position_gain":args.kp,"velocity_gain":1.0,"initial_joint_deg":[0,args.hip,args.knee],"stride_mm":args.stride,"com_shift_mm":args.shift,"lower_mm":args.lower,"lift_mm":args.lift,"free_base":True,"base_constraints":False},
        "observed":{"simulated_seconds":step_count*timestep,"advance_x_mm":advance_x*1000,"final_base_mm":final[0]*1000,"final_rpy_deg":np.degrees(final[2]),"final_com_mm":final[3]*1000,"max_roll_pitch_deg":max(np.max(np.abs(m["rpy_deg"][:2])) for m in metrics),"minimum_stand_margin_mm":min((m["support_margin_m"] or -1)*1000 for m in standing) if standing else None,"minimum_mid_swing_margin_mm":min((m["support_margin_m"] if m["support_margin_m"] is not None else -1)*1000 for m in swing_mid) if swing_mid else None,"maximum_stance_error_mm":max(m["stance_error_m"]*1000 for m in metrics),"dynamic_peak_joint_torque_nm":torque_peaks,"torque_saturation_fraction":saturation,"static_peak_joint_torque_nm":static_peak},
        "limitations":["Masses and inertias come from the explicit manifest model. Part-only extrusion estimates exclude support and skirt material; actual finished parts, hardware and wiring still require weighing.","This is a rigid-body dynamics calculation. Reduced gains and a position-feedback dead zone are uncertainty proxies, not a simulation or qualification of anisotropic printed stiffness, mechanical backlash, creep, stress, fatigue, fracture or fastener retention.","The 14 mm wide, 5 mm radius rocker contact cylinder omits the printed toe's small neutral flat. Contact depth differs by at most 0.2 mm. Friction is assumed; floor slip is not physically calibrated.","Simplified collision boxes do not validate self collision, fastener clearance, cable sweep or strength. Separate CAD checks are required.","Servo stiffness, damping and gravity compensation are assumed control behavior. The controller has capped torque and commanded speed. Hardware gains, backlash, bus delay, temperature and electrical supply have not been measured.","This run contains one slow crawl cycle on a level floor. It does not establish robust walking, recovery from disturbance or safety on stairs.","Continuous phone pan requires wireless communication and the phone internal battery; USB must be unplugged during rotation."],
    }
    (args.output/"simulation_report.json").write_text(json.dumps(plain(summary),indent=2)+"\n",encoding="utf-8")
    (args.output/"trajectory.json").write_text(json.dumps(plain({"joint_names":ordered,"units":"SI","frames":trajectory}),separators=(",",":"))+"\n",encoding="utf-8")
    (args.output/"static_screen.json").write_text(json.dumps(plain({"samples":static_samples}),separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps(plain({"status":summary["status"],"gates":summary["gates"],"mass_kg":summary["mass_kg"],"advance_mm":advance_x*1000,"max_static_torque_nm":max(static_peak.values()) if static_peak else None,"failure":failure})))
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--expected-manifest-sha256",help="Reject a manifest that differs from the explicitly frozen release identity")
    parser.add_argument("--output",type=Path,default=HERE/"output_r5")
    parser.add_argument("--hip",type=float,default=30)
    parser.add_argument("--knee",type=float,default=81)
    parser.add_argument("--stride",type=float,default=22)
    parser.add_argument("--minimum-advance",type=float,default=20)
    parser.add_argument("--shift",type=float,default=10)
    parser.add_argument("--lower",type=float,default=0)
    parser.add_argument("--lift",type=float,default=15)
    parser.add_argument("--effort",type=float,default=0.588)
    parser.add_argument("--friction",type=float,default=0.7)
    parser.add_argument("--kp",type=float,default=0.3)
    parser.add_argument("--controller",choices=["torque"],default="torque")
    parser.add_argument("--torque-gain-scale",type=float,default=1.0)
    parser.add_argument("--torque-damping-scale",type=float,default=0.1)
    parser.add_argument("--feedback-deadband-deg",type=float,default=0.0,help="Position-feedback dead-zone half width; an uncertainty proxy, not a mechanical backlash model")
    result=evaluate(parser.parse_args())
    sys.exit(0 if result["status"] in ("bounded_simulation_pass","experimental_rated_torque_pass") else 1)
