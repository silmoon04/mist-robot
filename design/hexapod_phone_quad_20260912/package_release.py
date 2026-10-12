"""Package the current checked design, excluding exploratory runs and runtime logs."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parent
NAME='HexQuad_Landscape_Print_Package'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_files():
    roots=['references','printing','review','cad','simulation','manufacturing','software']
    top=['README.md','README.txt','REQUIREMENTS.md','REQUIREMENTS.txt','settings.json','package_release.py']
    files=[ROOT/p for p in top if (ROOT/p).is_file()]
    for folder in roots:
        for p in (ROOT/folder).rglob('*'):
            if not p.is_file():
                continue
            rel=p.relative_to(ROOT)
            if any(part.startswith(('preliminary_','previous_revision_')) or part in
                   ('__pycache__','.venv','source_snapshot','ANALYSIS_ONLY','R2_COMPARISON_ONLY',
                    'R2_SOURCE_SNAPSHOTS','test_r2_only','pipeline_r2_smoke') for part in rel.parts):
                continue
            if p.suffix in ('.log','.pyc','.tmp') or p.name in ('quick_audit.json','posture_screen.json','construction_probe.json','fusion_probe.py'):
                continue
            if p.name.endswith('_response.json'):
                continue
            if rel.parts[0]=='simulation' and len(rel.parts)>2:
                if not rel.parts[1].startswith(('output_r4_','analysis_r4_')):
                    continue
            if rel.parts[0]=='manufacturing' and rel.parts[1] in ('baseline_r2','baseline_r3','slicing_r3'):
                continue
            if rel.parts[:2]==('manufacturing','knee_inward_study'):
                if len(rel.parts)>3 or p.suffix in ('.stl','.step','.zip') or p.name=='candidate_initial_flip.py':
                    continue
            if p.name=='INTERFACE_REVIEW_HOLD.txt' or p.name=='integration_r4.json':
                continue
            if rel.parts[:3]==('manufacturing','orientation','slicer') and len(rel.parts)>3:
                if p.name not in ('SLICER_COMPARISON.md','SLICER_COMPARISON.txt','validation.json','slice_manifest.json'):
                    continue
            files.append(p)
    return sorted(set(files))


def main():
    manifest=ROOT/'cad/output/assembly_manifest.json'
    cad=json.loads(manifest.read_text())
    if cad['revision']!='hex_quad_r4_inward_knee':
        raise RuntimeError('Current release requires the inward-knee R4 revision')
    if cad['parameters']!=json.loads((ROOT/'settings.json').read_text(encoding='utf-8')):
        raise RuntimeError('CAD parameters do not match current settings')
    for path,digest in cad['source_hashes'].items():
        if sha(manifest.parent.parent/path)!=digest:
            raise RuntimeError('CAD source is stale: '+path)
    static=json.loads((manifest.parent/'static_interference.json').read_text())
    if static['source_manifest_sha256']!=sha(manifest) or static['positive_intersections']:
        raise RuntimeError('Static geometry verification is stale or failed')
    motion=json.loads((manifest.parent/'full_motion_check.json').read_text())
    if motion['assembly_manifest_sha256']!=sha(manifest) or not motion['passed']:
        raise RuntimeError('Motion verification is stale or failed')
    staged=json.loads((manifest.parent/'r4_leg_staged_assembly_check.json').read_text(encoding='utf-8'))
    if not staged['accepted_staged_assembly_gate_passed'] or not staged['corrected_screw_and_driver_access_passed']:
        raise RuntimeError('Staged leg assembly has not passed')
    for path,digest in staged['source_sha256_before'].items():
        if sha(manifest.parent.parent/path)!=digest:
            raise RuntimeError('Leg interface evidence is stale: '+path)
    phone=json.loads((manifest.parent/'r4_phone_check.json').read_text(encoding='utf-8'))
    if phone['manifest_sha256']!=sha(manifest) or phone['status']!='pass' or not phone['inputs_unchanged']:
        raise RuntimeError('Phone verification is stale or failed')
    plate=json.loads((ROOT/'printing/plate_manifest.json').read_text())
    if plate['source_manifest_sha256']!=sha(manifest):
        raise RuntimeError('Print plates do not match final CAD')
    for row in plate['plates']:
        for key in ('stl','model_3mf'):
            if sha(ROOT/'printing'/row[key])!=row[key+'_sha256']:
                raise RuntimeError('Print plate changed: '+row[key])
    printed=ROOT/'cad/output/assembly_manifest_as_printed.json'
    data=json.loads(printed.read_text())
    if data['mass_model']['source_solid_manifest_sha256']!=sha(manifest):
        raise RuntimeError('Printed mass model is stale')
    slices=ROOT/'manufacturing/slicing_r4/output/production_mass_properties.json'
    if data['mass_model']['source_production_properties_sha256']!=sha(slices):
        raise RuntimeError('Printed mass properties changed')
    deposition=json.loads(slices.read_text(encoding='utf-8'))
    if deposition['source_manifest_hash']!=sha(manifest):
        raise RuntimeError('Sliced production geometry is stale')
    for row in deposition['parts']:
        if sha(manifest.parent/'print_stl'/(row['sku']+'.stl'))!=row['source_stl_hash']:
            raise RuntimeError('Printed STL changed: '+row['sku'])
    physics=json.loads((ROOT/'simulation/output_r4_printed_nominal/simulation_report.json').read_text())
    if physics['inputs']['manifest_sha256']!=sha(printed):
        raise RuntimeError('Simulation is stale')
    if physics['status']!='bounded_simulation_pass':
        raise RuntimeError('Nominal simulation did not meet its declared gates')
    browser=json.loads((ROOT/'review/runtime_check.json').read_text())
    if browser['source_manifest_sha256']!=sha(manifest) or browser['status']!='pass':
        raise RuntimeError('Interactive preview verification is stale')
    for path,digest in browser['viewer_source_sha256'].items():
        if sha(ROOT/'review'/path)!=digest:
            raise RuntimeError('Viewer changed after browser verification: '+path)
    native=json.loads((ROOT/'cad/output/fusion/progress.json').read_text())
    if not native.get('export_complete') or not native.get('joints_complete'):
        raise RuntimeError('Native export has not completed')
    step_hashes={name:sha(manifest.parent/link['step']) for name,link in cad['links'].items()}
    native_input=hashlib.sha256(manifest.read_bytes()+json.dumps(step_hashes,sort_keys=True).encode()).hexdigest()
    if native['input_sha256']!=native_input or native['source_step_sha256']!=step_hashes:
        raise RuntimeError('Native verification is stale')
    for name,digest in native['export_sha256'].items():
        filename=native['exports'][name].replace('\\','/').rsplit('/',1)[-1]
        if sha(ROOT/'cad/output/fusion'/filename)!=digest:
            raise RuntimeError('Native export changed: '+name)
    if native['native_interferences']['positive_volume_result_count']:
        raise RuntimeError('Native assembly contains interference')
    files=selected_files()
    records={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    checksum=ROOT/'CHECKSUMS.sha256'
    checksum.write_text(''.join(f'{digest}  {path}\n' for path,digest in records.items()),encoding='utf-8')
    out=ROOT/(NAME+'.zip')
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files+[checksum]:
            z.write(p,arcname=NAME+'/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        for path,digest in records.items():
            actual=hashlib.sha256(z.read(NAME+'/'+path)).hexdigest()
            assert actual==digest,path
    print(json.dumps({'archive':str(out),'files':len(files)+1,'bytes':out.stat().st_size,
                      'archive_sha256':sha(out),'source_manifest_sha256':sha(manifest)}))


if __name__=='__main__':
    main()
