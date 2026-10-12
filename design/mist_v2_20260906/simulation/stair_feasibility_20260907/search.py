"""Bounded quasi-static screen. No physical controller or hardware connection.

Level body, horizontal treads, vertical contact forces, finite wheel/link clearance.
This checks necessary pose events; it does not infer a path from isolated poses.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
import model_snapshot as model

ROOT = Path(__file__).resolve().parent
P = model.load_parameters(ROOT / 'parameters_snapshot.json')
G, M, S, T = (P[k] for k in ['geometry', 'mass', 'servo', 'transmission'])
Q0 = model.neutral(P)
R = G['wheel_diameter_m'] / 2
HW = G['wheel_width_m'] / 2
RISE = P['environment']['step_rise_m']
TREAD = P['environment']['step_tread_m']
GRAV = P['environment']['gravity_m_s2']
TOTAL = model.total_mass(P)
STALL = S['stall_torque_nm'] * S['simulation_voltage_v'] / S['nominal_voltage_v']
CONT = min(S['continuous_fraction_of_stall'] * STALL, S['rated_torque_nm'])
PEAK = S['peak_fraction_of_stall'] * STALL
ETA = np.array(T['efficiency'])
A = model.coupling(P)
LIMITS = np.radians(G['joint_limits_deg'])
TRAVEL = np.array(T['motor_travel_limits_deg'])
BODY_M, BODY_C, _ = model.body_mass_properties(P)
SIGNS = np.array([1, -1, 1, -1])


def signed_free_distance(x, z, edge, top):
    """Distance outside an infinitely wide solid quadrant x>=edge,z<=top."""
    dx, dz = edge - x, z - top
    return np.hypot(np.maximum(dx, 0), np.maximum(dz, 0)) + np.minimum(np.maximum(dx, dz), 0)


def masses_and_gravity(i, q):
    f = model.fk(P, i, q)
    yaw_mass = M['yaw_carriage_without_servos_kg'] + M['proximal_servo_kg']
    fem = f['knee'] - f['pitch']
    tib = f['axle'] - f['knee']
    servo_fraction = abs(M['knee_servo_com_m'][2]) / G['femur_m']
    items = [(yaw_mass, (f['hip'] + f['pitch']) / 2),
             (M['femur_with_pulleys_kg'], f['pitch'] + .5 * fem),
             (M['proximal_servo_kg'], f['pitch'] + servo_fraction * fem),
             (M['tibia_with_carrier_kg'], f['knee'] + .5 * tib),
             (M['wheel_motor_with_mount_kg'], f['knee'] + .9 * tib),
             (M['wheel_hub_and_tire_kg'], f['axle'])]
    # dU/dq for exact point masses above, in the frozen level-body geometry.
    h, k = q[1:]
    l1, l2 = G['femur_m'], G['tibia_m']
    distal = M['tibia_with_carrier_kg'] + M['wheel_motor_with_mount_kg'] + M['wheel_hub_and_tire_kg']
    fem_weighted = (.5 * M['femur_with_pulleys_kg'] + servo_fraction * M['proximal_servo_kg'] + distal) * l1
    tib_weighted = (.5 * M['tibia_with_carrier_kg'] + .9 * M['wheel_motor_with_mount_kg'] + M['wheel_hub_and_tire_kg']) * l2
    grav_tau = GRAV * np.array([0, fem_weighted * np.sin(h) + tib_weighted * np.sin(h+k), tib_weighted * np.sin(h+k)])
    jz = np.array([0, l1 * np.sin(h) + l2 * np.sin(h+k), l2 * np.sin(h+k)])
    return items, grav_tau, jz, f


def evaluate(x, treads, swing=None, crossing=False, peak=False, details=False, guarded=False, touchdown=False):
    body = np.array(x[:3])
    xy = np.array(x[3:11]).reshape(4, 2)
    feet = np.column_stack([xy, np.array(treads) * RISE + R])
    if swing is not None:
        feet[swing, 2] = x[11]
    qs, fs, grav, jzs, constraints, weights = [], [], [], [], [], [(BODY_M, body + BODY_C)]
    for i in range(4):
        q, ok = model.ik(P, i, feet[i] - body)
        qs.append(q)
        items, gt, jz, f = masses_and_gravity(i, q)
        fs.append({k: body + v if isinstance(v, np.ndarray) and k != 'wheel_axis' else v for k, v in f.items()})
        weights.extend((w, body + pos) for w, pos in items)
        grav.append(gt)
        jzs.append(jz)
        error = np.linalg.norm(body + f['axle'] - feet[i])
        constraints.extend([(1e-6-error)*100, *(q-LIMITS[:, 0]), *(LIMITS[:, 1]-q)])
        travel = np.degrees(A @ (q-Q0[i]))
        constraints.extend((travel-TRAVEL[:, 0])/50)
        constraints.extend((TRAVEL[:, 1]-travel)/50)
    qs, grav, jzs = np.array(qs), np.array(grav), np.array(jzs)
    com = sum(w * pos for w, pos in weights) / TOTAL
    support = [i for i in range(4) if i != swing]
    # The fourth force is a search variable only during four-contact support.
    forces = np.zeros(4)
    matrix = np.stack([np.ones(len(support)), feet[support, 0], feet[support, 1]])
    rhs = TOTAL * GRAV * np.array([1, com[0], com[1]])
    if len(support) == 4:
        forces[3] = x[11]
        rhs -= matrix[:, 3] * forces[3]
        matrix = matrix[:, :3]
        solved = support[:3]
    else:
        solved = support
    try:
        forces[solved] = np.linalg.solve(matrix, rhs)
    except np.linalg.LinAlgError:
        forces[solved] = -1000
    # A 1 N minimum load avoids a solution resting exactly on a support edge.
    constraints.extend((forces[support] - 1) / 30)
    torques = np.array([np.linalg.solve(A.T, grav[i] - jzs[i]*forces[i]) / ETA for i in range(4)])
    limit = PEAK if peak else CONT
    constraints.extend(((limit - abs(torques)) / limit).ravel())
    col = []
    # Cylinder body against the floor and successive vertical risers. An AABB
    # for its x/z projection is exact for a level vertical cylinder.
    bottom = body[2] - G['hip_mount_height_above_body_bottom_m']
    col.append(bottom - .005)
    for j in range(3):
        col.append(max(j*TREAD - body[0] - G['body_diameter_m']/2, bottom-(j+1)*RISE) - .005)
    for i, f in enumerate(fs):
        theta = f['heading']
        # Sample cylinder rim, both sidewalls, and central disc. Plane-specific
        # sampling error is <R*(1-cos(pi/64)) = 0.052 mm, padded by 0.06 mm.
        angles = np.linspace(0, 2*np.pi, 129)
        axis = np.array([math.sin(theta), -math.cos(theta), 0])
        radial = np.array([math.cos(theta), math.sin(theta), 0])
        wheel = np.concatenate([f['axle'] + off*axis + R*(np.cos(angles)[:, None]*radial + np.sin(angles)[:, None]*np.array([0, 0, 1])) for off in [-HW, 0, HW]])
        col.append(float(wheel[:, 2].min()) + 1e-7)
        for j in range(3):
            # Contact with its assigned tread has zero clearance by definition.
            contact = i != swing and treads[i] == j+1
            contact = contact or (i == swing and touchdown and abs(feet[i,2]-((j+1)*RISE+R)) < 1e-9)
            pad = 0 if contact else .00006
            col.append(float(signed_free_distance(wheel[:, 0], wheel[:, 2], j*TREAD, (j+1)*RISE).min()) - pad)
        # Conservative capsule around each 24x18 mm link, sampled each 5 mm.
        # The half sample spacing is added to avoid an unexamined gap.
        for start, end, radius in [(f['pitch'], f['knee'], .015), (f['knee'], f['axle'], .015)]:
            n = max(2, math.ceil(np.linalg.norm(end-start)/.005)+1)
            pts = np.linspace(start, end, n)
            col.append(float(pts[:, 2].min()) - radius)
            for j in range(3):
                col.append(float(signed_free_distance(pts[:, 0], pts[:, 2], j*TREAD, (j+1)*RISE).min()) - radius - .0025)
        # Yaw carriage below the hip plane. This is a coarse box envelope,
        # intentionally independent of the moving CAD assembly.
        centre = (f['hip'] + f['pitch'])/2
        halfx = .0325*abs(math.cos(theta)) + .03*abs(math.sin(theta))
        for j in range(3):
            col.append(max(j*TREAD-centre[0]-halfx, centre[2]-.0225-(j+1)*RISE)-.0025)
    constraints.extend(np.array(col)*20)
    if crossing:
        constraints.extend([(.0001-abs(feet[swing, 0]))*100, (feet[swing, 2]-(RISE+R+.015))*50])
    hull = ConvexHull(feet[support, :2])
    support_margin = float(-(hull.equations[:, :2] @ com[:2] + hull.equations[:, 2]).max())
    if guarded:
        constraints.append((support_margin-.015)*20)
        constraints.extend(((limit*.9-abs(torques))/limit).ravel())
        constraints.extend((qs-LIMITS[:, 0]-np.radians(2)).ravel())
        constraints.extend((LIMITS[:, 1]-qs-np.radians(2)).ravel())
        travel = np.degrees((A @ (qs-Q0).T).T)
        constraints.extend(((travel-TRAVEL[:, 0]-5)/50).ravel())
        constraints.extend(((TRAVEL[:, 1]-travel-5)/50).ravel())
    cons = np.array(constraints)
    if not details:
        return cons
    return dict(body_m=body.tolist(), feet_m=feet.tolist(), q_deg=np.degrees(qs).tolist(),
                motor_offset_deg=np.degrees((A @ (qs-Q0).T).T).tolist(),
                com_m=com.tolist(), support_legs=support, vertical_forces_n=forces.tolist(),
                motor_torque_nm=torques.tolist(), max_motor_torque_nm=float(abs(torques).max()),
                continuous_limit_nm=CONT, peak_limit_nm=PEAK, support_margin_m=support_margin,
                min_geometry_clearance_m=float(min(col)), min_scaled_constraint=float(cons.min()),
                feasible=bool(cons.min() >= -1e-5), x=np.array(x).tolist())


def run_case(name, treads, swing, crossing, peak, attempts=12, seed=6907, guarded=False):
    rng = np.random.default_rng(seed)
    has_lower_support = any(level == 0 and i != swing for i, level in enumerate(treads))
    bounds = [(-.23, .19), (-.095, .095), (.205, .309 if has_lower_support else .489)]
    for i, level in enumerate(treads):
        xb = (-.33, -.047) if level == 0 else (.025, .218)
        if crossing and i == swing:
            xb = (-1e-8, 1e-8)
        bounds.extend([xb, (.105, .27) if SIGNS[i] == 1 else (-.27, -.105)])
    bounds.append((RISE+R+.015, .31) if swing is not None else (1, TOTAL*GRAV-3))
    best = None
    trials = []
    for attempt in range(attempts):
        x0 = np.array([rng.uniform(lo, hi) for lo, hi in bounds])
        x0[:3] = [rng.uniform(-.14, .06), rng.uniform(-.055, .055), rng.uniform(.245, .295)]
        x0[11] = .255 if swing is not None else TOTAL*GRAV/4
        def residual(x):
            c = evaluate(x, treads, swing, crossing, peak, guarded=guarded)
            return float(np.dot(np.minimum(c, 0), np.minimum(c, 0)))
        result = minimize(residual, x0, method='L-BFGS-B', bounds=bounds,
                          options={'maxiter': 260, 'ftol': 1e-13, 'maxls': 25})
        val = residual(result.x)
        details = evaluate(result.x, treads, swing, crossing, peak, True, guarded)
        trials.append(dict(attempt=attempt, objective=val, success=bool(result.success), feasible=details['feasible']))
        if best is None or val < best['objective']:
            best = dict(objective=val, result=details)
        print(name, attempt, round(val, 7), round(details['min_scaled_constraint'], 5), flush=True)
        if details['feasible']:
            break
    output = dict(name=name, treads=treads, swing=swing, crossing=crossing, torque_budget='peak' if peak else 'continuous',
                  guarded=guarded, bounds=bounds, trials=trials, **best)
    destination = ROOT / (name+'.json')
    if destination.exists():
        from datetime import datetime
        destination = ROOT / (name+'_'+datetime.now().strftime('%H%M%S%f')+'.json')
    destination.write_text(json.dumps(output, indent=2))
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', default='bridge')
    parser.add_argument('--peak', action='store_true')
    parser.add_argument('--attempts', type=int, default=10)
    parser.add_argument('--guarded', action='store_true')
    args = parser.parse_args()
    specs = {'bridge': ([1, 1, 0, 0], None, False),
             'first_front_crossing': ([0, 0, 0, 0], 0, True),
             'second_front_crossing': ([1, 0, 0, 0], 1, True),
             'first_rear_crossing': ([1, 1, 0, 0], 2, True),
             'last_rear_crossing': ([1, 1, 1, 0], 3, True)}
    provenance = dict(parameters_sha256=hashlib.sha256((ROOT/'parameters_snapshot.json').read_bytes()).hexdigest(),
                      model_sha256=hashlib.sha256((ROOT/'model_snapshot.py').read_bytes()).hexdigest(),
                      mass_kg=TOTAL, continuous_nm=CONT, peak_nm=PEAK,
                      scope='Necessary static event search only; isolated feasible events do not establish a connected path.')
    (ROOT/'provenance.json').write_text(json.dumps(provenance, indent=2))
    print(json.dumps(run_case(args.case+('_peak' if args.peak else '')+('_guarded' if args.guarded else ''), *specs[args.case], args.peak, args.attempts, guarded=args.guarded)['result'], indent=2))
