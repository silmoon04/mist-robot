"""Blind the four predeclared reasoning calibration samples after the run."""
import json
import random
from pathlib import Path

base = Path(__file__).resolve().parents[2] / 'results/architecture-cost-20260928'
cases = {c['id']: c for c in json.loads((base / 'cases.json').read_text(encoding='utf-8'))['cases']}
rows = json.loads((base / 'model/results.json').read_text(encoding='utf-8'))
diagnostics = [r for r in rows if r['sample_id'].startswith('cal-')]
assert len(diagnostics) == 4
packets, key = [], {}
rng = random.Random(20260928)
for case_id in sorted({r['case_id'] for r in diagnostics}):
    group = [r for r in diagnostics if r['case_id'] == case_id]
    assert len(group) == 2
    rng.shuffle(group)
    case = cases[case_id]
    for label, row in zip('AB', group):
        packet_id = f'{case_id}.diagnostic.{label}'
        key[packet_id] = row['sample_id']
        packets.append({
            'packet_id': packet_id, 'case_id': case_id, 'anonymous_label': label,
            'case_goal': case.get('case_goal'), 'review_focus': case.get('review_focus', []),
            'critical_failures': case.get('critical_failures', []),
            'assertions': case.get('assertions', []), 'status': row['status'],
            'dialogue': [{'turn_ref': f'{packet_id}.t{i}', 'user': t['user'],
                          'assistant': t['text'], 'status': t['status'],
                          'tool_calls': [{'name': call['name'], 'success': call['success'],
                                          'result': call['result']}
                                         for call in t['tool_calls']]}
                         for i, t in enumerate(row['turns'])],
            'evidence_limit': 'Text and server tool receipts only; audio/playback and renderer visibility unverified.',
        })
(base / 'model/blind_diagnostics.json').write_text(json.dumps(packets, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(base / 'model/diagnostic_key.json').write_text(json.dumps(key, indent=2) + '\n', encoding='utf-8')
print(f'Exported {len(packets)} blind diagnostics')
