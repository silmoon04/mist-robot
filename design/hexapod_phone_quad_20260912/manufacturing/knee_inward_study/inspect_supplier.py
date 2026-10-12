from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'cad'))
from geom import bounds, volume
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID, TopAbs_EDGE, TopAbs_FACE
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).parent
reader=STEPControl_Reader()
reader.ReadFile(str(root/'ST3215-3D_supplier/ST3215.step'))
reader.TransferRoots()
shape=reader.OneShape()
print('ALL', bounds(shape))
it=TopExp_Explorer(shape,TopAbs_SOLID)
solids=[]
while it.More():
    s=it.Current(); solids.append(s)
    print('SOLID',len(solids)-1,'bounds',bounds(s),'volume',volume(s))
    it.Next()
fig,axs=plt.subplots(1,3,figsize=(18,7))
for idx,s in enumerate(solids):
    it=TopExp_Explorer(s,TopAbs_EDGE)
    while it.More():
        curve=BRepAdaptor_Curve(TopoDS.Edge_s(it.Current()))
        points=[curve.Value(float(t)) for t in np.linspace(curve.FirstParameter(),curve.LastParameter(),18)]
        p=np.array([[p.X(),p.Y(),p.Z()] for p in points])
        for ax,(i,j) in zip(axs,[(0,1),(0,2),(1,2)]):
            ax.plot(p[:,i],p[:,j],linewidth=.35,color=plt.cm.tab10(idx%10))
        it.Next()
for ax,label in zip(axs,['XY','XZ','YZ']):
    ax.set_aspect('equal'); ax.set_title(label); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(root/'supplier_orthographic.png',dpi=180)
fig,ax=plt.subplots(figsize=(12,7))
it=TopExp_Explorer(solids[2],TopAbs_EDGE)
while it.More():
    curve=BRepAdaptor_Curve(TopoDS.Edge_s(it.Current()))
    points=[curve.Value(float(t)) for t in np.linspace(curve.FirstParameter(),curve.LastParameter(),18)]
    p=np.array([[p.X(),p.Y(),p.Z()] for p in points])
    if p[:,1].min() < -23:
        ax.plot(p[:,0],p[:,2],linewidth=.7,color='black')
    it.Next()
ax.set_aspect('equal'); ax.set_xlabel('Supplier X (mm)'); ax.set_ylabel('Supplier Z (mm)'); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(root/'supplier_auxiliary_edges.png',dpi=180)
it=TopExp_Explorer(solids[2],TopAbs_FACE)
while it.More():
    face=TopoDS.Face_s(it.Current()); b=bounds(face)
    if b[0][1] < -23 and b[0][0]>-20 and b[1][0]<-10:
        print('PORT_REGION_FACE',b)
    it.Next()
