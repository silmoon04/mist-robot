import json,sys,math,hashlib
from pathlib import Path
import numpy as np
root=Path.cwd()
sys.path.insert(0,str(root/'simulation'))
import model
out=root/'cad'/'leg_output_checked_20260907'
r=json.loads((out/'leg_geometry_report.json').read_text())
p=json.loads(Path(r['parameters_path']).read_text())
q=model.neutral(p)
checks=[]
for i,name in enumerate(p['geometry']['leg_names']):
 actual=r['specifications'][name]['joint_centers_world_mm']
 expected=model.fk(p,i,q[i])
 errors={a:float(np.max(np.abs(np.array(actual[a])-np.array(expected[b])*1000))) for a,b in [('yaw','hip'),('hip','pitch'),('knee','knee'),('wheel','axle')]}
 assert max(errors.values())<1e-8,(name,errors)
 checks.append({'leg':name,'max_coordinate_error_mm':max(errors.values()),'pose_deg':np.degrees(q[i]).tolist()})
roundtrip=json.loads((out/'step_roundtrip_check.json').read_text())
for key,group in [('MIST_leg_FL_candidate','FL'),('MIST_robot_candidate',None)]:
 expected=sum(x['volume_cm3']*1000 for x in r['parts'] if group is None or x['group']==group)
 actual=roundtrip[key]['imported_volume_mm3']
 # STEP decimal serialization is compared at one part per million of solid volume.
 assert abs(actual-expected)<max(.01,expected*1e-6),(key,actual,expected)
 roundtrip[key].update(expected_volume_mm3=expected,absolute_volume_error_mm3=abs(actual-expected),relative_volume_tolerance=1e-6,relative_volume_error=abs(actual-expected)/expected)
(out/'step_roundtrip_check.json').write_text(json.dumps(roundtrip,indent=2))
(out/'simulation_coordinate_check.json').write_text(json.dumps({'passed':True,'checks':checks,'belt_center_mm':p['geometry']['femur_m']*1000,'parameters_sha256':r['parameters_sha256']},indent=2))
for path in [out/'leg_geometry_report.json',out/'leg_FL_geometry_report.json']:
 report=json.loads(path.read_text())
 for key in ('selected_leg','whole_robot'):
  if key in report['assembly_exports']: report['assembly_exports'][key].update(step_roundtrip_checked=True,step_roundtrip_evidence='step_roundtrip_check.json')
 path.write_text(json.dumps(report,indent=2))
print(json.dumps({'kinematic_checks':checks,'STEP_volumes_agree_within_one_ppm':True},indent=2))
