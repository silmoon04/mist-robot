import json,sys
from pathlib import Path
sys.path.insert(0,str(Path('cad').resolve()))
from leg_native import leg_spec
from export_body import tool_shape
from export_leg import place_shape,checked_overlap
p=json.loads(Path('simulation/design_parameters_20260907.json').read_text())
spec=leg_spec(p)
by={a['name']:a for a in spec['parts']}
servo=by['S01_C018_yaw_CASE']
shape=place_shape(tool_shape(servo['ops'][0]),servo['transform'])
for i,op in enumerate(by['Y01_fixed_mount_bridge']['ops']):
 if op['mode']=='cut': continue
 test=place_shape(tool_shape(op),by['Y01_fixed_mount_bridge']['transform'])
 v,w=checked_overlap(test,shape)
 if v>.01: print(i+1,op,v,flush=True)
