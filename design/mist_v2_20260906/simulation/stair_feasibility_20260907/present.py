"""Readable trace exports and a static engineering review figure."""
from pathlib import Path
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import search as s
import pitch_search as ps

ROOT=Path(__file__).resolve().parent
verification=json.loads((ROOT/'verification.json').read_text())
coarse=json.loads((ROOT/verification['path_source']).read_text())['samples']
dense=json.loads((ROOT/'first_leg_dense_trace.json').read_text())['samples']
pitch=json.loads((ROOT/'first_rear_pitch_5.0deg.json').read_text())['result']
times=[]
for p in coarse:
    phase=p['phase'];u=p['phase_fraction']
    times.append(u*6 if phase=='lift' else (6+u*6 if phase=='cross' else 12+u*2))
for p in dense:
    i=p.get('segment')
    p['illustrative_time_s']=14 if i is None else times[i]*(1-p['fraction'])+times[i+1]*p['fraction']
    p['reverse_lowering_time_s']=14-p['illustrative_time_s']
with (ROOT/'first_leg_trace.csv').open('w',newline='') as f:
    writer=csv.writer(f)
    writer.writerow(['time_s','body_x_m','body_y_m','body_z_m','support_margin_m']+
                    [f'{leg}_{axis}' for leg in ['FL','FR','RL','RR'] for axis in ['wheel_x_m','wheel_y_m','wheel_z_m']]+
                    [f'{leg}_{joint}' for leg in ['FL','FR','RL','RR'] for joint in ['yaw_deg','hip_deg','knee_deg']]+
                    [f'{leg}_{joint}' for leg in ['FL','FR','RL','RR'] for joint in ['yaw_motor_Nm','hip_motor_Nm','knee_motor_Nm']])
    for p in dense:
        writer.writerow([p['illustrative_time_s'],*p['body_m'],p['support_margin_m'],
                         *np.array(p['feet_m']).ravel(),*np.array(p['q_deg']).ravel(),*np.array(p['motor_torque_nm']).ravel()])
(ROOT/'first_leg_candidate.json').write_text(json.dumps(dict(verification=verification,
    scope='One front-leg lift and reverse lowering with three fixed supports. No full four-leg stair sequence or dynamics pass.',samples=dense),indent=2))

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
fig,axs=plt.subplots(2,2,figsize=(13,9),layout='constrained')
colours=['#007c91','#cf6a24','#658649','#805da5']

def stairs(ax):
    ax.plot([-400,0,0,270,270,500],[0,0,180,180,360,360],color='#454d55',lw=2)
    ax.set(xlabel='Forward x (mm)',ylabel='Height z (mm)')
    ax.set_aspect('equal',adjustable='box')
    ax.grid(alpha=.18)

ax=axs[0,0];stairs(ax)
foot=np.array([p['feet_m'][0] for p in dense])
ax.plot(foot[:,0]*1000,foot[:,2]*1000,color=colours[0],lw=2.5,label='Front-left wheel axle')
for index in [0,29,49,74]:
    p=coarse[index];body=np.array(p['body_m']);q=np.radians(p['q_deg'][0]);f=s.model.fk(s.P,0,q)
    chain=body+np.array([f['hip'],f['pitch'],f['knee'],f['axle']])
    ax.plot(chain[:,0]*1000,chain[:,2]*1000,color=colours[0],alpha=.25+index/120,marker='o',ms=3)
ax.axhline(245,color='#a6adb3',ls=':',lw=1)
ax.set(xlim=(-310,175),ylim=(-5,470),title='First front leg: lift, cross and touch down')
ax.legend(loc='upper left',fontsize=9)

ax=axs[0,1]
contacts=np.array(coarse[0]['feet_m'])[1:,:2]*1000
hull=ps.ConvexHull(contacts)
ax.add_patch(Polygon(contacts[hull.vertices],color='#e8eef0',label='Three fixed floor supports'))
ax.scatter(contacts[:,0],contacts[:,1],c='#454d55',s=35)
com=np.array([p['com_m'] for p in dense])*1000
ax.plot(com[:,0],com[:,1],c=colours[1],lw=2.5,label='Whole-robot centre of mass')
ax.plot(foot[:,0]*1000,foot[:,1]*1000,c=colours[0],alpha=.6,label='Airborne wheel axle')
ax.set(xlabel='Forward x (mm)',ylabel='Left y (mm)',title='Support margin stays at least 15.10 mm')
ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.18);ax.legend(fontsize=8,loc='upper left')

ax=axs[1,0]
t=np.array([p['illustrative_time_s'] for p in dense]);torque=np.array([p['motor_torque_nm'] for p in dense])
for i,name in enumerate(['FL airborne','FR support','RL support','RR support']):
    ax.plot(t,abs(torque[:,i]).max(axis=1),c=colours[i],label=name)
ax.axhline(s.CONT,color='#b8423a',ls='--',label='Assumed continuous limit')
ax.axhline(s.CONT*.9,color='#81898f',ls=':',label='10% reserve')
ax.set(xlabel='Illustrative schedule (s)',ylabel='Largest motor torque in each leg (N m)',
       title='Static loads with unchanged 6.341 kg mass',xlim=(0,14),ylim=(0,.82))
ax.grid(alpha=.18);ax.legend(ncol=2,fontsize=8,loc='lower left')

ax=axs[1,1];stairs(ax)
body=np.array(pitch['body_m']);rot=ps.rotation(np.radians(pitch['pitch_deg']))
for part in ps.BODY:
    pts=ps.boundary_samples(body+(rot@part.T).T)*1000
    ax.add_patch(Polygon(pts,color='#dce3e5',alpha=.65))
for i in range(4):
    f=s.model.fk(s.P,i,np.radians(pitch['q_deg'][i]))
    chain=body+(rot@np.array([f['hip'],f['pitch'],f['knee'],f['axle']]).T).T
    ax.plot(chain[:,0]*1000,chain[:,2]*1000,c=colours[i],marker='o',ms=3,label=['FL','FR','RL airborne','RR'][i])
    angles=np.linspace(0,2*np.pi,129)
    radial=rot@np.array([np.cos(f['heading']),np.sin(f['heading']),0])
    vertical=rot@np.array([0,0,1])
    rim=chain[-1]+s.R*(np.cos(angles)[:,None]*radial+np.sin(angles)[:,None]*vertical)
    ax.plot(rim[:,0]*1000,rim[:,2]*1000,c=colours[i],alpha=.7)
ax.set(xlim=(-200,350),ylim=(-5,590),title='Rear event: 3.17° nose-down body pitch')
ax.legend(loc='upper left',fontsize=8)
fig.suptitle('MIST stair feasibility screen · 180 mm rise / 270 mm tread (provisional)\nQuasi-static candidates; full stair sequence and dynamic stability remain unverified',fontsize=14)
fig.savefig(ROOT/'stair_candidates.png',dpi=160)
print(ROOT/'stair_candidates.png')
