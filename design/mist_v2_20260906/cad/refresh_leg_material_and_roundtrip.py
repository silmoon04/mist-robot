from pathlib import Path
import json,hashlib,datetime,sys,shutil
import cadquery as cq
sys.path.insert(0,str(Path('cad').resolve()))
from export_body import build_solids
from export_leg import _mass_summary
out=Path('cad/leg_output_checked_20260907')
report_path=out/'leg_geometry_report.json'
r=json.loads(report_path.read_text())
backup=out/'leg_geometry_report_before_material_refresh.json'
if not backup.exists(): shutil.copy2(report_path,backup)
source_hash=hashlib.sha256(backup.read_bytes()).hexdigest()
parts={group+'__'+p['name']:p for group,spec in r['specifications'].items() for p in spec['parts']}
free_shapes={}
for row in r['parts']:
 p=parts[row['assembly_name']]; printed=p['category']=='print'
 density=float(p.get('density_g_cm3',1.27))
 v=row['volume_cm3']
 if p.get('free_shape_ops'):
  result,checks=build_solids({'parts':[dict(p,ops=p['free_shape_ops'])]})
  shape=result[p['name']]
  assert not checks and shape.isValid() and len(shape.Solids())==1
  free_shapes[row['assembly_name']]=shape
  v=shape.Volume()/1000
 row.update(solid_material_mass_g=v*density if printed else None,
  material=p.get('material','PETG' if printed else 'reference'),
  mass_volume_cm3=v,assumed_density_g_cm3=density if printed else None)
for entry in r['candidate_part_stls']:
 name=entry['assembly_name']; p=parts[name]
 entry.update(material=p.get('material','PETG'),shape_state='assembled_part_local')
 if name in free_shapes:
  cq.exporters.export(free_shapes[name],entry['path'],tolerance=.1,angularTolerance=.15)
  entry.update(shape_state='uncompressed_free_state_print_recipe',free_thickness_mm=p['free_thickness_mm'],assembled_thickness_mm=p['assembled_thickness_mm'])
r.update(_mass_summary(r['parts']))
r['material_refresh']={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_geometry_report_sha256':source_hash,'intersection_results_unchanged':True,'assembly_STEP_GLB_unchanged':True,'free_pad_STLs_reexported':len(free_shapes),'geometry_export_process_exit_code':1,'process_exit_interpretation':'All requested geometry and exports completed before interpreter returned1 without a traceback; no clean process exit is claimed.'}
report_path.write_text(json.dumps(r,indent=2))
flp=out/'leg_FL_geometry_report.json'
fl=json.loads(flp.read_text())
fl.update(parts=[row for row in r['parts'] if row['group']=='FL'],candidate_part_stls=[x for x in r['candidate_part_stls'] if x['assembly_name'].startswith('FL__')],material_refresh=r['material_refresh'])
fl.update(_mass_summary(fl['parts']))
flp.write_text(json.dumps(fl,indent=2))
print(json.dumps({'material_print_mass_g':r['printed_solid_mass_g'],'FL_print_mass_g':fl['printed_solid_mass_g'],'free_pads':len(free_shapes)},indent=2),flush=True)
roundtrip={}
for label,expected in [('MIST_leg_FL_candidate',136),('MIST_robot_candidate',577)]:
 shape=cq.importers.importStep(str(out/(label+'.step'))).val()
 solids=shape.Solids()
 actual=len(solids)
 valid=all(s.isValid() and s.Volume()>0 for s in solids)
 assert actual==expected and valid,(label,actual,expected,valid)
 roundtrip[label]={'expected_solids':expected,'imported_solids':actual,'all_solids_valid':valid,'imported_volume_mm3':sum(s.Volume() for s in solids),'file_sha256':hashlib.sha256((out/(label+'.step')).read_bytes()).hexdigest()}
 print(label,actual,'valid STEP solids',flush=True)
(out/'step_roundtrip_check.json').write_text(json.dumps(roundtrip,indent=2))
