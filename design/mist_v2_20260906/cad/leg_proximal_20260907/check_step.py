import json,hashlib
from pathlib import Path
import cadquery as cq
out=Path('cad/leg_proximal_20260907/output_candidate')
p=out/'MIST_proximal_robot_candidate.step'
r=json.loads((out/'leg_geometry_report.json').read_text())
shape=cq.importers.importStep(str(p)).val();solids=shape.Solids()
expected=sum(a['volume_cm3']*1000 for a in r['parts']);actual=sum(a.Volume() for a in solids)
result={'expected_solids':len(r['parts']),'imported_solids':len(solids),'all_solids_valid':all(s.isValid() and s.Volume()>0 for s in solids),'expected_volume_mm3':expected,'imported_volume_mm3':actual,'relative_volume_error':abs(actual-expected)/expected,'volume_relative_tolerance':1e-6,'source_STEP_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_report_sha256':hashlib.sha256((out/'leg_geometry_report.json').read_bytes()).hexdigest()}
assert result['imported_solids']==result['expected_solids'] and result['all_solids_valid']
assert result['relative_volume_error']<1e-6
(out/'step_roundtrip_check.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2),flush=True)
