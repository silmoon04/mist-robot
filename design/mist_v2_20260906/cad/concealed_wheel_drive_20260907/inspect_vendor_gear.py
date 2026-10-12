from pathlib import Path
import json
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
p=Path('references/KHK_SM1_20/SM1-20_On.stp')
s=cq.importers.importStep(str(p)).val();b=s.BoundingBox()
r={'valid':s.isValid(),'solids':len(s.Solids()),'volume_mm3':s.Volume(),'center':s.Center().toTuple(),'bbox':[[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]],'cylinders':[]}
for f in s.Faces():
 if f.geomType()=='CYLINDER':
  c=BRepAdaptor_Surface(f.wrapped).Cylinder();a=c.Axis();v=a.Direction();q=a.Location()
  r['cylinders'].append({'radius':c.Radius(),'axis':[v.X(),v.Y(),v.Z()],'origin':[q.X(),q.Y(),q.Z()],'face_center':f.Center().toTuple()})
Path('cad/concealed_wheel_drive_20260907/vendor_gear_inspection.json').write_text(json.dumps(r,indent=2))
print(json.dumps(r,indent=2),flush=True)
