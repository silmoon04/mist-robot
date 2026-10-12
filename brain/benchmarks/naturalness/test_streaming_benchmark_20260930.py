"""Offline protocol and capture tests; no studio or provider requests."""
import json
from pathlib import Path

import pytest

from brain.benchmarks.naturalness import streaming_benchmark_20260930 as bench


def _terminal(events, **kwargs):
    return bench.terminal_state(events, input_start_ms=100, input_last_sample_ms=500,
        expected_reply=True, expected_stop=False, preserve_backchannel=False,
        playback_active=False, playback_queue_end=.8, now=3,
        settled_ms=100, **kwargs)


def test_full_plan_is_paired_and_has_legacy_controls():
    plan = bench.make_plan()
    assert plan['planned_trial_count'] == 104
    assert len([t for t in plan['trials'] if t['kind'] == 'core']) == 96
    assert len([t for t in plan['trials'] if t['kind'] == 'legacy_control']) == 8
    assert len({(t['repetition'], t['case_id'], t['arm']) for t in plan['trials']}) == 104
    for repetition in (1, 2):
        for case in plan['cases']:
            arms = {t['arm'] for t in plan['trials'] if t['case_id'] == case
                    and t['repetition'] == repetition}
            assert set(bench.MAIN_ARMS) <= arms
    assert bench.make_plan()['trials'] == plan['trials']
    shadow = bench.make_plan(include_shadow=True)
    assert shadow['planned_trial_count'] == 112
    assert {t['case_id'] for t in shadow['trials'] if t['kind'] == 'passive_shadow_control'} \
        == {'correction', 'unfinished_pause_resume'}


def test_seed_audio_is_excluded_even_when_it_arrives_after_input_start():
    events = [
        {'type': 'audio', 't_ms': 101, 'benchmark_turn_id': 'seed', 'epoch': 0, 'seq': 1},
        {'type': 'transcript_done', 'role': 'user', 't_ms': 600, 'benchmark_turn_id': 'user'},
        {'type': 'audio', 't_ms': 800, 'benchmark_turn_id': 'reply',
         'benchmark_parent_user_turn_id': 'user', 'epoch': 1, 'seq': 1},
        {'type': 'latency', 't_ms': 900, 'tts': {'epoch': 1, 'sequence': 1}},
        {'type': 'transcript_done', 'role': 'assistant', 't_ms': 950,
         'benchmark_parent_user_turn_id': 'user'},
    ]
    filtered = bench._post_input_events(events, 100, 'seed')
    assert events[0] not in filtered
    assert _terminal(events, seed_turn_id='seed') == (True, 'assistant_and_tts_complete')
    assert bench._post_input_events(events, 100, None) == events


def test_all_tts_sequences_and_resumed_user_epoch_must_finish():
    events = [
        {'type': 'transcript_done', 'role': 'user', 't_ms': 550},
        {'type': 'audio', 't_ms': 700, 'epoch': 1, 'seq': 1},
        {'type': 'audio', 't_ms': 710, 'epoch': 1, 'seq': 2},
        {'type': 'latency', 't_ms': 720, 'tts': {'epoch': 1, 'sequence': 1}},
        {'type': 'transcript_done', 'role': 'assistant', 't_ms': 750},
    ]
    assert _terminal(events)[1] == 'waiting_for_tts_sequences'
    events.append({'type': 'latency', 't_ms': 760, 'tts': {'epoch': 1, 'sequence': 2}})
    assert _terminal(events)[0]
    events.append({'type': 'debug_model', 'phase': 'turn_resumed', 't_ms': 800})
    assert _terminal(events)[1] == 'waiting_for_active_user_epoch'
    events.append({'type': 'transcript_done', 'role': 'user', 't_ms': 900})
    assert _terminal(events)[1] == 'waiting_for_reply'
    events.append({'type': 'transcript_done', 'role': 'assistant', 't_ms': 1000})
    assert _terminal(events)[0]


def test_cancelled_prior_epoch_does_not_block_new_reply():
    events = [
        {'type': 'audio', 't_ms': 520, 'epoch': 1, 'seq': 1},
        {'type': 'audio_reset', 't_ms': 560, 'epoch': 2},
        {'type': 'transcript_done', 'role': 'user', 't_ms': 650},
        {'type': 'audio', 't_ms': 800, 'epoch': 2, 'seq': 1},
        {'type': 'latency', 't_ms': 850, 'tts': {'epoch': 2, 'sequence': 1}},
        {'type': 'transcript_done', 'role': 'assistant', 't_ms': 900},
    ]
    assert _terminal(events) == (True, 'assistant_and_tts_complete')
    events.pop(4)
    assert _terminal(events)[1] == 'waiting_for_tts_sequences'


