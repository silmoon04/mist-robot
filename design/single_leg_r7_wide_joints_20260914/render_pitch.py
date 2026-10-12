"""Show actual hip and knee range endpoints from the released mesh geometry."""
from pathlib import Path
import json,sys,math
from types import SimpleNamespace
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'
sys.path.insert(0,str(ROOT.parent/'hexapod_phone_quad_r5_20260912/review'))
from render_preview import draw_mesh,camera_basis

def pose(x=0,angle=0):
    a=math.radians(angle);t=np.eye(4);t[:3,:3]=[[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]];t[0,3]=x;return t

def main():
    manifest=json.loads((OUT/'manifest.json').read_text());fig,axes=plt.subplots(2,2,figsize=(12,10),facecolor='#f3f4f0')
    for ax,(hip,knee,title) in zip(axes.ravel(),[(-30,81,'Hip -30 degrees'),(65,81,'Hip +65 degrees'),(30,5,'Knee 5 degrees'),(30,115,'Knee 115 degrees')]):
        frames={'base_mount':np.eye(4),'coxa':np.eye(4),'femur':pose(82,hip)};frames['tibia']=frames['femur']@pose(90,knee)
        tri=[];norm=[];col=[]
        for p in manifest['parts']:
            mesh=trimesh.load_mesh(OUT/p['assembly_stl']);mesh.apply_transform(frames[p['link']]);tri.append(mesh.triangles);norm.append(mesh.face_normals)
            colour='#697779' if p['link']=='base_mount' else '#303940' if p['material']=='servo' else '#b3bfc2' if p['material']=='metal' else '#d3a65d' if 'cap' in p['name'] else '#38949a'
            col.append(np.tile(to_rgb(colour),(len(mesh.faces),1)))
        draw_mesh(ax,SimpleNamespace(triangles=np.concatenate(tri),normals=np.concatenate(norm),colors=np.concatenate(col)),camera_basis(10,-80))
        ax.axis('off');ax.set_aspect('equal');ax.set_xlim(-125,275);ax.set_ylim(-210,110);ax.set_facecolor('#f3f4f0');ax.set_title(title,fontsize=15,color='#20383c')
    fig.suptitle('R7: 95 degrees of hip travel and 110 degrees at the knee',fontsize=20,color='#20383c')
    fig.text(.5,.03,'Actual CAD endpoints. Hip is measured from horizontal; knee is the relative bend between links.',ha='center',fontsize=11,color='#536268')
    fig.savefig(OUT/'Hip_Knee_Range.png',dpi=150,facecolor=fig.get_facecolor(),bbox_inches='tight');plt.close(fig)

if __name__=='__main__':main()
