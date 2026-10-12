"""Inspect actual deposition for support intrusion into functional openings."""
from pathlib import Path
import json,gzip,re,math
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'
PARAM=re.compile(r'([XYZEF])(-?\d+(?:\.\d+)?)')

def rot(deg):
    x,y,z=np.radians(deg);cx,sx=np.cos(x),np.sin(x);cy,sy=np.cos(y),np.sin(y);cz,sz=np.cos(z),np.sin(z)
    return np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])@np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])@np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])

def segments(path):
    pos=np.zeros(4);kind='';result=[];layer=0
    with gzip.open(path,'rt') as f:
        for line in f:
            if line.startswith(';TYPE:'):kind=line.strip()[6:]
            if line.startswith(';LAYER:'):layer=int(line.strip()[7:])
            line=line.removeprefix('; DISABLED ');cmd=line.split(';')[0].strip();verb=cmd.split(' ')[0]
            fields={k:float(v) for k,v in PARAM.findall(cmd)}
            if verb=='G92':
                if 'E' in fields:pos[3]=fields['E']
                continue
            if verb not in ('G0','G1'):continue
            nxt=pos.copy()
            for k,v in fields.items():
                if k in 'XYZE':nxt['XYZE'.index(k)]=v
            if nxt[3]>pos[3]+1e-7 and np.linalg.norm(nxt[:3]-pos[:3])>1e-6:result.append((pos[:3].copy(),nxt[:3].copy(),kind,layer))
            pos=nxt
    return result

def regions(p):
    n=p['name'];rs=[]
    if n in ('yaw_case_saddle','coxa_upper_and_hip_saddle','femur_main_and_knee_saddle'):
        bolts=[(-38.915,-5.5),(13.915,-23),(13.915,-7)]
        if n=='coxa_upper_and_hip_saddle':bolts[0]=(-38.915,-27.5)
        pitch=np.eye(4)
        if n!='yaw_case_saddle':pitch[:3,:3]=rot([-90,0,0]);pitch[:3,3]=[82 if n.startswith('coxa') else 90,14.5,0]
        for i,(x,z) in enumerate(bolts):
            rs.append((f'clamp nut {i}',np.array([x-2.5,-16.36,z-2.5]),np.array([x+2.5,-10,z+2.5]),pitch))
            # The matching cap is printed flat on plate 01. The saddle's end
            # wall stops at raw Y=11.565; do not mislabel external tree branches
            # in the absent cap's future volume as support inside this bore.
            rs.append((f'clamp screw {i}',np.array([x-1.2,-10,z-1.2]),np.array([x+1.2,11.565,z+1.2]),pitch))
    if n=='femur_main_and_knee_saddle':
        rs.append(('femur bridge nut slot',np.array([62.5,2.5,20.5]),np.array([67.5,5.2,27.4]),np.eye(4)))
    if n=='tibia_curved_main_and_foot':
        for x in (36,44):rs.append(('tibia bridge nut slot '+str(x),np.array([x-2.5,2.5,0]),np.array([x+2.5,5.2,11.4]),np.eye(4)))
    if n=='coxa_upper_and_hip_saddle':
        for y,z0 in [(-4.5,-41.5),(4.5,-37.5)]:rs.append(('post nut entry '+str(y),np.array([37.9,min(y,-11.4) if y<0 else y,z0+.1]),np.array([43.1,y if y<0 else 11.4,z0+2.6]),np.eye(4)))
    return rs

def main():
    manifest=json.loads((OUT/'manifest.json').read_text());by={p['name']:p for p in manifest['parts']}
    printing=json.loads((OUT/'print_validation.json').read_text());rows=[]
    for plate in printing['plates']:
        seg=segments(ROOT/'analysis_slices'/(plate['name']+'.analysis_only.gcode.gz'))
        support=[s for s in seg if s[2].startswith('SUPPORT')]
        mids=np.array([(a+b)/2 for a,b,_,_ in support]).reshape((-1,3))
        # Cura was supplied a centred STL, but retain its explicit frame map.
        inv=np.linalg.inv(np.array(plate['engine']['source_to_gcode_transform']))
        mids=mids@inv[:3,:3].T+inv[:3,3];mids[:,2]-=.14
        widths=[]
        for placed in plate['parts']:
            p=by[placed['name']];widths.append(np.array(placed['lower_corner_mm'])+np.array(p['dimensions_mm']))
        extent=np.max(widths,axis=0);shift=np.array([112.5-extent[0]/2,112.5-extent[1]/2,0])
        checks=[]
        for placed in plate['parts']:
            p=by[placed['name']];r=rot(p['print_rotation']);m=trimesh.load_mesh(OUT/p['assembly_stl'])
            lo=(m.vertices@r.T).min(axis=0)
            points=(mids-np.array(placed['lower_corner_mm'])-shift+lo)@r
            for tag,lower,upper,pitch in regions(p):
                local=(points-pitch[:3,3])@pitch[:3,:3]
                mask=np.all((local>lower)&(local<upper),axis=1)
                external=0
                if tag.startswith('post nut entry'):
                    # The established rear-cap driver scallop removes this
                    # region from the post entirely. Classify branches there
                    # as exposed external support, not enclosed nut-slot fill.
                    scallop=(local[:,0]-43.085)**2+(local[:,1]+13)**2 < 4**2
                    external=int((mask&scallop).sum());mask &= ~scallop
                checks.append({'part':p['name'],'opening':tag,'support_segment_midpoints_inside':int(mask.sum()),'external_driver_scallop_support_midpoints':external,'first_local_hits_mm':local[mask][:5].tolist()})
        rows.append({'plate':plate['name'],'support_segments':len(support),'opening_checks':checks})
        fig,axes=plt.subplots(1,2,figsize=(13,6),facecolor='#f3f4f0')
        for ax,axes_idx,title in [(axes[0],[0,1],'Top view'),(axes[1],[0,2],'Side view')]:
            for is_support in (False,True):
                selected=[s for s in seg if s[2].startswith('SUPPORT')==is_support and s[2] not in ('SKIRT','BRIM')]
                step=1 if is_support else 12
                lines=np.array([[a[axes_idx],b[axes_idx]] for a,b,_,_ in selected[::step]])
                if len(lines):ax.add_collection(LineCollection(lines,colors='#ce8c38' if is_support else '#488d92',linewidths=.45 if is_support else .18,alpha=.7 if is_support else .18))
            ax.autoscale();ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)' if axes_idx==[0,1] else 'Z (mm)');ax.set_facecolor('#f3f4f0')
        fig.suptitle(plate['name'].replace('_',' ')+' | teal: model, amber: actual tree support',fontsize=14)
        fig.tight_layout();fig.savefig(OUT/'plates'/(plate['name']+'_supports.png'),dpi=140);plt.close(fig)
    report={'status':'pass' if not any(c['support_segment_midpoints_inside'] for p in rows for c in p['opening_checks']) else 'review required',
        'plates':rows,'scope':'Actual sliced support centreline midpoints versus inset screw/nut opening boxes. This samples deposition centres; it does not prove bead-edge clearance, bridge quality or easy breakaway.'}
    (OUT/'support_check.json').write_text(json.dumps(report,indent=2));print(report)

if __name__=='__main__':main()
