"""Try a connected first-leg lift, crossing and touchdown with fixed support feet."""
from pathlib import Path
import json
import numpy as np
from scipy.optimize import minimize
import search as s

ROOT = Path(__file__).resolve().parent
event = json.loads((ROOT/'first_front_crossing_guarded.json').read_text())['result']
template = np.array(event['x'])
phases = [('lift', -.065, -.065, s.R, .245, 30),
          ('cross', -.065, .085, .245, .245, 35),
          ('touchdown', .085, .085, .245, s.R+s.RISE, 10)]
prev = np.r_[template[:3], .17]
records=[]
for name, xa, xb, za, zb, count in phases:
    for u in np.linspace(0, 1, count, endpoint=True):
        footx, footz = xa+(xb-xa)*u, za+(zb-za)*u
        touchdown = name == 'touchdown' and u == 1
        def unpack(y):
            x=template.copy()
            x[:3]=y[:3]
            x[3:5]=[footx,y[3]]
            x[11]=footz
            return x
        def residual(y):
            c=s.evaluate(unpack(y), [0,0,0,0], swing=0, guarded=True, touchdown=touchdown)
            # Leave a small numerical interpolation reserve inside the stated
            # engineering guard bands; do not relax a failed constraint.
            d=s.evaluate(unpack(y),[0,0,0,0],swing=0,details=True,guarded=True,touchdown=touchdown)
            q=np.radians(d['q_deg']);travel=np.array(d['motor_offset_deg'])
            extra=np.r_[((q-s.LIMITS[:,0])-np.radians(2.1)).ravel(),
                        ((s.LIMITS[:,1]-q)-np.radians(2.1)).ravel(),
                        ((travel-s.TRAVEL[:,0]-5.1)/50).ravel(),
                        ((s.TRAVEL[:,1]-travel-5.1)/50).ravel(),
                        (d['support_margin_m']-.0151)*20,
                        ((.899*s.CONT-abs(np.array(d['motor_torque_nm'])))/s.CONT).ravel()]
            c=np.r_[c,extra]
            return float(np.minimum(c,0)@np.minimum(c,0))
        trials=[]
        for initial in [prev, np.r_[template[:3], .24], np.array([-.18, .01, .30, .25])]:
            out=minimize(residual,initial,method='L-BFGS-B',bounds=[(-.23,.05),(-.06,.08),(.22,.309),(.11,.30)],options={'maxiter':220,'ftol':1e-13,'maxls':30})
            trials.append(out)
            if residual(out.x)<1e-11: break
        best=min(trials,key=lambda o:residual(o.x))
        d=s.evaluate(unpack(best.x),[0,0,0,0],swing=0,details=True,guarded=True,touchdown=touchdown)
        d.update(phase=name,phase_fraction=float(u),objective=residual(best.x))
        records.append(d)
        prev=best.x
        print(name,round(u,3),round(d['objective'],6),d['feasible'],flush=True)
path=ROOT/'first_leg_path.json'
if path.exists():
    from datetime import datetime
    path=ROOT/('first_leg_path_'+datetime.now().strftime('%H%M%S%f')+'.json')
path.write_text(json.dumps({'connected_sampled_path_feasible':all(r['feasible'] for r in records),
                           'claim':'Sampled kinematic/quasi-static screen only; no acceleration, inertia, wheel scrub or dynamics integration.',
                           'samples':records},indent=2))
print(path)
