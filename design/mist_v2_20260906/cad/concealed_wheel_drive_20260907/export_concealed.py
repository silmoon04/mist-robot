"""Separate solid export for the concealed-wheel transmission candidate."""
from pathlib import Path
import argparse,datetime,hashlib,json,sys
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent))
sys.path.insert(0,str(HERE.parent/'leg_proximal_20260907'))
import export_leg as replay
from body_native import body_spec,COLORS as BODY_COLORS
from concealed_leg import leg_spec,COLORS
from inertia_report import enrich_report
from reference_shapes import enable_step_references

def export(parameters,output,include_body=False,leg='FL'):
    enable_step_references()
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    params=json.loads(Path(parameters).read_text())
    params['geometry']['tibia_m']=.140
    params['transmission']['topology']='proximal_femur_relative_knee'
    params['transmission']['motor_coordinate_equation']='s=[2*yaw,2*hip,2*knee]'
    params['wheel_transmission']=dict(topology='longitudinal_upper_tibia_shaft_miter_1to1',ratio=1,
        efficiency_assumption=.9,load_rating_verified=False)
    params['status']='concealed_wheel_interim_candidate_not_print_release'
    snapshot=output/'parameters_used.json';snapshot.write_text(json.dumps(params,indent=2))
    names=params['geometry']['leg_names'] if include_body else [leg]
    specs={name:leg_spec(params,name) for name in names}
    if include_body:specs['body']=body_spec(params)
    entries=[];palette=dict(BODY_COLORS,**COLORS)
    for group,spec in specs.items():
        for part in spec['parts']:
            tr=part.get('transform')
            if group=='body':
                tr=np.eye(4);tr[2,3]=spec['assembly_z_offset'];tr=tr.tolist()
            entries.append(dict(assembly_name=group+'__'+part['name'],group=group,part=part,transform=tr,
                                color_rgba=replay._rgba(part['color'],palette)))
    (output/'leg_recipes.json').write_text(json.dumps(specs,indent=2))
    local,world,rows,checks=replay._build(entries)
    report=dict(status=params['status'],generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        parameters_path=str(snapshot.resolve()),parameters_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        specifications=specs,parts=rows,shape_checks=checks,native_Fusion_executed=False,print_release=False)
    report.update(replay._mass_summary(rows))
    report['interference']=replay.pairwise_interference(world,rows)
    report['interference']['warning_free_negative_evidence']=not report['interference']['boolean_warnings']
    report['interference']['warning_policy']='A zero-volume result with kernel warnings is unresolved, not clearance proof. The phased OEM pair has a separate native Fusion check.'
    (output/'leg_geometry_report.json').write_text(json.dumps(report,indent=2))
    if include_body:enrich_report(report,local,world,entries,params)
    report['candidate_part_stls']=replay._export_candidate_parts(output,entries,local)
    report['assembly_exports']=replay._export_assembly(output,'MIST_concealed_'+('robot' if include_body else leg)+'_candidate',entries,world)
    report['exports_complete']=True
    (output/'leg_geometry_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(parts=len(rows),shape_checks=checks,
        positive_interferences=len(report['interference']['positive_volume_interferences']),
        boolean_failures=len(report['interference']['boolean_failures']),printed_mass_g=report['printed_solid_mass_g']),indent=2),flush=True)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--parameters',type=Path,default=ROOT/'simulation'/'design_parameters_20260907.json')
    parser.add_argument('--output',type=Path,default=HERE/'output_first')
    parser.add_argument('--include-body',action='store_true')
    parser.add_argument('--leg',default='FL')
    a=parser.parse_args();export(a.parameters,a.output,a.include_body,a.leg)
