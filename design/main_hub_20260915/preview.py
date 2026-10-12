from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np,trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'
sys.path.insert(0,str(ROOT.parent/'hexapod_phone_quad_r5_20260912/review'))
from render_preview import draw_mesh,camera_basis
m=trimesh.load_mesh(OUT/'Main_Hub_4Leg.stl')
a=SimpleNamespace(triangles=m.triangles,normals=m.face_normals,colors=np.tile(to_rgb('#58acbd'),(len(m.faces),1)))
fig,ax=plt.subplots(figsize=(11,9),facecolor='#f3f4f0');ax.set_facecolor('#f3f4f0');draw_mesh(ax,a,camera_basis(52,-65));ax.axis('off');ax.set_aspect('equal');ax.set_title('Four-leg centre hub | one piece, flat underside',fontsize=18)
fig.savefig(OUT/'Hub_Preview.png',dpi=150,bbox_inches='tight');plt.close(fig)
