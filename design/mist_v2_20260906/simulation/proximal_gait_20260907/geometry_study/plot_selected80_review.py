"""Render one saved crawl run without changing its evidence or the simulator."""
from pathlib import Path
import hashlib
import json
import os
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / '.plot_deps'))
os.environ['MPLCONFIGDIR'] = str(HERE / '.plot_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    run = HERE.parent / 'stride80_force_feedback_3s_3cycles'
    evidence = {name: hashlib.sha256((run/name).read_bytes()).hexdigest()
                for name in ('report.json', 'trajectory.json', 'controller.json', 'parameters_used.json')}
    report = json.loads((run/'report.json').read_text())
    controller = json.loads((run/'controller.json').read_text())
    frames = json.loads((run/'trajectory.json').read_text())['frames']
    time = np.array([f['t'] for f in frames])
    position = np.array([f['base_position'] for f in frames])*1000
    desired = np.array([f['desired_base_position'] for f in frames])*1000
    late = time >= controller['settle_s']
    contacts = np.array([sum(np.array(f['contact_normal_n']) > 1) for f in frames])
    margins = np.array([np.nan if f['support_margin_m'] is None else f['support_margin_m']*1000 for f in frames])
    bad = late & (contacts < 3)
    loss_pct = 100*np.mean(contacts[late] < 3)
    negative = late & (margins < 0)
    assert abs(loss_pct - 100*report['fewer_than_three_contact_sample_fraction']) < 1e-8
    rms = np.array(report['motor_rms_nm'])
    names = ['FL','FR','RL','RR']
    blue, orange, red, green, purple = '#286289','#b3681e','#b43d32','#38806b','#80629a'
    leg_colors = [blue, orange, green, purple]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.titlesize':13,
                         'axes.titleweight':'bold','axes.labelsize':11,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.edgecolor':'#a8acb0','axes.labelcolor':'#26323a',
                         'xtick.color':'#44515a','ytick.color':'#44515a','text.color':'#26323a',
                         'grid.color':'#e4e7e9','grid.linewidth':.7})
    fig, axes = plt.subplots(2,2,figsize=(15,10),gridspec_kw={'hspace':.37,'wspace':.22})
    fig.subplots_adjust(left=.08,right=.966,bottom=.145,top=.829)
    fig.suptitle('MIST crawl: 237 mm forward, with no sampled loss of support',x=.07,y=.952,ha='left',fontsize=20,fontweight='bold')
    fig.text(.07,.908,'Three cycles · 80 mm stride · 3 s per leg · 6.341 kg coarse model · 39.50 s simulated',fontsize=12,color='#53636e')

    ax = axes[0,0]
    ax.plot(time, position[:,0],color=blue,lw=1.9,label='Forward X')
    ax.plot(time, position[:,1],color=orange,lw=1.7,label='Lateral Y')
    ax.plot(time, desired[:,0],color='#929ba2',lw=1.1,ls='--',label='Desired X')
    ax.axhline(0,color='#b7bec3',lw=.8)
    ax.set(title='Body position through the crawl',xlabel='Time (s)',ylabel='Position (mm)',xlim=(0,40),ylim=(-65,265))
    ax.set_xticks(np.arange(0,41,10));ax.grid(axis='y');ax.legend(loc='upper left',frameon=False,ncol=3,fontsize=10)
    ax.text(39.7,243,f"{report['base_displacement_m'][0]*1000:.1f} mm",ha='right',va='bottom',color=blue,fontsize=11,fontweight='bold')

    ax = axes[0,1]
    audits = report['swing_audits']
    heights = np.array([a['max_swing_clearance_m']*1000 for a in audits])
    idx = np.arange(len(audits))
    for cycle in (0,2): ax.axvspan(cycle*4-.5,cycle*4+3.5,color='#f1f4f5',zorder=0)
    ax.bar(idx,heights,color=[leg_colors[a['leg']] for a in audits],width=.65,zorder=3)
    ax.axhline(15,color=red,ls='--',lw=1.2,zorder=4)
    ax.axhline(40,color='#9ba5ad',ls=':',lw=1.1,zorder=1)
    for x,h in zip(idx,heights): ax.text(x,h+.7,f'{h:.1f}',ha='center',va='bottom',fontsize=10)
    for cycle in range(3):ax.text(cycle*4+1.5,36,'Cycle '+str(cycle+1),ha='center',fontsize=10,color='#53636e')
    ax.text(11.4,15.7,'15 mm required',color=red,ha='right',fontsize=10,
            bbox={'facecolor':'white','edgecolor':'none','alpha':.95,'pad':1.5})
    ax.text(11.4,40.8,'40 mm commanded',color='#6d7881',ha='right',fontsize=10)
    ax.set_xticks(idx,[names[a['leg']] for a in audits])
    ax.set(title='Peak actual clearance in every scheduled swing',ylabel='Wheel clearance (mm)',xlabel='Swing order',ylim=(0,45),xlim=(-.6,11.6))
    ax.grid(axis='y',zorder=0)

    ax = axes[1,0]
    ax.step(time[late],contacts[late],where='post',color=blue,lw=1.25)
    ax.scatter(time[bad],contacts[bad],s=28,color=red,zorder=4)
    ax.axhline(3,color='#a4adb4',ls='--',lw=.9)
    ax.set(title='Loaded wheels (>1 N), after initial settling',xlabel='Time (s)',ylabel='Wheel count',xlim=(0,40),ylim=(1.45,4.7),yticks=[2,3,4])
    ax.set_xticks(np.arange(0,41,10));ax.grid(axis='y')
    assert not bad.any() and not negative.any(), 'Selected support conclusion changed'
    ax.text(2,2.05,f'0% sampled loss of three-wheel support\nMinimum support margin: +{np.nanmin(margins[late]):.1f} mm',
            ha='left',va='center',fontsize=12,color=green,bbox={'facecolor':'white','edgecolor':'none','pad':3})
    ax.text(.02,.94,'Contact count and margin checked at 50 Hz',transform=ax.transAxes,fontsize=10,color='#53636e',va='top')

    ax = axes[1,1]
    x = np.arange(4)
    for j,(label,color) in enumerate([('Yaw','#8c9ba5'),('Hip',blue),('Knee',purple)]):
        ax.bar(x+(j-1)*.25,rms[:,j],width=.22,color=color,label=label,zorder=3)
        for i,h in enumerate(rms[:,j]):
            stagger = .045 if j == 2 and abs(h-rms[i,1]) < .06 else 0
            ax.text(x[i]+(j-1)*.25,h+.013+stagger,f'{h:.3f}',ha='center',va='bottom',fontsize=9)
    limit = report['servo_continuous_limit_nm']
    ax.axhline(limit,color=red,ls='--',lw=1.3)
    ax.text(3.4,limit+.018,f'Assumed continuous limit: {limit:.3f} Nm',ha='right',color=red,fontsize=10)
    ax.set(title='Individual actuator RMS over the entire run',xlabel='Leg',ylabel='Servo shaft torque (Nm)',ylim=(0,.87),xlim=(-.6,3.6))
    ax.set_xticks(x,names);ax.grid(axis='y',zorder=0)
    ax.legend(loc='upper left',frameon=False,ncol=3,fontsize=10)

    fig.text(.07,.080,'All 12 swings clear 15 mm. Ideal state feedback, assumed actuator dynamics and coarse geometry still limit this model result.',fontsize=11,color='#53636e')
    fig.text(.07,.049,'Source: stride80_force_feedback_3s_3cycles/report.json + trajectory.json · This chart does not validate CAD fit, stairs or hardware.',fontsize=10,color='#6d7881')
    for ext in ('png','svg','pdf'):
        fig.savefig(HERE/f'controller_selected80_3s_3cycles.{ext}',dpi=120,facecolor='white')
    fig.savefig(HERE/'controller_selected80_3s_3cycles_preview50.png',dpi=60,facecolor='white')
    plt.close(fig)
    evidence_after={name:hashlib.sha256((run/name).read_bytes()).hexdigest() for name in evidence}
    assert evidence_after == evidence, 'Source evidence changed during analysis'
    (HERE/'controller_selected80_chart_sources.json').write_text(json.dumps({'source_run':str(run),'sha256':evidence,
        'contact_loss_pct':loss_pct,'negative_support_frames':int(negative.sum()),
        'minimum_support_margin_mm':float(np.nanmin(margins[late])),
        'source_evidence_unchanged':True,'matplotlib_version':matplotlib.__version__},indent=2),encoding='utf-8')
    print(HERE/'controller_selected80_3s_3cycles.png')


if __name__=='__main__':
    main()
