"""Independent numerical identities and dense interpolation checks for the screen."""
from pathlib import Path
import json
import hashlib
import numpy as np
import search as s
import pitch_search as ps

ROOT=Path(__file__).resolve().parent
path=max(ROOT.glob('first_leg_path*.json'),key=lambda p:p.stat().st_mtime)
poses=json.loads(path.read_text())['samples']
errs=[];mass_errors=[]
rng=np.random.default_rng(1707)
for i in range(4):
    for n in range(5):
        q=s.Q0[i]+rng.normal(0,.12,3)
        items,g,j,f=s.masses_and_gravity(i,q)
        for k in range(3):
            eps=np.zeros(3);eps[k]=1e-6
            def potential(q):
                return s.GRAV*sum(w*p[2] for w,p in s.masses_and_gravity(i,q)[0])
            numeric=(potential(q+eps)-potential(q-eps))/2e-6
            errs.append(abs(numeric-g[k]))
    mass_errors.append(abs(sum(w for w,pos in items)-(s.TOTAL-s.BODY_M)/4))
pitch_jac=[];low_jac=[]
for tilt in np.radians([-10,-5,5,10]):
    rot=ps.rotation(tilt)
    for i in range(4):
        q=np.radians(poses[-1]['q_deg'][i])
        for k in range(3):
            eps=np.zeros(3);eps[k]=1e-6
            fplus=s.model.fk(s.P,i,q+eps);fminus=s.model.fk(s.P,i,q-eps)
            numeric=rot@(fplus['axle']-fminus['axle'])/2e-6
            pitch_jac.append(float(abs(numeric-(rot@ps.jacobian(q,i,1,1))[:,k]).max()))
        theta=s.model.fk(s.P,i,q)['heading']
        az=math_sin=float(np.sin(tilt)*np.sin(theta))
        analytic=(-s.R*az/np.sqrt(1-az*az)+s.HW*np.sign(az))*np.sin(tilt)*np.cos(theta)
        def low(angle):
            az=np.sin(tilt)*np.sin(angle)
            return s.R*np.sqrt(1-az*az)+s.HW*abs(az)
        low_jac.append(abs(analytic-(low(theta+1e-6)-low(theta-1e-6))/2e-6))
dense=[]
for index,(a,b) in enumerate(zip(poses,poses[1:])):
    for fraction in np.linspace(0,1,11,endpoint=False):
        x=np.array(a['x'])*(1-fraction)+np.array(b['x'])*fraction
        result=s.evaluate(x,[0,0,0,0],swing=0,details=True,guarded=True)
        result.update(segment=index,fraction=float(fraction))
        dense.append(result)
dense.append(s.evaluate(np.array(poses[-1]['x']),[0,0,0,0],swing=0,details=True,guarded=True,touchdown=True))
eq=[]
for p in dense:
    force=np.array(p['vertical_forces_n']);feet=np.array(p['feet_m']);com=np.array(p['com_m'])
    eq.append(float(abs(np.r_[sum(force)-s.TOTAL*s.GRAV,force@feet[:,:2]-s.TOTAL*s.GRAV*com[:2]]).max()))
times=[]
for p in poses:
    phase=p['phase'];u=p['phase_fraction']
    times.append(u*6 if phase=='lift' else (6+u*6 if phase=='cross' else 12+u*2))
speed=[];envelope=[]
for i in range(len(poses)-1):
    dt=times[i+1]-times[i]
    if dt<=0: continue
    a,b=poses[i:i+2]
    shaft=s.A@np.radians(np.array(b['q_deg'])-np.array(a['q_deg'])).T/dt
    speed.append(float(abs(shaft).max()))
    tau=(np.array(a['motor_torque_nm'])+np.array(b['motor_torque_nm']))/2
    avail=np.minimum(s.PEAK,s.STALL*np.clip(1-np.sign(tau)*shaft.T/(s.S['no_load_speed_rpm']*2*np.pi/60*s.S['simulation_voltage_v']/s.S['nominal_voltage_v']),0,1))
    envelope.append(float((avail-abs(tau)).min()))
report=dict(path_source=path.name, dense_count=len(dense),dense_feasible=all(p['feasible'] for p in dense),
            dense_min_constraint=min(p['min_scaled_constraint'] for p in dense),
            min_support_margin_m=min(p['support_margin_m'] for p in dense),max_torque_nm=max(p['max_motor_torque_nm'] for p in dense),
            gravity_gradient_max_error_nm=max(errs),leg_mass_closure_kg=max(mass_errors),
            pitched_axle_jacobian_max_error_m_rad=max(pitch_jac),wheel_camber_derivative_error_m_rad=max(low_jac),
            equilibrium_residual_max=max(eq),
            provisional_14s_schedule=dict(max_motor_speed_rad_s=max(speed),min_static_torque_speed_headroom_nm=min(envelope),
                interpretation='Only a static torque plus finite-difference speed screen. Acceleration, tyre scrub, actuator transients and thermal behavior are not simulated.'),
            failed_dense_samples=[dict(segment=p.get('segment'),fraction=p.get('fraction'),min_constraint=p['min_scaled_constraint']) for p in dense if not p['feasible']],
            source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'model_snapshot.py',ROOT/'parameters_snapshot.json',ROOT/'search.py',ROOT/'pitch_search.py',ROOT/'first_leg_path.py']})
(ROOT/'verification.json').write_text(json.dumps(report,indent=2))
(ROOT/'first_leg_dense_trace.json').write_text(json.dumps(dict(claim='Quasi-static only; full robot stair sequence and dynamics remain unverified.',samples=dense),indent=2))
print(json.dumps(report,indent=2))
