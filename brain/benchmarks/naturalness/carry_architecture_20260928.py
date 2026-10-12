"""Verify and carry unaffected pre-correction samples into the corrected run."""
import hashlib
import json
from pathlib import Path

from architecture_comparison_20260928 import BRAIN, ARMS, make_schedule, SOURCE_FILES, calibration_architectures
from duplex.live_studio import ARCHITECTURES

base = BRAIN / 'results/architecture-cost-20260928'
old_dir = base / 'model-pre-correction'
new_dir = base / 'model'
old = json.loads((base / 'cases.pre-correction.json').read_text(encoding='utf-8'))
new = json.loads((base / 'cases.json').read_text(encoding='utf-8'))
manifest = json.loads((old_dir / 'manifest.json').read_text(encoding='utf-8'))
rows = [json.loads(line) for line in (old_dir / 'results.jsonl').read_text(encoding='utf-8').splitlines()]
assert hashlib.sha256((base / 'cases.pre-correction.json').read_bytes()).hexdigest() == manifest['suite_sha256']
assert len(rows) == 17
assert all(hashlib.sha256((BRAIN / p).read_bytes()).hexdigest() == manifest['source_sha256'][p]
           for p in SOURCE_FILES)
old_cases = {case['id']: case for case in old['cases']}
new_cases = {case['id']: case for case in new['cases']}
assert set(old_cases) == set(new_cases)
catalog = {a['id']: a for a in ARCHITECTURES}
catalog.update(calibration_architectures(catalog))
assert all(catalog[a] == manifest['architectures'][a] for a in ARMS)
schedule = make_schedule(new['cases'], ARMS, 1, manifest['seed'])
assert [row['sample_id'] for row in rows] == [item['id'] for item in schedule[:len(rows)]]
assert all(old_cases[row['case_id']] == new_cases[row['case_id']] for row in rows)
assert all(row['case_id'] != 'ac29.constraint_reasoning' for row in rows)
assert not new_dir.exists(), 'Corrected output directory must be empty'
new_dir.mkdir(parents=True)
(new_dir / 'results.jsonl').write_bytes((old_dir / 'results.jsonl').read_bytes())
provenance = {
    'kind': 'verified_unaffected_sample_carry_forward',
    'source_manifest': str((old_dir / 'manifest.json').resolve()),
    'source_manifest_sha256': hashlib.sha256((old_dir / 'manifest.json').read_bytes()).hexdigest(),
    'old_suite_sha256': manifest['suite_sha256'],
    'new_suite_sha256': hashlib.sha256((base / 'cases.json').read_bytes()).hexdigest(),
    'verification': 'All carried cases are byte-equivalent JSON objects, source hashes/configs and deterministic schedule match.',
    'carried_sample_ids': [row['sample_id'] for row in rows],
    'interrupted_attempt': {
        'sample_id': schedule[len(rows)]['id'],
        'status': 'aborted_by_operator_before_sample_record',
        'provider_request_started': 'unknown',
        'token_usage': 'unknown',
        'retry_classification': 'one new attempt after interrupted harness run, not a model retry',
    },
    'continued_schedule': 'Corrected case suite, same deterministic order; samples 1-17 carried, sample 18 onward newly executed.',
}
(new_dir / 'carry_forward.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
print(f'Carried {len(rows)} verified samples; interrupted attempt: {schedule[len(rows)]["id"]}')
