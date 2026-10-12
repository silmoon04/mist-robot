"""Convert a complete measured-CAD inventory into explicit URDF inertials."""
from pathlib import Path
import argparse
import hashlib
import json
import math
from model import build_urdf,total_mass,validate_link_mass_properties


def reconcile(report_path,output):
    report_path=Path(report_path)
    raw=report_path.read_bytes()
    report=json.loads(raw)
    source=Path(report['parameters_path'])
    params=json.loads(source.read_text())
    names=params['geometry']['leg_names']
    if set(report['specifications'])!=set(names)|{'body'}:
        raise ValueError('Need the full four-leg and body export, not a single-leg inventory')
    if not report.get('exports_complete') or report.get('shape_checks'):
        raise ValueError('CAD exports and shape validation must have completed')
    properties=report.get('link_mass_properties',{})
    expected={'base_link'}|{name+suffix for name in names for suffix in ('_yaw','_femur','_tibia','_wheel')}
    if set(properties)!=expected or any(not value.get('has_geometry') for value in properties.values()):
        raise ValueError('All seventeen rigid bodies need actual CAD mass allocations')
    if report['physical_mass_properties']['units']['inertia']!='kg m^2':
        raise ValueError('Unexpected inertia units')
    params['link_mass_properties']={name:dict(mass_kg=value['mass_kg'],com_m=value['com_local_m'],
        inertia_kg_m2=value['inertia_com_local_kg_m2']) for name,value in properties.items()}
    params['transmission'].update(topology='proximal_femur_relative_knee',knee_motor_mount='femur',
        motor_coordinate_equation='s=[2*yaw,2*hip,2*knee]; normalized actuator directions, physical commissioning pending')
    params['mass']['knee_servo_com_m']=[x/1000 for x in report['specifications'][names[0]]['knee_servo_com_femur_mm']]
    params['mass']['provenance']='The per-link CAD inertials are authoritative for this simulation. Older scalar component allowances remain only for compatibility and must not be summed as the new robot mass.'
    interference=report['interference']
    params['cad_evidence']={
        'report_path':str(report_path.resolve()),'report_sha256':hashlib.sha256(raw).hexdigest(),
        'part_count':len(report['parts']),
        'positive_volume_interferences':len(interference['positive_volume_interferences']),
        'boolean_failures':len(interference['boolean_failures']),
        'collision_geometry_in_urdf':'Simplified primitive links, not final CAD meshes',
        'material_mass_assumptions':report['physical_mass_properties']['assumptions'],
        'internal_rotors':'Mass and pose inertia included in housing links; independent rotor kinetic energy omitted',
        'physical_fit_validated':False,'production_release':False}
    params['status']='proximal_CAD_inertia_sensitivity_not_structural_or_collision_release'
    validate_link_mass_properties(params)
    mass=total_mass(params)
    accounted=report['physical_mass_properties']['assigned_mass_kg']
    if not math.isclose(mass,accounted,rel_tol=1e-10,abs_tol=1e-10):
        raise ValueError('URDF and CAD inventory mass disagree')
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    path=output/'parameters_cad_inertials.json'
    path.write_text(json.dumps(params,indent=2),encoding='utf-8')
    build_urdf(params,output/'MIST_proximal_cad_inertials.urdf')
    summary=dict(status=params['status'],accounted_mass_kg=mass,source_report_sha256=hashlib.sha256(raw).hexdigest(),
                 parameters_path=str(path.resolve()),cad_evidence=params['cad_evidence'])
    (output/'reconciliation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
    return path


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    reconcile(args.report,args.output)