def test_queue_and_nonreply_policy_terminal():
    events = [{'type': 'transcript_done', 'role': 'user', 't_ms': 550,
               'backchannel': True}]
    args = dict(input_start_ms=100, input_last_sample_ms=500,
                expected_reply=False, expected_stop=False, preserve_backchannel=True,
                playback_queue_end=.8, now=3, settled_ms=100)
    assert not bench.terminal_state(events, playback_active=True, **args)[0]
    assert bench.terminal_state(events, playback_active=False, **args)[0]


def test_early_reply_to_first_user_epoch_fails_even_with_final_reply():
    case = next(c for c in bench.spec.CASES if c.id == 'unfinished_pause_resume')
    events = [
        {'type': 'transcript_done', 'role': 'user', 'text': 'The green bracket',
         'benchmark_turn_id': 'first', 't_ms': 1350},
        {'type': 'transcript_delta', 'role': 'assistant', 'text': 'Okay',
         'benchmark_parent_user_turn_id': 'first', 't_ms': 2100},
        {'type': 'transcript_done', 'role': 'user', 'text': 'needs sanding',
         'benchmark_turn_id': 'final', 't_ms': 5750},
        {'type': 'transcript_delta', 'role': 'assistant', 'text': 'Sand it gently',
         'benchmark_parent_user_turn_id': 'final', 't_ms': 6500},
    ]
    ids = bench._input_turn_ids(events)
    assert ids == ['first', 'final']
    scored = bench.spec.score_trial(case, events=events,
        transcript=bench._transcript_rows(events), active_user_turn_id=ids[-1],
        input_user_turn_ids=ids, input_start_ms=100,
        audio_clock={'clip_start_ms': 100, 'input_last_nonsilent_sample_ms': 5660,
                     'capture_complete': True})
    assert scored['metrics']['false_premature_response']['pass'] is False
    assert scored['metrics']['missed_reply']['pass'] is True


@pytest.mark.asyncio
async def test_failed_connection_retains_partial_row_without_error_string(tmp_path: Path):
    class BadHTTP:
        def ws_connect(self, *args, **kwargs):
            raise RuntimeError('secret=NEVER_WRITE_THIS')
    trial = {'order': 1, 'case_id': 'normal_end', 'arm': 'nova-jev-off',
             'repetition': 1, 'kind': 'core'}
    row = await bench.run_one(BadHTTP(), 'http://127.0.0.1:9066', trial, tmp_path)
    assert row['status'] == 'failed'
    assert row['events'] == []
    saved = next(tmp_path.glob('*.json')).read_text(encoding='utf-8')
    assert 'NEVER_WRITE_THIS' not in saved
    assert json.loads(saved)['score']['case_id'] == 'normal_end'


@pytest.mark.asyncio
async def test_existing_output_is_refused_before_network(tmp_path: Path):
    existing = tmp_path / 'existing'
    existing.mkdir()
    plan = bench.make_plan(cases=('normal_end',), arms=('nova-jev-off',),
                           repetitions=1, include_legacy=False)
    with pytest.raises(FileExistsError):
        await bench.run_batch('http://127.0.0.1:9066', existing, plan)


def test_usage_keeps_all_model_rounds_and_marks_failures_unknown():
    trace = {'events': [
        {'source': 'voice', 'event': {'type': 'debug_model', 'phase': 'thinking_finished',
            'timings': {'http_requests': [{'usage': {'input_tokens': 10}},
                                           {'usage': {'input_tokens': 20}}]}}},
        {'source': 'voice', 'event': {'type': 'debug_model', 'phase': 'model_failed'}},
        {'source': 'voice', 'event': {'type': 'latency', 'tts': {'epoch': 1,
            'sequence': 2, 'characters': 14}}},
        {'source': 'benchmark_adapter', 'event': {'type': 'jev_policy_outcomes',
            'outcomes': [{'endpoint_id': 'a', 'result': {
                'response': {'usage': {'input_tokens': 5}}}}]}},
    ]}
    usage = bench._usage(trace)
    assert [r['usage']['input_tokens'] for r in usage['request_records']] == [10, 20, 5]
    assert usage['tts_completed_sequences'][0]['characters'] == 14
    assert usage['known'] is False
    assert 'failed_model_request_usage' in usage['unknown_components']


def test_client_delivery_summary_keeps_only_counts_and_timing():
    events = [{'type': 'audio', 't_ms': 100, 'pcm_bytes': 480},
              {'type': 'audio', 't_ms': 160, 'pcm_bytes': 480},
              {'type': 'audio_reset', 't_ms': 180}]
    summary = bench._client_delivery_metrics(events)
    assert summary['pcm_bytes'] == 960
    assert summary['max_interpacket_gap_ms'] == 60
    assert summary['audio_resets'] == 1
    assert 'pcm' not in summary
