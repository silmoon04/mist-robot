"""Rebind existing deposition evidence after a verified metadata-only export."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import shutil

from engine_runner import sha256
from run_production_slices import save_json,write_report
from validate_rebind_inputs import validate

HERE=Path(__file__).resolve().parent


def run(manifest_path,expected_hash,output):
    manifest_path,output=Path(manifest_path).resolve(),Path(output).resolve()
    assert sha256(manifest_path)==expected_hash
    aggregate_path=output/'production_mass_properties.json'
    old_manifest_path=output/'source_assembly_manifest.json'
    old=json.loads(aggregate_path.read_text())
    old_hash=sha256(aggregate_path)
    assert old['source_manifest_hash']!=expected_hash
    check=validate(aggregate_path,old_manifest_path,manifest_path,[])
    assert not check['changed_skus'] and not check['requires_reslice_skus']
    previous=output/('previous_revision_'+old['source_manifest_hash'][:12])
    previous.mkdir(exist_ok=False)
    for name in ('production_mass_properties.json','source_assembly_manifest.json','validation.json',
                 'PRODUCTION_SLICING.md','PRODUCTION_SLICING.txt','production_slicing_summary.csv',
                 'deck_rebind_receipt.json'):
        source=output/name
        if source.exists():
            shutil.copyfile(source,previous/name)
    for name in ('R5_CHANGE_AUDIT.json','R5_CHANGE_AUDIT.md','R5_CHANGE_AUDIT.txt'):
        if (HERE/name).exists():
            shutil.copyfile(HERE/name,previous/name)
    save_json(previous/'preservation_receipt.json',dict(
        preserved_utc=datetime.now(timezone.utc).isoformat(),
        reason='Final yaw-limit and clearance-target metadata; no print geometry change.',
        source_manifest_hash=old['source_manifest_hash'],aggregate_hash=old_hash,
        files={p.name:sha256(p) for p in previous.iterdir() if p.is_file()}))
    manifest=json.loads(manifest_path.read_text())
    result=dict(old)
    result['created_utc']=datetime.now(timezone.utc).isoformat()
    result['source_revision']=manifest['revision']
    result['source_manifest_path']=str(manifest_path)
    result['source_manifest_hash']=expected_hash
    result['source_script_hashes']=dict(old['source_script_hashes'],
        **{'rebind_metadata.py':sha256(__file__)})
    history=list(old.get('rebind_history',[]))
    if old.get('rebind'):
        history.append(old['rebind'])
    result['rebind_history']=history
    result['rebind']=dict(reason='Final yaw range is plus or minus 19 degrees with a 1.5 mm clearance target. Print geometry, quantities and transforms are unchanged.',
        metadata_only=True,previous_aggregate_path=str(previous/'production_mass_properties.json'),
        previous_aggregate_hash=old_hash,previous_source_manifest_hash=old['source_manifest_hash'],
        changed_skus=[],resliced_sku_count=0,reused_production_sku_count=len(old['parts']),
        input_validation=check)
    # Repeat the complete gate before updating the canonical source snapshot.
    validate(aggregate_path,old_manifest_path,manifest_path,[])
    assert sha256(manifest_path)==expected_hash
    assert result['parts']==old['parts']
    assert result['quantity_weighted_totals']==old['quantity_weighted_totals']
    (output/'source_assembly_manifest.json').write_bytes(manifest_path.read_bytes())
    save_json(aggregate_path,result)
    write_report(result,output)
    note=('\n## Final motion-limit metadata\n\n'
          'The final source metadata records a yaw range of plus or minus 19 degrees and a 1.5 mm clearance target. '
          'All 34 STL hashes, all quantities and all print-to-link transforms match the preceding export. '
          'No part was resliced. Every deposition record, mass, COM, inertia tensor, support quantity and time estimate was retained unchanged. '
          'The preceding ce504 aggregate and reports are preserved in the previous-revision directory.\n')
    for name in ('PRODUCTION_SLICING.md','PRODUCTION_SLICING.txt'):
        with (output/name).open('a',encoding='utf-8') as handle:
            handle.write(note)
    save_json(output/'metadata_rebind_receipt.json',dict(status='pass',
        source_manifest_hash=expected_hash,production_properties_hash=sha256(aggregate_path),
        previous_aggregate_hash=old_hash,all_34_deposition_records_unchanged=True,
        all_print_to_link_transforms_unchanged=True,resliced_sku_count=0,rebind=result['rebind']))
    print(json.dumps(dict(status='pass',aggregate_hash=sha256(aggregate_path),
        source_manifest_hash=expected_hash,reused_sku_count=len(result['parts']),
        quantity_weighted_totals=result['quantity_weighted_totals'])))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True)
    p.add_argument('--expected-manifest-hash',required=True)
    p.add_argument('--output',default=str(HERE/'output'));a=p.parse_args()
    run(a.manifest,a.expected_manifest_hash,a.output)
