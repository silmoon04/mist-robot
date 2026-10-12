"""Rear crossing with a pitched body, cambered wheels and vertical reactions."""
from pathlib import Path
import itertools
import json
import math
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
import search as s

ROOT=Path(__file__).resolve().parent
M,G=s.M,s.G


def rotation(pitch):
    c,t=math.cos(pitch),math.sin(pitch)
    return np.array([[c,0,-t],[0,1,0],[t,0,c]])


def jacobian(q, i, t1, t2, proximal=.035, transverse=None):
    theta=math.radians(G['mount_azimuths_deg'][i])+q[0]
    h,k=q[1:]
    c=s.model.transverse(s.P,i) if transverse is None else transverse
    a=proximal+t1*G['femur_m']*np.sin(h)+t2*G['tibia_m']*np.sin(h+k)
    dh=t1*G['femur_m']*np.cos(h)+t2*G['tibia_m']*np.cos(h+k)
    dk=t2*G['tibia_m']*np.cos(h+k)
    zh=t1*G['femur_m']*np.sin(h)+t2*G['tibia_m']*np.sin(h+k)
    zk=t2*G['tibia_m']*np.sin(h+k)
    return np.array([[-a*np.sin(theta)-c*np.cos(theta),dh*np.cos(theta),dk*np.cos(theta)],
                     [a*np.cos(theta)-c*np.sin(theta),dh*np.sin(theta),dk*np.sin(theta)],
                     [0,zh,zk]])


def body_projections():
    # Body, deck tabs, phone cassette, face bezel and rear connector envelopes
    # from cad/body_native.py. All positions here use the hip plane origin.
    angle=np.linspace(0,2*np.pi,129)
    parts=[np.array([[.09*np.cos(t),.09*np.sin(t),z] for t in angle for z in [-.035,.225]])]
    for centre,size in [([0,0,-.0325],[.204,.204,.005]),
                        ([.072575,0,.105],[.01135,.0761,.151]),
                        ([.0915,0,.104],[.015,.094,.086]),
                        ([-.094,0,-.003],[.008,.049,.036])]:
        parts.append(np.array(centre)+np.array(list(itertools.product([-1,1],repeat=3)))*np.array(size)/2)
    return parts


BODY=body_projections()


def boundary_samples(points):
    hull=ConvexHull(points[:,[0,2]])
    v=points[hull.vertices][:,[0,2]]
    return np.concatenate([np.linspace(a,b,max(2,math.ceil(np.linalg.norm(a-b)/.003)+1)) for a,b in zip(v,np.roll(v,-1,axis=0))])


