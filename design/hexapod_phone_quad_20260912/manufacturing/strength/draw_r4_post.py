"""Actual mesh projection and section. This is not a stress contour."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
import trimesh

OUT=Path(__file__).resolve().parent
MESH=OUT.parents[1]/'cad/output/parts_mesh'
coxa=trimesh.load_mesh(MESH/'FL_coxa_upper_and_hip_saddle.stl')
lower=trimesh.load_mesh(MESH/'FL_coxa_lower_auxiliary_arm.stl')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
fig,axes=plt.subplots(1,2,figsize=(13,7.2),gridspec_kw={'width_ratios':[1.4,1]})
fig.subplots_adjust(left=.06,right=.97,top=.83,bottom=.25,wspace=.35)

def fill(ax,shape,colour,edge='#34424f'):
    pieces=[shape] if shape.geom_type=='Polygon' else list(shape.geoms)
    for p in pieces:
        if p.geom_type!='Polygon':continue
        xy=np.asarray(p.exterior.coords)
        ax.fill(xy[:,0],xy[:,1],color=colour,ec=edge,lw=.7)
        for hole in p.interiors:
            xy=np.asarray(hole.coords)
            ax.fill(xy[:,0],xy[:,1],color='white',ec=edge,lw=.7)

ax=axes[0]
for mesh,col in [(coxa,'#c6d3df'),(lower,'#a4bacb')]:
    polys=[Polygon(t[:,[0,2]]) for t in mesh.triangles]
    shape=unary_union([p for p in polys if p.area>1e-8])
    fill(ax,shape,col)
ax.plot([25,40],[-25,-25],color='#bd3c30',lw=2,ls='--')
ax.annotate('Access section at Z = -25',xy=(34,-25),xytext=(51,-35),
            arrowprops={'arrowstyle':'->','color':'#bd3c30'},color='#a93024',fontsize=11)
ax.annotate('Hip saddle and upper plate\nprovide a parallel load path',xy=(34,6),xytext=(17,36),
            arrowprops={'arrowstyle':'->','color':'#304d67'},ha='left',fontsize=11)
ax.annotate('Lower auxiliary arm',xy=(19,-49),xytext=(52,-53),
            arrowprops={'arrowstyle':'->','color':'#304d67'},fontsize=11)
ax.set(xlim=(-18,104),ylim=(-60,50),xlabel='Coxa local X (mm)',ylabel='Coxa local Z (mm)')
ax.set_aspect('equal')
ax.set_title('Actual coxa side projection',loc='left',fontsize=14,pad=12)
ax.grid(alpha=.18)

ax=axes[1]
cut=coxa.section(plane_normal=[0,0,1],plane_origin=[0,0,-25])
polys=[Polygon(p[:,[0,1]]) for p in cut.discrete]
shape=polys[0]
for p in polys[1:]:shape=shape.symmetric_difference(p)
reference=box(28,-8.5,36.5,8.5)
fill(ax,reference,'#f5c8c1','#bf7e72')
fill(ax,shape,'#c6d3df')
ax.text(32.25,10.4,'8.5 mm nominal width',ha='center',fontsize=11)
ax.annotate('Screw-access\nremoval',xy=(35.5,-7),xytext=(39,-5.5),
            arrowprops={'arrowstyle':'->','color':'#a93024'},color='#a93024',fontsize=11)
ax.text(26.5,0,'17 mm',rotation=90,va='center',fontsize=11)
ax.set(xlim=(25,46),ylim=(-11.8,12),xlabel='Coxa local X (mm)',ylabel='Coxa local Y (mm)')
ax.set_aspect('equal')
ax.set_title('Actual horizontal section',loc='left',fontsize=14,pad=12)
ax.grid(alpha=.18)

fig.suptitle('R4 post: real access cut, conditional load sharing',x=.06,y=.955,ha='left',fontsize=19,fontweight='bold')
fig.text(.06,.90,'Retained material is blue. Red shows material removed from the original rectangular post.',fontsize=12)
fig.text(.06,.15,'Net area: 124.53 mm²    |    Bending section modulus about Y: 140.70 mm³',fontsize=12,fontweight='bold')
fig.text(.06,.10,'Ordinary vertical load and full motor-torque allocation are separate screens. The screw access cuts the continuous post.',fontsize=11)
fig.text(.06,.055,'The lower nut-window coupon ends at Z = -28 and misses this cut. Test the complete production coxa with both yaw arms retained.',fontsize=11)
fig.savefig(OUT/'r4_post_section.png',dpi=140,facecolor='white')
plt.close(fig)
