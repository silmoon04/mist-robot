"""Servo-only inward A/B mass study. Does not modify production or run dynamics."""
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
DESIGN=HERE.parents[1]
sys.path.insert(0,str(DESIGN/"simulation"))
from kinematics import LEGS, crawl_plan, sample_phase
from statics import center_of_mass, link_frames, loads

MANIFEST=DESIGN/"cad/output/assembly_manifest_as_printed.json"
TRAJECTORY=DESIGN/"simulation/output_r3_printed_nominal/trajectory.json"
REPORT=DESIGN/"simulation/output_r3_printed_nominal/simulation_report.json"
G=9.81
LEGACY_D=.02023
CANONICAL_D=.025
KNEE=np.array([.09,0,0])
Q=np.diag([-1.0,1.0,-1.0])


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tensor(d):
    return np.array([[d['ixx'],d['ixy'],d['ixz']],[d['ixy'],d['iyy'],d['iyz']],[d['ixz'],d['iyz'],d['izz']]],dtype=float)


def terms(a):
    return {k:float(a[i,j]) for k,i,j in [('ixx',0,0),('iyy',1,1),('izz',2,2),('ixy',0,1),('ixz',0,2),('iyz',1,2)]}


def parallel_axis(m,r):return m*(np.dot(r,r)*np.eye(3)-np.outer(r,r))


def aggregate_parts(data):
    for link in data['links']:
        parts=[p for p in data['parts'] if p['link']==link]
        mass=sum(p['mass_kg'] for p in parts)
        com=sum(p['mass_kg']*np.asarray(p['com_mm'])/1000 for p in parts)/mass
        inertia=sum(tensor(p['inertia_kg_m2'])+parallel_axis(p['mass_kg'],np.asarray(p['com_mm'])/1000-com) for p in parts)
        data['links'][link].update(mass_kg=mass,com_mm=(com*1000).tolist(),inertia_kg_m2=terms(inertia))


def changed_model(original,mode):
    data=copy.deepcopy(original)
    changes={}
    for leg in LEGS:
        part=next(p for p in data['parts'] if p['name']==f'{leg}_servo_knee')
        old=np.asarray(part['com_mm'])/1000
        old_i=tensor(part['inertia_kg_m2'])
        new=old+np.array([-LEGACY_D,0,0]) if mode=='historical_translation_20_23_mm' else KNEE+Q@(old-KNEE)
        new_i=old_i if mode=='historical_translation_20_23_mm' else Q@old_i@Q.T
        part['com_mm']=(new*1000).tolist()
        part['inertia_kg_m2']=terms(new_i)
        changes[leg]={'mass_kg':part['mass_kg'],'old_com_m':old,'new_com_m':new,'old_i':old_i,'new_i':new_i,'delta_m':new-old}
    aggregate_parts(data)
    return data,changes


def canonical_outward_reference(production):
    reference=copy.deepcopy(production)
    for leg in LEGS:
        part=next(p for p in reference['parts'] if p['name']==f'{leg}_servo_knee')
        part['com_mm'][0]=102.5
        part['com_mm'][2]=0.0
    aggregate_parts(reference)
    return reference


def world_tensor(data,frames,about):
    result=np.zeros((3,3))
    for link,(origin,rotation) in frames.items():
        item=data['links'][link]
        center=origin+rotation@(np.asarray(item['com_mm'])/1000)
        result+=rotation@tensor(item['inertia_kg_m2'])@rotation.T+parallel_axis(item['mass_kg'],center-about)
    return result


