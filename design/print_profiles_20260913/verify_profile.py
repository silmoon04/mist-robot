"""Check the exported profile and record a bounded first-plate engine trial."""
from pathlib import Path
import gzip
import hashlib
import importlib.util
import json
import sys
import zipfile
from build_profile import HERE,FILE,CURA,VALUES


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser_file=CURA/'UM/FastConfigParser.py'
    spec=importlib.util.spec_from_file_location('installed_cura_parser',parser_file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    merged={}
    with zipfile.ZipFile(FILE) as archive:
        for name in archive.namelist():
            parsed=module.FastConfigParser(archive.read(name).decode('utf-8'))
            assert parsed['general']['definition']=='elegoo_neptune_4'
            assert parsed['metadata']['quality_type']=='Elegoo_layer_020'
            merged.update(parsed['values'])
    assert merged=={k:str(v) for k,v in VALUES.items()}
    pipeline=HERE.parent/'hexapod_phone_quad_r5_20260912/manufacturing/slicing_r5'
    sys.path.insert(0,str(pipeline))
    from deposition_properties import parse_gcode
    run=json.loads((HERE/'analysis/slice_run.json').read_text(encoding='utf-8'))
    raw=Path(run['raw_temporary_path'])
    archived=HERE/'analysis/first_plate.ANALYSIS_ONLY.gcode.gz'
    if raw.exists():
        text=raw.read_text(encoding='utf-8')
    else:
        lines=gzip.decompress(archived.read_bytes()).decode('utf-8').splitlines()
        text='\n'.join(line.removeprefix('; DISABLED| ') for line in lines)
    result=parse_gcode(text,run['gcode_to_source_transform'])
    assert result['unclassified_deposition_is_zero']
    support=result['properties']['support']['mass_g']
    assert support>0
    flow=max(p.get('peak_nominal_deposition_flow_mm3_s',0) for p in result['properties'].values())
    assert flow<=8.1,flow
    assert run['motion_inside_build_envelope']
    if raw.exists():
        inert='; ANALYSIS ONLY. ALL MACHINE COMMANDS DISABLED. DO NOT PRINT.\n'
        inert+='\n'.join(line if line.lstrip().startswith(';') or not line.strip()
                        else '; DISABLED| '+line for line in text.splitlines())+'\n'
        archived.write_bytes(gzip.compress(inert.encode('utf-8')))
        assert raw.resolve().parent==(HERE/'analysis').resolve()
        raw.unlink()
    validation=json.loads((HERE/'profile_validation.json').read_text(encoding='utf-8'))
    validation['checks'].append('Both members parse with the installed Cura FastConfigParser')
    validation['installed_parser_sha256']=sha(parser_file)
    validation['first_plate_trial']={
        'engine_version':run['engine_version'],'source_stl_sha256':run['source_sha256'],
        'return_code':run['return_code'],'model_PLA_g':result['properties']['model']['mass_g'],
        'support_PLA_g':support,'adhesion_PLA_g':result['properties']['adhesion']['mass_g'],
        'estimated_hours':run['estimated_time_seconds']/3600,
        'peak_nominal_flow_mm3_s':flow,'motion_bounds_mm':run['motion_bounds_mm'],
        'checked_build_volume_mm':run['build_envelope_mm'],'motion_inside_bed':True,
        'profile_overrides_match':run['settings_overrides']==VALUES,
        'method':'Process overrides from the profile applied to the existing explicit numeric CuraEngine analysis stack. This is not a live Cura frontend import test.',
        'start_end_code':'Disabled for analysis; the import profile inherits the selected printer startup code.',
        'toolpath_archive_sha256':sha(archived)}
    assert validation['first_plate_trial']['profile_overrides_match']
    (HERE/'profile_validation.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    print(json.dumps(validation['first_plate_trial'],indent=2))


if __name__=='__main__':main()
