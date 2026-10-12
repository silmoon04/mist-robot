import importlib.util
import json
from pathlib import Path
import hashlib
import numpy as np
import pytest

PATH=Path(__file__).parents[1]/'scripts/migrate_receipt_only.py'
spec=importlib.util.spec_from_file_location('receipt_migration',PATH)
migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)


def fixture(tmp_path,monkeypatch):
    old,new=migration.approved_patch()
    repo=tmp_path/'repo';(repo/'locomotion').mkdir(parents=True)
    (repo/migration.KEY).write_bytes(new)
    model=repo/'locomotion/mist_env.py';model.write_bytes(b'unchanged physical model')
    oldhash={migration.KEY:migration.OLD_SHA,'locomotion/mist_env.py':migration.prov.digest(model)}
    env={'schema':1,'sources':oldhash,'contract':migration.prov.CONTRACT,'experiment':{'sensor':{'mode':'none','profile':None},'algorithm_parameters':{'learning_rate':.0003}}}
    checkpoint=tmp_path/'original.zip';checkpoint.write_bytes(b'exact weights')
    replay=tmp_path/'original_replay_buffer.pkl';replay.write_bytes(b'exact replay')
    record={'envelope':env,'envelope_sha256':migration.prov.identity(env),'checkpoint_sha256':migration.prov.digest(checkpoint),'replay_sha256':migration.prov.digest(replay),'algorithm':'sac','status':'candidate','continuation_seed':1042,'hardware_qualified':False}
    checkpoint.with_suffix('.provenance.json').write_text(json.dumps(record))
    monkeypatch.setattr(migration.prov,'REPO',repo)
    monkeypatch.setattr(migration.prov,'source_hashes',lambda:{k:migration.prov.digest(repo/k) for k in oldhash})
    return checkpoint,replay,record


def test_exact_scalar_serializer_only():
    import ast
    old,new=migration.approved_patch()
    before=ast.parse(old);after=ast.parse(new)
    # All preexisting functions other than main are AST-identical.
    original={n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
    updated={n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
    assert all(original[k]==updated[k] for k in original if k!='main')
    scope={};node=next(n for n in after.body if isinstance(n,ast.FunctionDef) and n.name=='_json_scalar')
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<serializer>','exec'),scope)
    encoder=scope['_json_scalar']
    assert json.loads(json.dumps({'checks':{'progress':np.bool_(False)},'metric':np.float64(.5)},default=encoder,allow_nan=False))=={'checks':{'progress':False},'metric':.5}
    with pytest.raises(TypeError):json.dumps(object(),default=encoder)
    with pytest.raises(ValueError):json.dumps(np.float64(float('nan')),default=encoder,allow_nan=False)


def test_migration_preserves_original_and_semantics(tmp_path,monkeypatch):
    checkpoint,replay,record=fixture(tmp_path,monkeypatch)
    sidecar=checkpoint.with_suffix('.provenance.json').read_bytes()
    destination=migration.migrate(checkpoint,tmp_path/'migrated')
    out=json.loads(destination.with_suffix('.provenance.json').read_text())
    assert checkpoint.with_suffix('.provenance.json').read_bytes()==sidecar
    assert (destination.parent/'original_metadata/provenance.json').read_bytes()==sidecar
    assert destination.read_bytes()==checkpoint.read_bytes()
    assert (destination.parent/'original_replay_buffer.pkl').read_bytes()==replay.read_bytes()
    assert out['envelope']['experiment']==record['envelope']['experiment']
    assert out['envelope']['contract']==record['envelope']['contract']
    assert out['continuation_seed'] is None
    assert out['status']=='diagnostic_revalidation_required_receipt_only_migration'
    assert (destination.parent/'original_source'/migration.KEY).read_bytes()==migration.approved_patch()[0]
    with pytest.raises(FileExistsError):migration.migrate(checkpoint,tmp_path/'migrated')


@pytest.mark.parametrize('changed',['weights','replay','physics','serializer','envelope'])
def test_migration_rejects_any_unapproved_change(tmp_path,monkeypatch,changed):
    checkpoint,replay,record=fixture(tmp_path,monkeypatch)
    if changed=='weights':checkpoint.write_bytes(b'other weights')
    elif changed=='replay':replay.write_bytes(b'other replay')
    elif changed=='physics':(migration.prov.REPO/'locomotion/mist_env.py').write_bytes(b'changed physics')
    elif changed=='serializer':
        p=migration.prov.REPO/migration.KEY;p.write_bytes(p.read_bytes()+b'\n# extra unreviewed edit\n')
    else:
        record['envelope']['experiment']['algorithm_parameters']['learning_rate']=.2
        checkpoint.with_suffix('.provenance.json').write_text(json.dumps(record))
    with pytest.raises(ValueError):migration.migrate(checkpoint,tmp_path/'migrated')
    assert not (tmp_path/'migrated').exists()


def test_original_named_checkpoint_cannot_overwrite_archived_sidecar(tmp_path,monkeypatch):
    checkpoint,_,record=fixture(tmp_path,monkeypatch)
    original=checkpoint.with_suffix('.provenance.json').read_bytes()
    destination=migration.migrate(checkpoint,tmp_path/'migrated')
    assert destination.name=='original.zip'
    assert (destination.parent/'original_metadata/provenance.json').read_bytes()==original
    assert json.loads((destination.parent/'original_metadata/provenance.json').read_text())['status']=='candidate'
    assert json.loads(destination.with_suffix('.provenance.json').read_text())['status'].startswith('diagnostic_')


def test_late_failure_removes_generated_sidecar_but_preserves_archive(tmp_path,monkeypatch):
    checkpoint,_,_=fixture(tmp_path,monkeypatch)
    original=checkpoint.with_suffix('.provenance.json').read_bytes()
    def fail_verification(*args,**kwargs):
        raise RuntimeError('injected final verification failure')
    monkeypatch.setattr(migration.prov,'verify_checkpoint',fail_verification)
    output=tmp_path/'failed'
    with pytest.raises(RuntimeError,match='injected final verification'):
        migration.migrate(checkpoint,output)
    assert (output/'MIGRATION_FAILED').is_file()
    assert not (output/checkpoint.name).with_suffix('.provenance.json').exists()
    assert (output/'original_metadata/provenance.json').read_bytes()==original
    assert checkpoint.with_suffix('.provenance.json').read_bytes()==original
