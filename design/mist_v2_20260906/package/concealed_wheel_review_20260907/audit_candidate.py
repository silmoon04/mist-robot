"""Read-only inventory comparison of a supplied concealed-drive CAD report."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
BASE=ROOT/'cad/leg_proximal_20260907/output_candidate/leg_geometry_report.json'


def inventory(report):
    specs={(group,p['name']):p for group,spec in report['specifications'].items() for p in spec['parts']}
    rows=[]
    for part in report['parts']:
        spec=specs[(part['group'],part['name'])]
        mass=part.get('assigned_mass_g')
        if mass is None:
            mass=part.get('solid_material_mass_g')
        if mass is None:
            mass=spec.get('mass_g')
        if mass is None and 'density_g_cm3' in spec:
            mass=spec['density_g_cm3']*part['volume_cm3']
        rows.append(dict(name=part['name'],group=part['group'],category=part['category'],
                         link=part.get('link'),mass_g=mass,volume_cm3=part['volume_cm3'],
                         bounds_partlocal_mm=part['bounds_partlocal_mm'],note=part.get('note','')))
    return rows


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('report',type=Path)
    parser.add_argument('--label',default='candidate_audit')
    args=parser.parse_args()
    if not args.label.replace('_','').replace('-','').isalnum():
        raise ValueError('Use a filename-safe label')
    raw=args.report.read_bytes(); report=json.loads(raw)
    baseline=json.loads(BASE.read_bytes())
    rows=inventory(report); base_rows=inventory(baseline)
    fl=[r for r in rows if r['group']=='FL']
    base_fl={r['name']:r for r in base_rows if r['group']=='FL'}
    current_fl={r['name']:r for r in fl}
    changes=[]
    for name in sorted(set(base_fl)|set(current_fl)):
        a=base_fl.get(name,{}).get('mass_g') or 0
        b=current_fl.get(name,{}).get('mass_g') or 0
        if abs(b-a)>1e-6:
            changes.append(dict(name=name,baseline_g=a,candidate_g=b,delta_g=b-a))
    physics=report.get('physical_mass_properties') or {}
    interference=report.get('interference') or {}
    grouped=defaultdict(float)
    for row in rows:
        if row['mass_g'] is not None:
            grouped[row['group']]+=row['mass_g']
    result=dict(status='independent_report_review_not_new_CAD_verification',
                report_path=str(args.report.resolve()),report_sha256=hashlib.sha256(raw).hexdigest(),
                baseline_report_sha256=hashlib.sha256(BASE.read_bytes()).hexdigest(),
                part_count=len(rows),groups=sorted(grouped),group_assigned_g=dict(grouped),
                assigned_total_kg=physics.get('assigned_mass_kg'),
                baseline_assigned_total_kg=baseline['physical_mass_properties']['assigned_mass_kg'],
                shape_checks=report.get('shape_checks'),
                positive_interference_count=len(interference.get('positive_volume_interferences',[])),
                boolean_failure_count=len(interference.get('boolean_failures',[])),
                boolean_warning_count=len(interference.get('boolean_warnings',[])),
                tested_pose_only=interference.get('tested_pose_only'),
                FL_thermal_and_cover_g=sum((r['mass_g'] or 0) for r in fl if r['name'].startswith('TH')),
                FL_baseline_assigned_g=sum((r['mass_g'] or 0) for r in base_rows if r['group']=='FL'),
                FL_candidate_assigned_g=sum((r['mass_g'] or 0) for r in fl),
                FL_cover_g=sum((r['mass_g'] or 0) for r in fl if r['name'].startswith('TH03')),
                FL_heat_path_hardware_g=sum((r['mass_g'] or 0) for r in fl if r['name'].startswith(('TH01','TH02'))),
                largest_FL_mass_changes=sorted(changes,key=lambda r:abs(r['delta_g']),reverse=True)[:30],
                missing_FL_mass=[r['name'] for r in fl if r['mass_g'] is None],
                remaining_old_foot_drive_parts=[r['name'] for r in fl if r['name'].startswith(('W05','W06','W07','W08','W09'))],
                motor_and_cover_bounds=[r for r in fl if r['name'].startswith(('CW01','TH03'))],
                relevant_interfaces=[r for r in fl if r['name'].startswith(('CW03','CW04','CW05','CW07','CW08','CW12','CW13'))])
    if result['assigned_total_kg'] is not None:
        result['delta_total_kg']=result['assigned_total_kg']-result['baseline_assigned_total_kg']
        result['delta_total_percent']=100*result['delta_total_kg']/result['baseline_assigned_total_kg']
    (HERE/(args.label+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    compact={k:v for k,v in result.items() if k not in ('largest_FL_mass_changes','motor_and_cover_bounds','relevant_interfaces')}
    print(json.dumps(compact,indent=2))
    for row in result['largest_FL_mass_changes'][:12]:
        print(f"{row['delta_g']:+8.2f} g  {row['name']}")


if __name__=='__main__':main()
