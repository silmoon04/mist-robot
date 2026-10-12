"""Kinematic and quasistatic crawl screen. No physics or hardware commands."""
from pathlib import Path
import itertools
import json
import sys

import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[1]
sys.path.insert(0, str(SIM))
from model import body_mass_properties, coupling, fk, ik, load_parameters, mount, neutral, rotation_z, total_mass, transverse, validate_link_mass_properties


def ryminus(q):
    return np.array([[np.cos(q), 0, -np.sin(q)], [0, 1, 0], [np.sin(q), 0, np.cos(q)]])


def com(p, q, wheel_angles=None):
    """Return the robot COM in the body frame.

    Explicit per-link COMs are local to the URDF link frames. A 4x4 state can
    include wheel joint angles; a 4x3 state defaults them to zero unless supplied
    separately. Wheel angles matter for an off-axis wheel COM.
    """
    q = np.asarray(q, dtype=float)
    if q.shape not in ((4, 3), (4, 4)) or not np.isfinite(q).all():
        raise ValueError('Expected finite joint angles with shape 4x3 or 4x4')
    if wheel_angles is not None and q.shape == (4, 4):
        raise ValueError('Supply wheel angles in q or separately, not both')
    wheels = np.asarray(q[:, 3] if q.shape == (4, 4) else
                        (np.zeros(4) if wheel_angles is None else wheel_angles), dtype=float)
    if wheels.shape != (4,) or not np.isfinite(wheels).all():
        raise ValueError('Expected four finite wheel joint angles')
    if p.get('link_mass_properties'):
        validate_link_mass_properties(p)
        properties = p['link_mass_properties']
        base = properties['base_link']
        points = [(float(base['mass_kg']), np.asarray(base['com_m'], dtype=float))]
        for i, name in enumerate(p['geometry']['leg_names']):
            f = fk(p, i, q[i])
            r = rotation_z(f['heading'])
            for suffix, origin, rotation in (
                ('_yaw', f['hip'], r),
                ('_femur', f['pitch'], r @ ryminus(q[i, 1])),
                ('_tibia', f['knee'], r @ ryminus(q[i, 1] + q[i, 2])),
                ('_wheel', f['axle'], r @ ryminus(q[i, 1] + q[i, 2] + wheels[i])),
            ):
                item = properties[name + suffix]
                points.append((float(item['mass_kg']), origin + rotation @ np.asarray(item['com_m'], dtype=float)))
        return sum(w*x for w, x in points) / sum(w for w, _ in points)
    m, g = p['mass'], p['geometry']
    body_mass, body_com, _ = body_mass_properties(p)
    points = [(body_mass, body_com)]
    for i in range(4):
        f = fk(p, i, q[i])
        r = rotation_z(f['heading'])
        points.append((m['proximal_servo_kg'] + m['yaw_carriage_without_servos_kg'],
                       mount(p, i) + r @ np.array([g['hip_radial_offset_m']/2, transverse(p,i)/2,0])))
        points.append((m['femur_with_pulleys_kg'], (f['pitch']+f['knee'])/2))
        points.append((m['proximal_servo_kg'], f['pitch']+r @ ryminus(q[i,1]) @ np.array(m['knee_servo_com_m'])))
        mt = m['tibia_with_carrier_kg'] + m['wheel_motor_with_mount_kg']
        zfraction = (.5*m['tibia_with_carrier_kg']+.9*m['wheel_motor_with_mount_kg'])/mt
        points.append((mt, f['knee'] + zfraction*(f['axle']-f['knee'])))
        points.append((m['wheel_hub_and_tire_kg'], f['axle']))
    return sum(w*x for w,x in points)/sum(w for w,x in points)


def margin(points, target):
    hull = ConvexHull(np.asarray(points)[:,:2])
    return float(np.min(-(hull.equations[:,:2] @ np.asarray(target)[:2] + hull.equations[:,2])))


def closest_inset(points, nominal, inset):
    hull = ConvexHull(np.asarray(points)[:,:2])
    a, b = hull.equations[:,:2], hull.equations[:,2]
    result = minimize(lambda x: np.dot(x-nominal,x-nominal), nominal,
                      jac=lambda x: 2*(x-nominal), constraints={'type':'ineq','fun':lambda x: -inset-a@x-b, 'jac':lambda x:-a},
                      method='SLSQP', options={'ftol':1e-14})
    if not result.success:
        raise ValueError(result.message)
    return result.x


def joint_pose(p, feet, body):
    results = [ik(p,i,feet[i]-body) for i in range(4)]
    return np.array([r[0] for r in results]), all(r[1] for r in results)


def body_for_com(p, feet, body_xy, z, com_xy):
    body = np.array([*body_xy,z],float)
    for _ in range(30):
        q, ok = joint_pose(p, feet, body)
        error = com_xy-(body+com(p,q))[:2]
        body[:2] += error
        if np.linalg.norm(error)<1e-10:
            break
    q, ok = joint_pose(p,feet,body)
    return body,q,ok


