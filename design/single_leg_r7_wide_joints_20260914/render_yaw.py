"""Show the wider operating range using the released assembly meshes."""
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

def main():
    d=json.loads((OUT/'manifest.json').read_text());fig,axes=plt.subplots(1,3,figsize=(15,6),facecolor='#f3f4f0')
    for ax,angle in zip(axes,[-55,0,55]):
        a=math.radians(angle);r=np.eye(4);r[:2,:2]=[[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]]
        tri=[];norm=[];col=[]
        for p in d['parts']:
            mesh=trimesh.load_mesh(OUT/p['assembly_stl']);frame=np.array(p['transform'])
            if p['link']!='base_mount':frame=r@frame
            mesh.apply_transform(frame);tri.append(mesh.triangles);norm.append(mesh.face_normals)
            colour='#697779' if p['link']=='base_mount' else '#303940' if p['material']=='servo' else '#b3bfc2' if p['material']=='metal' else '#38949a'
            col.append(np.tile(to_rgb(colour),(len(mesh.faces),1)))
        draw_mesh(ax,SimpleNamespace(triangles=np.concatenate(tri),normals=np.concatenate(norm),colors=np.concatenate(col)),camera_basis(90,-90))
        ax.axis('off');ax.set_aspect('equal');ax.set_xlim(-140,195);ax.set_ylim(-185,185);ax.set_facecolor('#f3f4f0');ax.set_title(f'{angle:+d} degrees' if angle else 'Centred',fontsize=16,color='#20383c')
    fig.suptitle('82 mm coxa: 110 degrees of provisional operating travel',fontsize=20,color='#20383c')
    fig.text(.5,.06,'Top views of the actual CAD assembly. Fixed bench mount stays in place.',ha='center',fontsize=12,color='#536268')
    fig.savefig(OUT/'Coxa_Wide_Range.png',dpi=160,facecolor=fig.get_facecolor(),bbox_inches='tight');plt.close(fig)

if __name__=='__main__':main()
