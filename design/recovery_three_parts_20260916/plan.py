from pathlib import Path
import json
import numpy as np
import trimesh
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'third_leg_20260916'
targets={'femur_main_and_knee_saddle':[8.,10.5,37.9],'coxa_upper_and_hip_saddle':[8.495,9.],'tibia_curved_main_and_foot':[16.]}
rows=[]
for name,levels in targets.items():
 m=trimesh.load_mesh(OLD/'output/print_stl'/(name+'.stl'))
 for target in levels:
  top=(np.floor(target/.28)-2)*.28
  mask=(m.face_normals[:,2]<-.995)&(abs(m.triangles_center[:,2]-target)<.015)
  footprint=unary_union([Polygon(t[:,:2]) for t in m.triangles[mask]])
  lower=m.slice_plane([0,0,top+.2],[0,0,-1])
  obstacles=unary_union([Polygon(t[:,:2]) for t in lower.triangles if Polygon(t[:,:2]).area>1e-6])
  # Preserve narrow contact areas. Expand the foundation only where a
  # vertical path to the bed remains outside the model.
  contact=footprint.buffer(-.10).difference(obstacles.buffer(.4))
  qs=list(contact.geoms) if hasattr(contact,'geoms') else [contact]
  for q in qs:
   if q.area<1:continue
   foundation=q.buffer(2,join_style=2).difference(obstacles.buffer(.4))
   components=list(foundation.geoms) if hasattr(foundation,'geoms') else [foundation]
   foundation=max(components,key=lambda s:s.intersection(q).area)
   fins=[]
   xmin,ymin,xmax,ymax=q.bounds
   for x in np.arange(xmin+.4,xmax,.0+2.4):
    strip=foundation.intersection(box(x-.4,foundation.bounds[1]-1,x+.4,foundation.bounds[3]+1))
    for f in (list(strip.geoms) if hasattr(strip,'geoms') else [strip]):
     if f.area>.3 and f.intersection(q).area>.05:fins.append(list(f.exterior.coords)[:-1])
   if not fins:
    fins=[list(q.exterior.coords)[:-1]]
   rows.append({'part':name,'target_z_mm':target,'top_mm':top,'gap_mm':target-top,'base':list(foundation.exterior.coords)[:-1],
     'base_holes':[list(r.coords)[:-1] for r in foundation.interiors],'fins':fins,'contact':list(q.exterior.coords)[:-1]})
print([(r['part'],r['target_z_mm'],len(r['fins'])) for r in rows])
(ROOT/'support_plan.json').write_text(json.dumps(rows,indent=2))
