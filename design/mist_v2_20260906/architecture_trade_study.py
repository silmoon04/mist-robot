"""Compare proximal knee motor frames at equal mass and endpoint load."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'simulation'/'analytic'))
import analytic as a

def run():
    p=json.loads((ROOT/'simulation/parameters.json').read_text())
    g=p['geometry']; lengths=(g['femur_m'],g['tibia_m']); offsets=(g['hip_radial_offset_m'],g['hip_transverse_offset_m'])
    neutral=a.ik_planar(g['drive_radial_reach_from_pitch_m'],g['hip_to_wheel_axle_height_m'],lengths)
    cases=[]
    for mass in [a.total_mass(p),5.2]:
        for name,contacts,factor in [('four_static',4,1),('three_static',3,1),('two_dynamic_1p5',2,1.5)]:
            force=np.array([0.,0.,mass*9.81*factor/contacts])
            original_load=a.jacobian(neutral,lengths,offsets).T@force+a.leg_gravity(neutral,lengths,offsets,p)
            for mode,ratios in [('absolute_tibia',[2,2,2]),('absolute_tibia',[2,3.5,2]),('joint_relative_ideal',[2,2,2])]:
                load=original_load.copy()
                if mode=='joint_relative_ideal':
                    # Same servo moves from carriage to 40mm down the femur.
                    load+=a.jacobian(neutral,(.040,0),offsets).T@np.array([0,0,-.055*9.81])
                torque=a.motor_torque(load,a.transmission(mode,ratios),p['transmission']['efficiency'])
                stall,speed,continuous,peak=a.servo_limits(9.9,p)
                cases.append(dict(mass_kg=mass,load_case=name,force_n=force.tolist(),mode=mode,ratios=ratios,
                                  motor_torque_nm=torque.tolist(),worst_continuous_ratio=float(max(abs(torque))/continuous),
                                  worst_peak_ratio=float(max(abs(torque))/peak),
                                  moving_servo_distance_m=.04 if mode=='joint_relative_ideal' else 0))
    result=dict(status='equal_mass_nominal_pose_architecture_comparison_not_gait_or_CAD_validation',
                parameters_sha256=hashlib.sha256((ROOT/'simulation/parameters.json').read_bytes()).hexdigest(),
                pose_deg=np.degrees(neutral).tolist(),cases=cases,
                caveats=['5.2kg is an illustrative heavier-CAD sensitivity, not a final mass measurement.',
                         'No credit is taken for deleting remote-shaft bearings, gears or frame material.',
                         'Moving-motor inertia, mounting clearance, belt routing and cable motion are not modeled.',
                         'Only one pose and vertical force are compared; horizontal traction and full stair/gait loads can dominate.'])
    (ROOT/'architecture_trade_study.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    lines=['# Knee-drive frame trade study', '',
           'The fully carriage-mounted knee drive has a torque penalty at the hip because it controls the absolute tibia angle. Mounting the knee motor on the first 40 mm of the femur changes that reaction path. The motor remains near the hip but moves with the upper leg. This is an architectural alternative allowed by the requested weight/complexity tradeoff; it is not yet a fitted CAD revision.', '',
           'For the current remote architecture, `sK = rK*(h+k)` and hip motor torque is `(tauH-tauK)/rH` before losses. For a motor mounted to the femur driving a belt referenced to that same femur, `sK = rK*k`; hip motor torque becomes `tauH/rH`. This change comes from where the motor housing reacts torque. It cannot be obtained by changing the software matrix while keeping the old hardware.', '',
           'This comparison holds total mass and endpoint force constant, moves one existing 55 g servo from the yaw carriage to 40 mm down the femur, and adds its static gravity contribution. The 3.95376 kg case uses the existing assumptions. The 5.2 kg case illustrates the upward mass pressure seen in the first actual leg CAD. Neither value is a measured robot weight.', '',
           '| Mass | Load | Architecture / ratios | Yaw / hip / knee motor demand | Worst peak utilization at 9.9 V |',
           '|---|---|---|---:|---:|']
    for r in cases:
        if r['load_case'] not in ('three_static','two_dynamic_1p5'):continue
        mode='carriage-mounted' if r['mode']=='absolute_tibia' else 'proximal-femur-mounted'
        torques=' / '.join(f'{abs(v):.3f}' for v in r['motor_torque_nm'])
        lines.append(f"| {r['mass_kg']:.3f} kg | {r['load_case']} | {mode}, {'/'.join(map(str,r['ratios']))} | {torques} N m | {100*r['worst_peak_ratio']:.1f}% |")
    lines+=['', 'A bare 55 g motor at 40 mm adds at most about 0.022 N m gravity moment about the hip. It also adds approximately 0.000088 kg m2 point-mass inertia, before its own rotational inertia and mount. These costs need comparison with the deleted transmission shafts, supports and frame. A motor at the distal knee would cost considerably more in swing inertia, and is not the same alternative.', '',
            'The relative-knee row is an ideal kinematic case grounded in a possible motor mounting frame. It does not establish that the servo, output support, reduction and belt fit the femur. Shaft support and belt tension remain necessary, even if the large opposing trunnion arrangement is removed. The body shell, knee pulley size, electrical routing and all moving clearances must be redesigned together.', '',
            'No gait, thermal duty or stair success is inferred from these nominal-pose torque numbers. The existing simulations remain attached to the carriage-mounted architecture. A new URDF and mass distribution are required before using the alternative as the robot design.', '',
            'Reproduce with `python architecture_trade_study.py` in an environment with NumPy. The source uses the existing analytically reviewed Jacobian and virtual-work transform.']
    (ROOT/'architecture_trade_study.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(result['cases'][-3:],indent=2))

if __name__=='__main__':run()
