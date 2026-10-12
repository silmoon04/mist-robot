"""Run only the eight passive Flux + Scribe diagnostic trials.

Flux owns turn control. Scribe supplies a shadow transcript for later alignment
and disagreement analysis; this probe does not test active transcript fusion.
The completed 104-trial main run supplies the matched Flux counterparts.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

try:
    from . import streaming_benchmark_20260930 as bench
except ImportError:
    import streaming_benchmark_20260930 as bench

DEFAULT_MAIN_PLAN = bench.OUTPUT_ROOT / 'main-02' / 'plan.frozen.json'
DEFAULT_OUTPUT = bench.OUTPUT_ROOT / 'shadow-probe-01'


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_shadow_plan(main_plan_path: Path) -> dict:
    """Build a standalone eight-trial diagnostic plan without provider calls."""
    main_plan_path = main_plan_path.resolve()
    main_dir = main_plan_path.parent
    attempts_path = main_dir / 'attempts.json'
    report_path = main_dir / 'report.json'
    main = json.loads(main_plan_path.read_text(encoding='utf-8'))
    attempts = json.loads(attempts_path.read_text(encoding='utf-8'))
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if (main.get('planned_trial_count') != 104 or main.get('shadow_control') is not False
            or main.get('legacy_control') is not True
            or len(attempts) != 104 or report.get('completed_trial_count') != 104):
        raise ValueError('A completed 104-trial main plan and attempts are required')
    identity = lambda row: (row.get('order'), row.get('case_id'), row.get('arm'),
                            row.get('repetition'))
    if {identity(row) for row in attempts} != {identity(row) for row in main['trials']}:
        raise ValueError('Main attempt identities differ from its frozen plan')
    bench.verify_plan(main)
    full = bench.make_plan(include_shadow=True, seed=main['seed'])
    if (full['source_hashes'] != main['source_hashes']
            or full['fixture_hashes'] != main['fixture_hashes']
            or full['fixture_manifest_sha256'] != main['fixture_manifest_sha256']):
        raise ValueError('Main and diagnostic source or fixture bytes differ')
    counterparts = {(trial['case_id'], trial['repetition'], trial['arm']): trial
                    for trial in main['trials']}
    selected = [trial for trial in full['trials']
                if trial['kind'] == 'passive_shadow_control']
    if len(selected) != 8 or {trial['case_id'] for trial in selected} != set(bench.SHADOW_CASES):
        raise ValueError('Expected exactly the eight specified shadow diagnostics')
    trials = []
    for order, trial in enumerate(selected, 1):
        counterpart_arm = trial['arm'].replace('-scribe-shadow', '')
        counterpart = counterparts.get((trial['case_id'], trial['repetition'], counterpart_arm))
        if counterpart is None:
            raise ValueError('Missing matched Flux main-run trial')
        trials.append({**trial, 'original_full_plan_order': trial['order'], 'order': order,
                       'counterpart_arm': counterpart_arm,
                       'counterpart_main_order': counterpart['order'],
                       'counterpart_case_id': counterpart['case_id'],
                       'counterpart_repetition': counterpart['repetition']})
    plan = dict(full)
    plan.update(experiment_type='passive_shadow_diagnostic_only',
                interpretation='Measures paired-stream compatibility and transcript information; not active fusion superiority.',
                planned_trial_count=8, trials=trials, cases=bench.SHADOW_CASES,
                arms=bench.SHADOW_ARMS, legacy_control=False, shadow_control=True,
                fixture_hashes={name: full['fixture_hashes'][name] for name in bench.SHADOW_CASES},
                parent_main_plan={'file': str(main_plan_path), 'sha256': _sha(main_plan_path),
                                  'attempts_sha256': _sha(attempts_path),
                                  'report_sha256': _sha(report_path)},
                probe_helper={'file': str(Path(__file__).resolve()),
                              'sha256': _sha(Path(__file__).resolve())})
    return plan


def verify_shadow_plan(plan: dict) -> None:
    bench.verify_plan(plan)
    helper = plan['probe_helper']
    parent = plan['parent_main_plan']
    if _sha(Path(helper['file'])) != helper['sha256']:
        raise ValueError('Shadow probe helper changed since planning')
    main_plan = Path(parent['file'])
    if (_sha(main_plan) != parent['sha256']
            or _sha(main_plan.parent / 'attempts.json') != parent['attempts_sha256']
            or _sha(main_plan.parent / 'report.json') != parent['report_sha256']):
        raise ValueError('Matched main-run evidence changed since planning')
    if len(plan['trials']) != 8 or any(t['kind'] != 'passive_shadow_control'
                                      for t in plan['trials']):
        raise ValueError('Only eight passive shadow trials may be dispatched')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--main-plan', type=Path, default=DEFAULT_MAIN_PLAN)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--base-url', default=f'http://127.0.0.1:{bench.PORT}')
    args = parser.parse_args()
    plan = make_shadow_plan(args.main_plan)
    verify_shadow_plan(plan)
    if args.plan:
        print(json.dumps(plan, indent=2))
    else:
        if args.output.exists():
            raise FileExistsError('Choose a fresh shadow-probe output directory')
        print(json.dumps(asyncio.run(bench.run_batch(args.base_url, args.output, plan)), indent=2))


if __name__ == '__main__':
    main()