def quaternion_matrix(q):
    x,y,z,w=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def plain(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {k:plain(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [plain(v) for v in value]
    return value


def main():
    inputs={str(p.relative_to(DESIGN)):sha(p) for p in [MANIFEST,TRAJECTORY,REPORT,DESIGN/'settings.json',DESIGN/'simulation/kinematics.py',DESIGN/'simulation/statics.py']}
    production=json.loads(MANIFEST.read_text())
    report=json.loads(REPORT.read_text())
    recorded=json.loads(TRAJECTORY.read_text())['frames']
    if report['inputs']['manifest_sha256']!=sha(MANIFEST):raise ValueError('Study manifest does not match the recorded production test')
    mass=sum(x['mass_kg'] for x in production['links'].values())
    neutral={leg:np.radians([0,30,81]) for leg in LEGS}
    neutral_frames,neutral_axes=link_frames(np.zeros(3),neutral)
    cases=[]
    for mode in ['canonical_case_center_half_turn_25_mm','historical_translation_20_23_mm','historical_invalid_envelope_half_turn_y']:
        baseline=canonical_outward_reference(production) if mode.startswith('canonical') else production
        com_before,_,_=center_of_mass(baseline,neutral_frames)
        inertia_before=world_tensor(baseline,neutral_frames,com_before)
        modified,changes=changed_model(baseline,mode)
        com_after,_,_=center_of_mass(modified,neutral_frames)
        inertia_after=world_tensor(modified,neutral_frames,com_after)
        hip_deltas=[]
        xy_shifts=[]
        z_shifts=[]
        yaw_axis_deltas=[]
        hip_inertia_deltas=[]
        neutral_direct=[]
        leg_yaw_before_after=[]
        hip_subtree_before_after=[]
        for leg,change in changes.items():
            origin,rotation=neutral_frames[f'femur_{leg}']
            axis=neutral_axes[leg][1][1]
            delta=rotation@change['delta_m']
            neutral_direct.append(float(-np.dot(axis,np.cross(delta,np.array([0,0,-change['mass_kg']*G])))))
            old=origin+rotation@change['old_com_m']
            new=origin+rotation@change['new_com_m']
            yaw_origin=neutral_frames[f'coxa_{leg}'][0]
            old_tensor=rotation@change['old_i']@rotation.T+parallel_axis(change['mass_kg'],old-yaw_origin)
            new_tensor=rotation@change['new_i']@rotation.T+parallel_axis(change['mass_kg'],new-yaw_origin)
            yaw_axis_deltas.append(float((new_tensor-old_tensor)[2,2]))
            old_h=change['old_i']+parallel_axis(change['mass_kg'],change['old_com_m'])
            new_h=change['new_i']+parallel_axis(change['mass_kg'],change['new_com_m'])
            hip_inertia_deltas.append(float((new_h-old_h)[1,1]))
            subtree={name:neutral_frames[name] for name in (f'coxa_{leg}',f'femur_{leg}',f'tibia_{leg}')}
            leg_yaw_before_after.append([float(world_tensor(model,subtree,yaw_origin)[2,2]) for model in (baseline,modified)])
            hip_subtree={name:neutral_frames[name] for name in (f'femur_{leg}',f'tibia_{leg}')}
            hip_subtree_before_after.append([float(axis@world_tensor(model,hip_subtree,origin)@axis) for model in (baseline,modified)])
        for frame in recorded:
            if frame['phase'] in ('stand','phone_pan'):continue
            angles={leg:np.array([frame['joint_rad'][f'{kind}_{leg}'] for kind in ('yaw','hip','knee')]) for leg in LEGS}
            frames,axes=link_frames(np.zeros(3),angles)
            body_rotation=quaternion_matrix(frame['base_quat_xyzw'])
            whole_delta=np.zeros(3)
            for leg,change in changes.items():
                rotation=body_rotation@frames[f'femur_{leg}'][1]
                delta=rotation@change['delta_m']
                axis=body_rotation@axes[leg][1][1]
                hip_deltas.append(float(-np.dot(axis,np.cross(delta,[0,0,-change['mass_kg']*G]))))
                whole_delta+=change['mass_kg']*delta/mass
            xy_shifts.append(float(np.linalg.norm(whole_delta[:2])*1000))
            z_shifts.append(float(whole_delta[2]*1000))
        same_pose=[]
        params=report['parameters']
        plan=crawl_plan(params['stride_mm']/1000,params['com_shift_mm']/1000,params['lower_mm']/1000,params['lift_mm']/1000,np.radians(params['initial_joint_deg']))
        for phase in plan:
            for fraction in np.linspace(0,1,41):
                desired_base,feet=sample_phase(phase,float(fraction))
                support=[leg for leg in LEGS if not(phase['kind']=='swing' and leg==phase['leg'])]
                old=loads(baseline,desired_base,feet,support)
                new=loads(modified,old['base'],feet,support,correct_com=False)
                same_pose.append({'old':old['torques'],'new':new['torques'],'support':support,'com_delta_mm':(new['com']-old['com'])*1000})
        supported_deltas=[new['new'][f'hip_{leg}']-new['old'][f'hip_{leg}'] for new in same_pose for leg in new['support']]
        knee_deltas=[new['new'][f'knee_{leg}']-new['old'][f'knee_{leg}'] for new in same_pose for leg in new['support']]
        overall_peaks=[max((abs(value),joint) for sample in same_pose for joint,value in sample[kind].items()) for kind in ('old','new')]
        cases.append({
            'case':mode,
            'interpretation':'Corrected case-center reference; actual internal COM unmeasured' if mode.startswith('canonical') else 'Historical invalid-datum premise; do not use as the corrected hardware reference',
            'mass_change_kg':sum(x['mass_kg'] for x in modified['links'].values())-mass,
            'servo_com_reference_x_mm_before_after':[changes['FL']['old_com_m'][0]*1000,changes['FL']['new_com_m'][0]*1000],
            'inward_com_shift_mm':-changes['FL']['delta_m'][0]*1000,
            'neutral_self_weight_moment_magnitude_reduction_nm_per_leg':neutral_direct[0],
            'neutral_fixed_foot_load_actuator_hip_torque_change_nm_per_leg':neutral_direct[0],
            'direct_knee_gravity_change_nm':0.0,
            'neutral_whole_com_change_mm':(com_after-com_before)*1000,
            'neutral_whole_polar_inertia_before_after_kg_m2':[inertia_before[2,2],inertia_after[2,2]],
            'neutral_whole_polar_inertia_change_percent':100*(inertia_after[2,2]/inertia_before[2,2]-1),
            'neutral_leg_yaw_axis_inertia_change_kg_m2_per_leg':yaw_axis_deltas[0],
            'neutral_hip_axis_inertia_change_kg_m2_per_leg':hip_inertia_deltas[0],
            'neutral_leg_yaw_subtree_inertia_before_after_kg_m2':leg_yaw_before_after[0],
            'neutral_leg_yaw_subtree_inertia_change_percent':100*(leg_yaw_before_after[0][1]/leg_yaw_before_after[0][0]-1),
            'neutral_hip_subtree_inertia_before_after_kg_m2':hip_subtree_before_after[0],
            'neutral_hip_subtree_inertia_change_percent':100*(hip_subtree_before_after[0][1]/hip_subtree_before_after[0][0]-1),
            'recorded_gait_direct_hip_torque_change_range_nm':[min(hip_deltas),max(hip_deltas)],
            'recorded_gait_whole_com_horizontal_shift_max_mm':max(xy_shifts),
            'recorded_gait_whole_com_vertical_shift_range_mm':[min(z_shifts),max(z_shifts)],
            'fixed_pose_static_rebalanced_stance_hip_torque_change_range_nm':[min(supported_deltas),max(supported_deltas)],
            'fixed_pose_static_rebalanced_stance_knee_torque_change_range_nm':[min(knee_deltas),max(knee_deltas)],
            'fixed_pose_static_peak_absolute_hip_before_after_nm':[max(abs(s[key]) for r in same_pose for key in r['old'] if key.startswith('hip_') for s in [r['old']]),max(abs(s[key]) for r in same_pose for key in r['new'] if key.startswith('hip_') for s in [r['new']])],
            'fixed_pose_static_peak_any_joint_before_after':[{'joint':joint,'absolute_torque_nm':value} for value,joint in overall_peaks],
        })
    cap=next(p for p in production['parts'] if p['name']=='FL_case_cap_knee')
    main_part=next(p for p in production['parts'] if p['name']=='FL_femur_main_and_knee_saddle')
    result={
        'scope':'A/B analysis only. Production geometry, mass manifests, gait and controller remain unchanged. No dynamics, clearance or printing validation of an inward candidate was run.',
        'baseline_mass_kg':mass,
        'baseline_model':production['mass_model'],
        'input_hashes':inputs,
        'corrected_case_geometry':{'case_ends_mm':[-35.115,10.115],'case_center_to_shaft_mm':12.5,'case_center_reversal_mm':25.0,'source':'Corrected manufacturer drawing interpretation, confirmed by root against supplier STEP within 0.0033 mm'},
        'canonical_reference_scope':'Rebase the four knee-case assumed COMs to outward femur X102.5 mm, then inward X77.5 mm. Keep their 55g masses and registered intrinsic tensors. Other motors, clamps and structure stay at the frozen R3 values to isolate this A/B change. This is not a corrected production manifest.',
        'superseded_datum':'The previous 20.23mm reversal and registered-envelope 19.718mm reversal used the incorrect case pocket datum. Retained only as historical calculations.',
        'historical_invalid_registered_envelope_center_offset_mm':next(p for p in production['parts'] if p['name']=='FL_servo_knee')['com_mm'][0]-90,
        'formulas':{
            'case_self_weight_moment_reduction':'m*g*d*cos(hip), for a pure inward femur-X translation and level body',
            'loaded_stance_sign':'Required hip torque = upward foot reaction moment minus distal self-weight moment. Reducing case self-weight moment increases required positive stance torque if foot load is held fixed.',
            'whole_com':'Sum(m_i * world_delta_i) / whole_robot_mass',
            'polar_translation':'Delta Izz = m * (new_x^2 + new_y^2 - old_x^2 - old_y^2), plus any rotated intrinsic-tensor change',
        },
        'cases':cases,
        'clamp_mass_pending':{
            'detachable_printed_knee_cap_mass_kg_per_leg':cap['mass_kg'],
            'integrated_femur_main_and_saddle_mass_kg_per_leg':main_part['mass_kg'],
            'same_translation_moment_magnitude_per_additional_10g_nm':.010*G*CANONICAL_D*math.cos(math.radians(30)),
            'cap_only_if_same_translation_moment_magnitude_nm':cap['mass_kg']*G*CANONICAL_D*math.cos(math.radians(30)),
            'note':'Old R3 clamp masses are a scale reference only. The integrated main part is not all movable clamp mass. Corrected clamp, cap, bridge and fastener changes require candidate geometry and new deposited properties. The cap-only figure assumes a pure 25mm translation and is not a full-candidate result.',
        },
        'limitations':['The 55g servo mass is specified hardware mass. Its actual internal COM and inertia are unmeasured; the canonical study assumes COM at the corrected case center and retains the registered intrinsic tensor.','The old 20.23mm and 19.718mm calculations are invalid-datum historical results, not alternate corrected hardware values.','Only knee-case reference properties are rebased in memory; production geometry and the other components remain untouched.','Whole-body COM remains symmetric horizontally only at matching leg poses.','Static rebalancing holds body and feet fixed and adjusts vertical support forces. It is not a new gait or a dynamic test.','No appearance, collision, connector-clearance, assembly or strength pass is inferred from these mass calculations.'],
    }
    if inputs!={str(p.relative_to(DESIGN)):sha(p) for p in [MANIFEST,TRAJECTORY,REPORT,DESIGN/'settings.json',DESIGN/'simulation/kinematics.py',DESIGN/'simulation/statics.py']}:raise ValueError('Production input changed during A/B study')
    result['inputs_unchanged']=True
    result['study_script_sha256']=sha(__file__)
    (HERE/'mass_tradeoff.json').write_text(json.dumps(plain(result),indent=2)+'\n',encoding='utf-8')
    a=cases[0]
    prose=f"""# Knee inward mass tradeoff

The corrected drawing places the case center **12.5 mm from the shaft**, with case ends **−35.115 and +10.115 mm**. Reversing it moves the case center **25 mm**. The old 20.23 mm figure used an incorrect datum and is retained only as historical data in the JSON.

This A/B reference assumes each 55 g case's COM is at that corrected case center: femur X102.5 mm outward and X77.5 mm inward. Actual internal servo COM remains unmeasured. The four knee-case references are rebased in memory; other components stay at frozen R3 values. Model mass remains {mass:.6f} kg, with no production edits or dynamics rerun.

For that 25 mm reversal at a 30° hip angle, the case's own gravity moment decreases by **{a['neutral_self_weight_moment_magnitude_reduction_nm_per_leg']:.6f} N·m per leg**, about 2.0% of the 0.588 N·m screening cap. An unsupported leg requires less self-weight holding torque. In a loaded stance, the case weight opposes the upward foot reaction, so unchanged foot load requires **more** positive hip torque by that amount. The case belongs to the femur, so there is no direct knee gravity change.

At the symmetric 30°/81° pose, the four horizontal shifts cancel and whole-robot COM rises by **{a['neutral_whole_com_change_mm'][2]:.3f} mm**. The polar inertia about the central vertical axis decreases by **{-a['neutral_whole_polar_inertia_change_percent']:.2f}%**, using the complete registered mass model. This can reduce inertia during yaw acceleration, but it does not establish a walking-energy or servo-temperature improvement.

Across the saved nominal gait, the direct per-leg hip holding-torque change is **{min(a['recorded_gait_direct_hip_torque_change_range_nm']):.6f} to {max(a['recorded_gait_direct_hip_torque_change_range_nm']):.6f} N·m**. Maximum horizontal whole-COM movement is **{a['recorded_gait_whole_com_horizontal_shift_max_mm']:.3f} mm**. A separate fixed-pose gravity calculation allowing support-force redistribution changes the peak absolute hip load from **{a['fixed_pose_static_peak_absolute_hip_before_after_nm'][0]:.6f} to {a['fixed_pose_static_peak_absolute_hip_before_after_nm'][1]:.6f} N·m**. That calculation is not a dynamic rerun.

The largest existing gravity-load screen is at {a['fixed_pose_static_peak_any_joint_before_after'][0]['joint']}, which changes from **{a['fixed_pose_static_peak_any_joint_before_after'][0]['absolute_torque_nm']:.6f} to {a['fixed_pose_static_peak_any_joint_before_after'][1]['absolute_torque_nm']:.6f} N·m** after the small support-force redistribution. Direct knee gravity from the case is still zero. At the neutral pose, the complete moving leg's yaw inertia falls by **{-a['neutral_leg_yaw_subtree_inertia_change_percent']:.2f}%**, and its hip subtree inertia falls by **{-a['neutral_hip_subtree_inertia_change_percent']:.2f}%**.

For scale only, the old R3 detachable cap is {cap['mass_kg']*1000:.3f} g per leg. A pure 25 mm translation would add another {result['clamp_mass_pending']['cap_only_if_same_translation_moment_magnitude_nm']:.6f} N·m of moment change. The {main_part['mass_kg']*1000:.3f} g integrated femur-and-saddle part includes structural material that cannot all be treated as a moving clamp. A complete case-plus-clamp comparison awaits corrected candidate geometry and mass properties.

The static load changes are small, and the robot keeps the same weight. Appearance, connector clearance, hardware access and the complete inward geometry still need their own review.
"""
    (HERE/'mass_tradeoff.md').write_text(prose,encoding='utf-8')
    (HERE/'mass_tradeoff.txt').write_text(prose,encoding='utf-8')
    print(json.dumps(plain({'mass_kg':mass,'cases':cases,'clamp_mass_pending':result['clamp_mass_pending']}),indent=2))


if __name__=='__main__':main()
