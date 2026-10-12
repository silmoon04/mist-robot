#!/usr/bin/env python3
"""Audit/copy a checkpoint across one exact sensitivity JSON serializer repair.

Never edits source or original artifacts. Run only after training has finished.
The resulting artifact is for diagnostic revalidation, not resumed training.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import provenance as prov

KEY='locomotion/sensitivity.py'
BASELINE=Path(__file__).parent/'receipt_patch/sensitivity.before.py.txt'
OLD_SHA='3a685edcfc3a2c2a8fba6591339f137d95bdf4e11835876229b6a3e1aff8b6cc'
ANCHOR="HERE = Path(__file__).resolve().parent\n"
HELPER='''\n\ndef _json_scalar(value):
    # Receipt conversion only; unknown objects and nonfinite numbers still fail.
    import numpy as np
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Unsupported receipt value: {type(value).__name__}")
'''
OLD_LINE="json.dumps(result,indent=2)+'\\n'"
NEW_LINE="json.dumps(result,indent=2,allow_nan=False,default=_json_scalar)+'\\n'"


def approved_patch():
    original=BASELINE.read_bytes()
    if hashlib.sha256(original).hexdigest()!=OLD_SHA:
        raise ValueError('archived original source does not match reviewed hash')
    text=original.decode()
    if text.count(ANCHOR)!=1 or text.count(OLD_LINE)!=1:
        raise ValueError('serializer patch anchor is not unique')
    changed=text.replace(ANCHOR,ANCHOR+HELPER).replace(OLD_LINE,NEW_LINE).encode()
    return original,changed


def validate_transition(record,current,changed):
    original,expected=approved_patch()
    old=record['envelope']
    if prov.identity(old)!=record['envelope_sha256'] or old['contract']!=prov.CONTRACT:
        raise ValueError('original envelope/observation contract mismatch')
    if changed!=expected or old['sources'].get(KEY)!=OLD_SHA:
        raise ValueError('only the exact reviewed serializer patch is permitted')
    if set(current)!=set(old['sources']):
        raise ValueError('source inventory changed')
    differences={k for k in current if current[k]!=old['sources'][k]}
    if differences!={KEY} or current[KEY]!=hashlib.sha256(expected).hexdigest():
        raise ValueError('physical, training, contract or other tooling source changed')
    new=deepcopy(old)
    new['sources']=current
    if new['experiment']!=old['experiment'] or new['contract']!=old['contract']:
        raise ValueError('experiment semantics changed')
    return new


def migrate(checkpoint,output,replay=None):
    checkpoint=prov.checkpoint_path(checkpoint).resolve()
    output=Path(output).resolve()
    original_sidecar=checkpoint.with_suffix('.provenance.json')
    sidecar_bytes=original_sidecar.read_bytes()
    record=json.loads(sidecar_bytes)
    if record['checkpoint_sha256']!=prov.digest(checkpoint):
        raise ValueError('original checkpoint content mismatch')
    if record['algorithm'] not in ('ppo','sac'):
        raise ValueError('unsupported algorithm')
    if record['replay_sha256'] is not None:
        replay=Path(replay).resolve() if replay else Path(str(checkpoint.with_suffix(''))+'_replay_buffer.pkl')
        if prov.digest(replay)!=record['replay_sha256']:
            raise ValueError('original replay content mismatch')
    elif record['algorithm']=='sac':
        raise ValueError('SAC migration requires original matching replay')
    elif replay is not None:
        raise ValueError('unexpected replay artifact')
    frozen=prov.source_hashes()
    original,expected=approved_patch()
    new_env=validate_transition(record,frozen,(prov.REPO/KEY).read_bytes())
    output.mkdir(parents=True,exist_ok=False)
    destination=output/checkpoint.name
    migrated_sidecar=destination.with_suffix('.provenance.json')
    try:
        # Preserve a full byte snapshot, not only a list of prior hashes.
        snapshot=output/'original_source'
        for relative,sha in record['envelope']['sources'].items():
            src=prov.REPO/relative
            target=snapshot/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            if relative==KEY:target.write_bytes(original)
            else:shutil.copyfile(src,target)
            if prov.digest(target)!=sha:raise ValueError('source changed during snapshot')
        metadata=output/'original_metadata'
        metadata.mkdir()
        (metadata/'provenance.json').write_bytes(sidecar_bytes)
        shutil.copyfile(checkpoint,destination)
        destination_replay=None
        if replay is not None:
            destination_replay=output/(destination.stem+'_replay_buffer.pkl')
            shutil.copyfile(replay,destination_replay)
        prov.check_sources(frozen)
        if prov.digest(destination)!=record['checkpoint_sha256'] or (destination_replay and prov.digest(destination_replay)!=record['replay_sha256']):
            raise ValueError('artifact changed while copying')
        migrated=deepcopy(record)
        migrated.update(envelope=new_env,envelope_sha256=prov.identity(new_env),
                        status='diagnostic_revalidation_required_receipt_only_migration',
                        continuation_seed=None,hardware_qualified=False)
        migrated['migration']={'kind':'exact_sensitivity_json_serializer_only',
                              'old_envelope_sha256':record['envelope_sha256'],
                              'original_sidecar_sha256':hashlib.sha256(sidecar_bytes).hexdigest(),
                              'continuation':'disabled; original artifacts retain their continuation seed',
                              'tool_sha256':prov.digest(__file__)}
        migrated_sidecar.write_text(json.dumps(migrated,indent=2,allow_nan=False)+'\n')
        audit={'created_utc':datetime.now(timezone.utc).isoformat(),'old_envelope':record['envelope'],
               'new_envelope':new_env,'changed_source_keys':[KEY],'old_sensitivity_sha256':OLD_SHA,
               'new_sensitivity_sha256':hashlib.sha256(expected).hexdigest(),
               'checkpoint_sha256':prov.digest(destination),'replay_sha256':prov.digest(destination_replay) if destination_replay else None,
               'source_snapshot':'original_source','original_sidecar':'original_metadata/provenance.json','original_checkpoint':str(checkpoint),
               'status':migrated['status'],'physical_training_parameters_and_contract_unchanged':True,
               'patch':''.join(difflib.unified_diff(original.decode().splitlines(True),expected.decode().splitlines(True),fromfile=KEY,tofile=KEY)),
               'review_note':'Exact serializer conversion of NumPy scalar receipts; no score, simulation, optimizer or observation changes. Revalidate diagnostics before interpreting outputs.'}
        (output/'migration_audit.json').write_text(json.dumps(audit,indent=2,allow_nan=False)+'\n')
        prov.verify_checkpoint(destination,record['algorithm'],replay=destination_replay)
        if original_sidecar.read_bytes()!=sidecar_bytes or prov.digest(checkpoint)!=record['checkpoint_sha256']:
            raise ValueError('original artifact changed during migration')
        return destination
    except Exception:
        # Preserve incomplete evidence, but no valid-looking sidecar survives failure.
        migrated_sidecar.unlink(missing_ok=True)
        (output/'MIGRATION_FAILED').write_text('Incomplete migration. Do not load this output.\n')
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path)
    parser.add_argument('--replay',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    old,new=approved_patch()
    if args.checkpoint is None:
        print(''.join(difflib.unified_diff(old.decode().splitlines(True),new.decode().splitlines(True),fromfile=KEY,tofile=KEY)),end='')
        return
    if args.output is None:parser.error('--checkpoint requires new --output directory')
    print(migrate(args.checkpoint,args.output,args.replay))

if __name__=='__main__':main()
