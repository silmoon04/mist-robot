"""Offline checks for the standalone eight-trial shadow schedule."""
import json

import pytest

from brain.benchmarks.naturalness import streaming_benchmark_20260930 as bench
from brain.benchmarks.naturalness import streaming_shadow_probe_20260930 as probe


def _main_evidence(tmp_path):
    directory = tmp_path / 'main'
    directory.mkdir()
    plan = bench.make_plan()
    (directory / 'plan.frozen.json').write_text(json.dumps(plan), encoding='utf-8')
    (directory / 'attempts.json').write_text(json.dumps(plan['trials']), encoding='utf-8')
    (directory / 'report.json').write_text(json.dumps({'completed_trial_count': 104}),
                                           encoding='utf-8')
    return directory / 'plan.frozen.json'


def test_probe_dispatches_only_eight_shadow_trials_with_counterparts(tmp_path):
    path = _main_evidence(tmp_path)
    plan = probe.make_shadow_plan(path)
    probe.verify_shadow_plan(plan)
    assert plan['planned_trial_count'] == 8
    assert plan['arms'] == bench.SHADOW_ARMS
    assert {trial['case_id'] for trial in plan['trials']} == set(bench.SHADOW_CASES)
    assert [trial['order'] for trial in plan['trials']] == list(range(1, 9))
    assert {trial['original_full_plan_order'] for trial in plan['trials']} == set(range(105, 113))
    for trial in plan['trials']:
        assert trial['counterpart_arm'] in ('flux-jev-off', 'flux-jev-on')
        assert trial['counterpart_main_order'] <= 104
        assert trial['kind'] == 'passive_shadow_control'


def test_probe_refuses_changed_main_evidence(tmp_path):
    path = _main_evidence(tmp_path)
    plan = probe.make_shadow_plan(path)
    (path.parent / 'report.json').write_text(json.dumps({'completed_trial_count': 103}),
                                            encoding='utf-8')
    with pytest.raises(ValueError, match='changed'):
        probe.verify_shadow_plan(plan)


def test_probe_requires_completed_main_run(tmp_path):
    path = _main_evidence(tmp_path)
    (path.parent / 'attempts.json').write_text('[]', encoding='utf-8')
    with pytest.raises(ValueError, match='completed 104'):
        probe.make_shadow_plan(path)
