"""Replay captured Luna tool mistakes against current real request guards."""
import json
from pathlib import Path
import tempfile

from eval_luna_conversations import BRAIN, RuntimeBridge, state_snapshot
from duplex.runtime import RobotRuntime


CASES = [
    ('baseline', 'upset_no_advice', 3),
    ('baseline', 'corrections', 1),
    ('baseline', 'corrections', 2),
    ('baseline', 'corrections', 4),
    ('final_targeted', 'regression_companionship', 3),
    ('final_contracts', 'regression_motion_idioms', 1),
    ('final_contracts', 'regression_motion_idioms', 3),
]


def main():
    root = BRAIN / 'results/luna_conversations_20260922'
    rows = []
    for run, arc, turn_number in CASES:
        source = root / run / arc / 'transcript.json'
        turn = json.loads(source.read_text(encoding='utf-8'))['turns'][turn_number-1]
        with tempfile.TemporaryDirectory(prefix='mist-guard-replay-') as temp:
            runtime = RobotRuntime(Path(temp))
            bridge = RuntimeBridge(runtime)
            bridge.prepare('none', turn['input'])
            before = state_snapshot(runtime)
            for call in turn['tools']:
                bridge.request('call', {'name':call['name'], 'arguments':call['args']})
            after = state_snapshot(runtime)
        rows.append({'source':str(source), 'turn':turn_number, 'input':turn['input'],
                     'original_calls':turn['tools'], 'guarded_receipts':bridge.receipts,
                     'state_unchanged':before == after,
                     'every_bad_call_rejected': bool(bridge.receipts) and all(r['is_error'] for r in bridge.receipts)})
    report = {'kind':'deterministic replay of actual previous Luna mistakes; no new model calls',
              'cases':rows, 'all_protected':all(r['state_unchanged'] and r['every_bad_call_rejected'] for r in rows)}
    (root / 'guard_replay.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(rows),'all_protected':report['all_protected']}))
    return 0 if report['all_protected'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
