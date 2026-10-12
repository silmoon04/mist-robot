"""Place open, removable combs under the knee saddle's flat underside."""
from pathlib import Path
import json
import numpy as np
import trimesh
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parent
n='femur_main_and_knee_saddle'
m=trimesh.load_mesh(ROOT/'output/print_stl'/(n+'.stl'))
target=10.5; top=9.8
mask=(m.face_normals[:,2]<-.999)&(abs(m.triangles_center[:,2]-target)<.001)
foot=unary_union([Polygon(t[:,:2]) for t in m.triangles[mask]])
lower=m.slice_plane([0,0,top+.2],[0,0,-1])
obstacles=unary_union([Polygon(t[:,:2]) for t in lower.triangles if Polygon(t[:,:2]).area>1e-6])
allowed=foot.buffer(-.35).difference(obstacles.buffer(.35))
components=list(allowed.geoms) if hasattr(allowed,'geoms') else [allowed]
records=[]
for q in components:
    if q.area<8:continue
    xmin,ymin,xmax,ymax=q.bounds
    fins=[]
    for x in np.arange(xmin+.4,xmax,.0+3):
        strip=q.intersection(box(x-.4,ymin-1,x+.4,ymax+1))
        pieces=list(strip.geoms) if hasattr(strip,'geoms') else [strip]
        for s in pieces:
            if s.area>.5:fins.append(list(s.exterior.coords)[:-1])
    if fins:records.append({'base':list(q.exterior.coords)[:-1],'base_holes':[list(r.coords)[:-1] for r in q.interiors],'fins':fins,'height_mm':top})
result={'part':n,'underside_z_mm':target,'support_top_z_mm':top,'nominal_gap_mm':target-top,'combs':records,
        'coverage_scope':'Flat knee-saddle underside at 10.5 mm only. Existing automatic support handles other surfaces.'}
(ROOT/'support_plan.json').write_text(json.dumps(result,indent=2))
print('COMBS',len(records),'FINS',sum(len(r['fins']) for r in records),'AREA',sum(Polygon(r['base']).area for r in records))
