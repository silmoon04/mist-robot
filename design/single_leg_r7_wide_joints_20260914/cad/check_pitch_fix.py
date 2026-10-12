import json
import build,geom as g
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
parts,frames=build.load_assembly(0,30,120)
a=next(p['shape'] for p in parts if p['name']=='femur_main_and_knee_saddle')
b=next(p['shape'] for p in parts if p['name']=='tibia_curved_main_and_foot')
b=build.shape_at(b,build.pose((90,0,0),(0,120,0)))
d=BRepExtrema_DistShapeShape(a,b);d.Perform()
print('Main knee at 120',g.common_volume(a,b),d.Value(),flush=True)
a=next(p['shape'] for p in parts if p['name']=='femur_auxiliary_cheek')
b=next(p['shape'] for p in parts if p['name']=='tibia_auxiliary_cheek')
b=build.shape_at(b,build.pose((90,0,0),(0,120,0)))
d=BRepExtrema_DistShapeShape(a,b);d.Perform()
print('Auxiliary knee at 120',g.common_volume(a,b),d.Value(),flush=True)
