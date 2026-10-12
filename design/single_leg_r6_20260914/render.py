"""Render the actual exported CAD meshes, without generative approximations."""
from pathlib import Path
import sys,json
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

def assembly(exploded=False):
    d=json.loads((OUT/'manifest.json').read_text());tri=[];norm=[];colors=[]
    for p in d['parts']:
        m=trimesh.load_mesh(OUT/p['assembly_stl']);t=np.array(p['transform'])
        if exploded:
            shift=[0,0,0]
            if 'auxiliary_cheek' in p['name']:shift=[0,-40,0]
            if 'case_cap_' in p['name']:shift=[0,0,-30] if p['link']!='base_mount' else [0,30,0]
            m.apply_translation(shift)
        m.apply_transform(t);tri.append(m.triangles);norm.append(m.face_normals)
        c='#323b40' if p['material']=='servo' else '#b3bfc2' if p['material']=='metal' else '#d3a65d' if 'cap' in p['name'] or 'spacer' in p['name'] else '#697779' if 'bench' in p['name'] else '#38949a'
        colors.append(np.tile(to_rgb(c),(len(m.faces),1)))
    return SimpleNamespace(triangles=np.concatenate(tri),normals=np.concatenate(norm),colors=np.concatenate(colors))

def main():
    for explode in (False,True):
        fig,ax=plt.subplots(figsize=(12,9),facecolor='#f3f4f0');ax.set_facecolor('#f3f4f0')
        draw_mesh(ax,assembly(explode),camera_basis(23,-64));ax.axis('off');ax.set_aspect('equal')
        fig.suptitle('Single leg R6: '+('removable caps and bearing cheeks' if explode else 'three servos and bench mount'),fontsize=19,color='#20383c')
        fig.text(.5,.04,'Actual CAD geometry | 82 / 90 / 105 mm joint lengths | one physical leg prototype',ha='center',fontsize=12,color='#536268')
        fig.savefig(OUT/('assembly_exploded.png' if explode else 'assembly.png'),dpi=160,facecolor=fig.get_facecolor(),bbox_inches='tight');plt.close(fig)

if __name__=='__main__':main()