def evaluate(x,details=False):
    body=x[:3]; tilt=x[12]; rot=rotation(tilt)
    feet=np.column_stack([x[3:11].reshape(4,2),[s.R+s.RISE,s.R+s.RISE,x[11],s.R]])
    weights=[(s.BODY_M,body+rot@s.BODY_C)]
    qs=[];fs=[];gravity=[];jzs=[];contacts=[];cons=[];col=[]
    for i in range(4):
        for _ in range(8):
            q,ok=s.model.ik(s.P,i,rot.T@(feet[i]-body))
            f=s.model.fk(s.P,i,q)
            axis=rot@f['wheel_axis']
            low=s.R*np.sqrt(1-axis[2]**2)+s.HW*abs(axis[2])
            if i != 2: feet[i,2]=([1,1,0,0][i]*s.RISE)+low
        f=s.model.fk(s.P,i,q)
        qs.append(q)
        world={k:body+rot@f[k] for k in ['hip','pitch','knee','axle']}
        world['axis']=rot@f['wheel_axis'];world['heading']=f['heading']
        fs.append(world)
        error=np.linalg.norm(world['axle']-feet[i])
        cons.extend([(1e-6-error)*100,*(q-s.LIMITS[:,0]-np.radians(2)),*(s.LIMITS[:,1]-q-np.radians(2))])
        travel=np.degrees(s.A@(q-s.Q0[i]))
        cons.extend((travel-s.TRAVEL[:,0]-5)/50)
        cons.extend((s.TRAVEL[:,1]-travel-5)/50)
        servo_frac=abs(M['knee_servo_com_m'][2])/G['femur_m']
        items,_,_,_=s.masses_and_gravity(i,q)
        weights.extend((w,body+rot@pos) for w,pos in items)
        jac=[jacobian(q,i,0,0,proximal=.0175,transverse=s.model.transverse(s.P,i)/2),
             jacobian(q,i,.5,0),jacobian(q,i,servo_frac,0),jacobian(q,i,1,.5),
             jacobian(q,i,1,.9),jacobian(q,i,1,1)]
        gravity.append(s.GRAV*sum(w*(rot@j)[2] for (w,pos),j in zip(items,jac)))
        jz=(rot@jacobian(q,i,1,1))[2]
        az=world['axis'][2]
        daz=math.sin(tilt)*math.cos(f['heading'])
        dl=(-s.R*az/np.sqrt(1-az*az)+s.HW*np.sign(az))*daz
        jz[0]-=dl
        jzs.append(jz)
        off=-s.R*(np.array([0,0,1])-az*world['axis'])/np.sqrt(1-az*az)-s.HW*np.sign(az)*world['axis']
        contacts.append(world['axle']+off)
    contacts=np.array(contacts);support=[0,1,3]
    com=sum(w*v for w,v in weights)/s.TOTAL
    mat=np.stack([np.ones(3),contacts[support,0],contacts[support,1]])
    force=np.zeros(4)
    try: force[support]=np.linalg.solve(mat,s.TOTAL*s.GRAV*np.r_[1,com[:2]])
    except np.linalg.LinAlgError: force[support]=-1000
    cons.extend((force[support]-1)/30)
    torque=np.array([np.linalg.solve(s.A.T,gravity[i]-jzs[i]*force[i])/s.ETA for i in range(4)])
    cons.extend(((.9*s.CONT-abs(torque))/s.CONT).ravel())
    hull=ConvexHull(contacts[support,:2])
    margin=float(-(hull.equations[:,:2]@com[:2]+hull.equations[:,2]).max())
    cons.append((margin-.015)*20)
    for part in BODY:
        points=boundary_samples(body+(rot@part.T).T)
        col.append(points[:,1].min()-.0015)
        for j in range(3): col.append(s.signed_free_distance(points[:,0],points[:,1],j*s.TREAD,(j+1)*s.RISE).min()-.0015)
    for i,f in enumerate(fs):
        theta=f['heading'];angles=np.linspace(0,2*np.pi,129)
        radial=rot@np.array([math.cos(theta),math.sin(theta),0]);vertical=rot@np.array([0,0,1])
        wheel=np.concatenate([f['axle']+off*f['axis']+s.R*(np.cos(angles)[:,None]*radial+np.sin(angles)[:,None]*vertical) for off in [-s.HW,0,s.HW]])
        col.append(float(wheel[:,2].min())+1e-7)
        for j in range(3):
            # The exact support point, rather than a sampled rim, sets contact.
            pad=0 if i!=2 and [1,1,0,0][i]==j+1 else .00006
            col.append(float(s.signed_free_distance(wheel[:,0],wheel[:,2],j*s.TREAD,(j+1)*s.RISE).min())-pad)
        for start,end in [(f['pitch'],f['knee']),(f['knee'],f['axle'])]:
            pts=np.linspace(start,end,math.ceil(np.linalg.norm(end-start)/.005)+1)
            col.append(pts[:,2].min()-.015)
            for j in range(3): col.append(s.signed_free_distance(pts[:,0],pts[:,2],j*s.TREAD,(j+1)*s.RISE).min()-.0175)
        # Yaw carriage box rotates with body pitch and leg yaw.
        local= np.array(list(itertools.product([-.0325,.0325],[-.03,.03],[-.0225,.0225])))
        rotation_yaw=s.model.rotation_z(theta)
        pts=(f['hip']+f['pitch'])/2+(rot@rotation_yaw@local.T).T
        pts=boundary_samples(pts)
        for j in range(3): col.append(s.signed_free_distance(pts[:,0],pts[:,1],j*s.TREAD,(j+1)*s.RISE).min()-.0015)
    cons.extend(np.array(col)*20)
    # The lowest part of the airborne wheel, including camber, clears the nose.
    cons.append((contacts[2,2]-s.RISE-.015)*50)
    if not details: return np.array(cons)
    return dict(body_m=body.tolist(),pitch_deg=float(np.degrees(tilt)),feet_axle_m=feet.tolist(),
                contacts_m=contacts.tolist(),q_deg=np.degrees(qs).tolist(),com_m=com.tolist(),
                support_margin_m=margin,forces_n=force.tolist(),motor_torque_nm=torque.tolist(),
                max_motor_torque_nm=float(abs(torque).max()),min_clearance_m=float(min(col)),
                min_scaled_constraint=float(min(cons)),feasible=bool(min(cons)>=-1e-5),x=x.tolist())


def run(degrees,attempts=5):
    rng=np.random.default_rng(7007)
    level=json.loads((ROOT/'first_rear_crossing_guarded.json').read_text())['result']['x']
    bounds=[(-.23,.19),(-.095,.095),(.205,.335)]
    for i in range(4): bounds.extend([(.025,.218) if i<2 else ((-1e-8,1e-8) if i==2 else (-.33,-.047)),(.105,.27) if i%2==0 else (-.27,-.105)])
    bounds.extend([(.2375,.31),(-np.radians(degrees),np.radians(degrees))])
    best=None;trials=[]
    for n in range(attempts):
        initial=np.r_[level,np.radians(degrees)*(1 if n%2==0 else -1)*.7]
        if n>1:
            initial=np.array([rng.uniform(lo,hi) for lo,hi in bounds])
            initial[:3]=[rng.uniform(.01,.10),rng.uniform(-.08,.02),rng.uniform(.26,.30)]
        def objective(x):
            c=evaluate(x)
            return float(np.minimum(c,0)@np.minimum(c,0))
        result=minimize(objective,initial,method='L-BFGS-B',bounds=bounds,options={'maxiter':350,'ftol':1e-13,'maxls':30})
        d=evaluate(result.x,True);val=objective(result.x)
        trials.append(dict(attempt=n,objective=val,feasible=d['feasible']))
        if best is None or val<best['objective']: best=dict(objective=val,result=d)
        print(degrees,n,val,d['pitch_deg'],d['feasible'],flush=True)
        if d['feasible']: break
    output=dict(pitch_bound_deg=degrees,trials=trials,bounds=bounds,**best)
    path=ROOT/f'first_rear_pitch_{degrees}deg.json'
    if path.exists():
        from datetime import datetime
        path=ROOT/f'first_rear_pitch_{degrees}deg_{datetime.now().strftime("%H%M%S%f")}.json'
    path.write_text(json.dumps(output,indent=2))
    return output


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--degrees',type=float,default=5);parser.add_argument('--attempts',type=int,default=5)
    args=parser.parse_args();print(json.dumps(run(args.degrees,args.attempts),indent=2))
