"""Find model cross-sections that start above air in the supplied print pose."""
from pathlib import Path
import json
import numpy as np
import trimesh
from shapely.geometry import Polygon, GeometryCollection
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'print_dfm_20260914/output'
manifest=json.loads((OLD/'manifest.json').read_text())
names=['coxa_upper_and_hip_saddle','femur_main_and_knee_saddle','tibia_curved_main_and_foot','case_cap_hip','yaw_case_saddle']
results=[]
for name in names:
    p=next(p for p in manifest['parts'] if p['name']==name)
    m=trimesh.load_mesh(OLD/p['print_stl'])
    prev=GeometryCollection(); islands=[]
    for i,z in enumerate(np.arange(.14,m.bounds[1,2],.28)):
        section=m.section([0,0,1],[0,0,z])
        if section is None: continue
        polys=[Polygon(curve[:,:2]) for curve in section.discrete]
        polys=[q for q in polys if q.is_valid and q.area>1e-5]
        # Symmetric difference retains holes regardless of loop winding.
        area=GeometryCollection()
        for q in polys:area=area.symmetric_difference(q)
        components=list(area.geoms) if hasattr(area,'geoms') else [area]
        if i:
            for q in components:
                if q.area>.5 and q.distance(prev)>.45:
                    islands.append({'layer':i,'z_mm':float(z),'area_mm2':q.area,'bounds_xy_mm':list(q.bounds),'distance_to_previous_mm':q.distance(prev)})
        prev=area
    results.append({'part':name,'new_model_islands':islands})
    print(name,islands,flush=True)
(ROOT/'island_screen.json').write_text(json.dumps(results,indent=2))
