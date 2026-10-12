"""Render the emitted deposition paths and an annotated inspection map."""
from pathlib import Path
import sys,json
from types import SimpleNamespace
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Polygon as Patch,Patch as Legend
from matplotlib.colors import to_rgb
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'hexapod_phone_quad_r5_20260912/review'))
from render_preview import draw_mesh,camera_basis
from generate import BASES,LABELS,BASE,BAND,TOP
COLOURS={'F':'#25859b','A':'#cb7635','R':'#725aa8','C':'#4b955f','T':'#697b87','S':'#b85180','BASE':'#c5c6bd','LABEL':'#263a3d','purge':'#c5c6bd'}

def main():
    rows=json.loads((ROOT/'expected_paths.json').read_text());design=json.loads((ROOT/'test_design.json').read_text())
    fig,ax=plt.subplots(figsize=(10,9),facecolor='#f4f3ed');ax.set_facecolor('#f4f3ed')
    descriptions={'F':'F: flow, long straight walls','A':'A: acceleration and ringing','R':'R: bracket quality at rising speed','C':'C: same bracket, constant 40 mm/s','T':'T: stringing control, 0.5 mm retract','S':'S: stringing, changing retraction'}
    for name,shape in BASES.items():
        for poly in [shape] if shape.geom_type=='Polygon' else shape.geoms:
            ax.add_patch(Patch(np.asarray(poly.exterior.coords),facecolor=COLOURS[name],alpha=.18,edgecolor=COLOURS[name],lw=1.2))
    for name in ('F','A','R','C','T','S'):
        selected=[r for r in rows if r['e_mm']>0 and r['stage']==name and r['band']==1]
        lines=[[r['start'][:2],r['end'][:2]] for r in selected]
        ax.add_collection(LineCollection(lines,colors=COLOURS[name],linewidths=.7,alpha=.35))
        x,y=LABELS[name];ax.text(x+2,y+1,name,fontsize=14,weight='bold',color=COLOURS[name],ha='center')
    ax.set_xlim(5,220);ax.set_ylim(0,220);ax.set_aspect('equal');ax.set_xlabel('Printer X (mm)');ax.set_ylabel('Printer Y (mm)')
    ax.set_title('One print, six readable test bands',fontsize=21,pad=18)
    ax.legend(handles=[Legend(color=COLOURS[n],label=descriptions[n]) for n in ('F','A','R','C','T','S')],loc='upper center',bbox_to_anchor=(.5,-.10),ncol=2,frameon=False,fontsize=10)
    fig.text(.5,.015,'F, R, C, S, T: 0.28 mm layers   |   A: 0.14 mm layers to isolate acceleration from flow',ha='center',fontsize=10)
    fig.subplots_adjust(bottom=.23);fig.savefig(ROOT/'Print_Map.png',dpi=160,bbox_inches='tight');plt.close(fig)
    # Render each extruded segment as a rectangular bead prism, preserving
    # recorded layer height, width, path and position. This is a toolpath view,
    # not a model of pressure, rounded bead shape or real fused material.
    triangles=[];colours=[]
    for r in rows:
        if r['e_mm']<=0 or r['stage'] in ('purge','startup'):continue
        a,b=np.array(r['start']),np.array(r['end']);delta=b-a;length=np.linalg.norm(delta[:2])
        if length<.01:continue
        perpendicular=np.array([-delta[1],delta[0],0])/length*r['width']/2
        top=np.array([a-perpendicular,b-perpendicular,b+perpendicular,a+perpendicular]);bottom=top.copy();bottom[:,2]-=r['layer_height'];vertices=np.concatenate([bottom,top])
        faces=[(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
        c=np.array(to_rgb(COLOURS.get(r['stage'],'#999999')))
        if r['band'] and r['band']%2==0:c=c*.75+.25
        for face in faces:triangles.append(vertices[list(face)]);colours.append(c)
    tri=np.array(triangles);norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-10)
    fig,ax=plt.subplots(figsize=(13,9),facecolor='#f4f3ed');ax.set_facecolor('#f4f3ed')
    draw_mesh(ax,SimpleNamespace(triangles=tri,normals=norm,colors=np.array(colours)),camera_basis(28,-65));ax.set_aspect('equal');ax.axis('off')
    fig.suptitle('Preview of the actual generated extrusion paths',fontsize=21)
    fig.text(.5,.035,'Six bands from bottom to top. Preview colours distinguish tests; print uses your single PLA colour.',ha='center',fontsize=11)
    fig.savefig(ROOT/'Toolpath_Preview.png',dpi=150,bbox_inches='tight');plt.close(fig)
    fig,ax=plt.subplots(figsize=(12,5),facecolor='#f4f3ed');ax.axis('off')
    columns=['Band','Height from bed','F: flow','F: speed','A: accel','R: speed','S: retract']
    table=[]
    for r in design['schedule']:table.append([r['band'],f"{r['z_bottom_mm']:.2f} to {r['z_top_mm']:.2f} mm",f"{r['F_flow_mm3_s']} mm3/s",f"{r['F_speed_mm_s']:.0f} mm/s",f"{r['A_acceleration_mm_s2']} mm/s2",f"{r['R_speed_mm_s']} mm/s",f"{r['S_retraction_mm']:.2f} mm"])
    t=ax.table(cellText=table,colLabels=columns,loc='center',cellLoc='center',colWidths=[.07,.24,.14,.14,.15,.14,.12]);t.auto_set_font_size(False);t.set_fontsize(11);t.scale(1,2.1)
    for (row,col),cell in t.get_celld().items():cell.set_facecolor('#cddfdf' if row==0 else '#ffffff' if row%2 else '#ecf0ec');cell.set_edgecolor('#c4cccc')
    ax.set_title('Read each specimen from bottom band 1 to top band 6',fontsize=18,pad=10)
    fig.text(.5,.04,'Controls stay constant: C = 40 mm/s; T = 0.5 mm retract. A stays at 120 mm/s and about 7.06 mm3/s.',ha='center',fontsize=11)
    fig.savefig(ROOT/'Band_Reference.png',dpi=160,bbox_inches='tight');plt.close(fig)
    print('Rendered map, actual toolpath preview and band reference')

if __name__=='__main__':main()
