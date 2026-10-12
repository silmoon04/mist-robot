from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'cad'))
from geom import bounds,volume,centroid
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID,TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Curve
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).parent
r=STEPControl_Reader();r.ReadFile(str(root/'ST3215-3D_supplier/ST3215.step'));r.TransferRoots()
it=TopExp_Explorer(r.OneShape(),TopAbs_SOLID);solids=[]
while it.More():solids.append(it.Current());it.Next()
fig,axs=plt.subplots(4,4,figsize=(16,15))
for idx,s in enumerate(solids):
 print(idx, 'VOLUME',volume(s),'BBOX',bounds(s),'COM',centroid(s),flush=True)
 it=TopExp_Explorer(s,TopAbs_EDGE)
 while it.More():
  c=BRepAdaptor_Curve(TopoDS.Edge_s(it.Current()));p=[c.Value(float(t)) for t in np.linspace(c.FirstParameter(),c.LastParameter(),24)]
  p=np.array([[q.X(),q.Y(),q.Z()] for q in p])
  for ax,(i,j) in zip(axs.flat[idx*2:idx*2+2],[(0,1),(0,2)]):ax.plot(p[:,i],p[:,j],color='black',linewidth=.35)
  it.Next()
 for ax,label in zip(axs.flat[idx*2:idx*2+2],['XY','XZ']):ax.set_aspect('equal');ax.set_title(f'Solid {idx}, {label}');ax.grid(alpha=.2)
fig.tight_layout();fig.savefig(root/'supplier_solid_inventory.png',dpi=160)
