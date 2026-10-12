import sys,json,math
from pathlib import Path
import cadquery as cq
import numpy as np
sys.path.insert(0,str(Path('cad').resolve()))
from export_leg import place_shape,checked_overlap
s=cq.importers.importStep('references/KHK_SM1_20/SM1-20_On.stp').val()
driver=np.eye(4);driver[:3,:3]=[[1,0,0],[0,0,1],[0,-1,0]];driver[:3,3]=[0,20,-140]
a=place_shape(s,driver)
base=np.array([[1,0,0],[0,-1,0],[0,0,-1]],float)
rows=[]
for deg in range(19):
 t=math.radians(deg);R=np.array([[math.cos(t),0,math.sin(t)],[0,1,0],[-math.sin(t),0,math.cos(t)]])
 b=np.eye(4);b[:3,:3]=base@R;b[:3,3]=[0,20,-140]
 v,w=checked_overlap(a,place_shape(s,b));rows.append({'output_phase_deg':deg,'overlap_mm3':v,'warning':w})
 print(deg,v,flush=True)
Path('cad/concealed_wheel_drive_20260907/vendor_pair_phase_scan.json').write_text(json.dumps(rows,indent=2))
