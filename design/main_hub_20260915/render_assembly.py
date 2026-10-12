from pathlib import Path
import json,sys,math
from types import SimpleNamespace
import numpy as np,trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output';LEG=ROOT.parent/'print_dfm_20260914/output'
sys.path.insert(0,str(ROOT.parent/'hexapod_phone_quad_r5_20260912/review'))
from render_preview import draw_mesh,camera_basis
def main():
    tri=[];norm=[];colors=[]
    def append(m,c):tri.append(m.triangles);norm.append(m.face_normals);colors.append(np.tile(to_rgb(c),(len(m.faces),1)))
    append(trimesh.load_mesh(OUT/'Main_Hub_4Leg.stl'),'#54b4ca');data=json.loads((LEG/'manifest.json').read_text())
    for deg,c in [(45,'#ddb373'),(-45,'#d39292'),(135,'#af9cd1'),(-135,'#8bb994')]:
        a=math.radians(deg);t=np.eye(4);t[:2,:2]=[[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]];t[:3,3]=[75*math.cos(a),75*math.sin(a),38]
        for p in data['parts']:
            if p['name']=='bench_mounting_plate':continue
            m=trimesh.load_mesh(LEG/p['assembly_stl']);m.apply_transform(t@np.array(p['transform']));append(m,'#445359' if p['material']=='servo' else '#cbd1d3' if p['material']=='metal' else c)
    obj=SimpleNamespace(triangles=np.concatenate(tri),normals=np.concatenate(norm),colors=np.concatenate(colors))
    fig,ax=plt.subplots(figsize=(12,10),facecolor='#f3f4f0');ax.set_facecolor('#f3f4f0');draw_mesh(ax,obj,camera_basis(49,-67));ax.axis('off');ax.set_aspect('equal')
    fig.suptitle('The centre hub connects all four existing leg assemblies',fontsize=18,color='#243b40')
    fig.text(.5,.035,'Blue: tonight\'s hub. Legs and servo saddles are shown for assembly context and are not on this plate.',ha='center',fontsize=11)
    fig.savefig(OUT/'Hub_With_Legs_Preview.png',dpi=150,bbox_inches='tight');plt.close(fig)

if __name__=='__main__':main()