def static_motor_torque(p,q,stance,feet,body):
    m = total_mass(p)
    gravity = p['environment']['gravity_m_s2']
    c = body+com(p,q)
    contacts = np.array([feet[i,:2] for i in stance])
    forces = np.linalg.solve(np.vstack([np.ones(3),contacts.T]), m*gravity*np.array([1,c[0],c[1]]))
    out = np.zeros((4,3))
    h = 1e-6
    a = coupling(p)
    eta = np.array(p['transmission']['efficiency'])
    for i in range(4):
        for j in range(3):
            qp,qm=q.copy(),q.copy()
            qp[i,j]+=h;qm[i,j]-=h
            dpotential=m*gravity*(com(p,qp)[2]-com(p,qm)[2])/(2*h)
            dfoot=(fk(p,i,qp[i])['axle'][2]-fk(p,i,qm[i])['axle'][2])/(2*h)
            out[i,j]=dpotential-(forces[stance.index(i)]*dfoot if i in stance else 0)
        out[i]=np.linalg.solve(a.T,out[i])/eta
    return out,forces


def trial(p,stride,inset,height,order):
    q0=neutral(p)
    initial=np.array([fk(p,i,q0[i])['axle'] for i in range(4)])
    initial[:,2]=p['geometry']['wheel_diameter_m']/2
    feet=initial.copy()
    lastbody=np.array([0,0,height])
    records=[]
    for k,active in enumerate(order):
        stance=[i for i in range(4) if i!=active]
        nominal=np.array([stride*k/4,0])+com(p,q0)[:2]
        comtarget=closest_inset(feet[stance],nominal,inset)
        body,q,ok=body_for_com(p,feet,lastbody[:2],height,comtarget)
        for u in np.linspace(0,1,21):
            shiftbody=lastbody*(1-u)+body*u
            shiftq,shiftok=joint_pose(p,feet,shiftbody)
            records.append(dict(phase='shift',active=active,ok=shiftok,q=shiftq,body=shiftbody,margin=margin(feet,shiftbody+com(p,shiftq))))
        before=feet[active].copy()
        for u in np.linspace(0,1,41):
            s=u*u*(3-2*u)
            sample=feet.copy()
            sample[active]=before+[stride*s,0,.035*np.sin(np.pi*u)**2]
            swingbody,swingq,swingok=body_for_com(p,sample,body[:2],height,comtarget)
            torques,forces=static_motor_torque(p,swingq,stance,feet,swingbody)
            records.append(dict(phase='swing',active=active,ok=swingok,q=swingq,body=swingbody,
                                margin=margin(feet[stance],swingbody+com(p,swingq)),motor=torques,forces=forces))
        feet[active,0]+=stride
        lastbody=body
    qs=np.array([r['q'] for r in records])
    motorangle=np.einsum('ij,tkj->tki',coupling(p),qs-q0)
    travel=np.degrees(motorangle)
    motor=np.array([r['motor'] for r in records if 'motor' in r])
    bodies=np.array([r['body'] for r in records])
    return dict(stride_m=stride,inset_m=inset,height_m=height,order=order,
                reachable=all(r['ok'] for r in records),min_margin_m=min(r['margin'] for r in records),
                joint_min_deg=np.degrees(np.min(qs,axis=(0,1))).tolist(),joint_max_deg=np.degrees(np.max(qs,axis=(0,1))).tolist(),
                max_abs_motor_travel_deg=float(np.max(abs(travel))),max_static_motor_nm=float(np.max(abs(motor))),
                static_motor_rms_pooled_nm=np.sqrt(np.mean(motor**2,axis=(0,1))).tolist(),
                static_motor_rms_per_leg_nm=np.sqrt(np.mean(motor**2,axis=0)).tolist(),
                static_motor_max_individual_rms_nm=float(np.sqrt(np.mean(motor**2,axis=0)).max()),
                max_static_by_axis_nm=np.max(abs(motor),axis=(0,1)).tolist(),
                min_support_normal_n=float(min(np.min(r['forces']) for r in records if 'forces' in r)),
                body_xy_min_m=bodies[:,:2].min(axis=0).tolist(),body_xy_max_m=bodies[:,:2].max(axis=0).tolist(),
                step_body_positions_m=[records[k*62+21]['body'].tolist() for k in range(4)])


def main():
    p=load_parameters(SIM/'proximal_knee_20260907/parameters_same_mass.json')
    q0=neutral(p)
    feet=np.array([fk(p,i,q0[i])['axle'] for i in range(4)])
    # Geometry samples and gravity balance only. No actuator limits are changed.
    trials=[trial(p,s,m,h,list(o)) for s,m,h,o in itertools.product([.02,.04,.06],[.02,.03],[.2225,.2325,.2425],[(0,3,1,2),(2,0,3,1)])]
    result=dict(scope='Kinematic/quasistatic only; no physics success or CAD fit implied',mass_kg=total_mass(p),
                neutral_q_deg=np.degrees(q0).tolist(),neutral_axles_body_m=feet.tolist(),
                neutral_robot_com_body_m=com(p,q0).tolist(),
                neutral_three_support_margin_m=[margin(np.delete(feet,i,axis=0),com(p,q0)) for i in range(4)],
                trials=trials)
    (HERE/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='trials'},indent=2))
    for r in trials:
        if r['stride_m']==.04 and r['height_m']==.2325:
            print(json.dumps(r))


if __name__=='__main__':
    main()
