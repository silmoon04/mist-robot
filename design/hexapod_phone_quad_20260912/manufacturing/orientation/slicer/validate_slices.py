"""Check slice evidence, gzip storage and numerical accounting."""
from pathlib import Path
import gzip, hashlib, json

root=Path(__file__).resolve().parent
manifest=json.loads((root/'slice_manifest.json').read_text())
rows=manifest['jobs']
checks={
    'all_six_slices_succeeded':len(rows)==6 and all(r['return_code']==0 for r in rows),
    'all_motion_inside_225_225_265_mm':all(r['motion_inside_build_envelope'] for r in rows),
    'all_nominal_deposition_flow_below_8_mm3_s':all(r['peak_nominal_deposition_flow_mm3_s']<8 for r in rows),
    'extrusion_accounting_within_0_01_percent':all(abs(r['extrusion_accounting_difference_percent'])<0.01 for r in rows),
    'all_gzip_artifact_hashes_match':all(hashlib.sha256(Path(r['disabled_gcode_path']).read_bytes()).hexdigest()==r['disabled_gcode_sha256'] for r in rows),
    'all_saved_machine_commands_commented_out':all(
        all(not line.strip() or line.lstrip().startswith(';')
            for line in gzip.decompress(Path(r['disabled_gcode_path']).read_bytes()).decode().splitlines())
        for r in rows),
    'all_snapshot_hashes_match':all(hashlib.sha256((root/'ANALYSIS_ONLY'/(r['part']+'__'+r['orientation']+'.stl')).read_bytes()).hexdigest()==r['snapshot_sha256'] for r in rows),
    'frozen_definition_hash_matches':hashlib.sha256((root/'resolved_analysis.def.json').read_bytes()).hexdigest()==manifest['definition_sha256'],
    'no_temporary_machine_gcodes_remaining':not list((root/'ANALYSIS_ONLY').glob('*.temporary.gcode')),
}
result={'checks':checks,'all_checks_pass':all(checks.values()),
    'source_hashes_still_match_at_validation':all(
        hashlib.sha256((Path(manifest['source_directory'])/(r['part']+'.stl')).read_bytes()).hexdigest()==r['source_sha256'] for r in rows),
    'maximum_extrusion_accounting_difference_percent':max(abs(r['extrusion_accounting_difference_percent']) for r in rows),
    'maximum_nominal_deposition_flow_mm3_s':max(r['peak_nominal_deposition_flow_mm3_s'] for r in rows)}
(root/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['all_checks_pass'] else 1)
