"""Offline invariants for the frozen paired live pilot."""
import asyncio
import base64
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from benchmarks.naturalness import qwen_flux_live_benchmark_20260929 as pilot
from duplex.tts import StreamingTTS


def test_frozen_design_and_fixture_bytes():
    manifest = json.loads((pilot.ROOT / 'manifest.v4.frozen.json').read_text(encoding='utf-8'))
    pilot.verify_frozen(manifest)
    assert len(manifest['trials']) == 32
    assert set(manifest['arms']) == set(pilot.ARMS)
    assert len({(r['case_id'], r['arm'], r['repetition']) for r in manifest['trials']}) == 32
    for repeat in (1, 2):
        for case in pilot.spec.CASES:
            pair = [r for r in manifest['trials'] if r['case_id'] == case.id
                    and r['repetition'] == repeat]
            assert len(pair) == 2
            assert {r['arm'] for r in pair} == set(pilot.ARMS)
            assert pair[1]['order'] == pair[0]['order'] + 1
            fixture = manifest['fixtures'][case.id]
            assert fixture['wav']['sample_rate'] == 16000
            assert fixture['wav']['sha256'] == fixture['sha256']
            assert Path(fixture['path']).exists()


def test_stage_lineage_excludes_seed_output():
    events = [
        dict(type='audio', t_ms=5, benchmark_turn_id='seed', pcm_bytes=100),
        dict(type='transcript_done', role='user', t_ms=100, benchmark_turn_id='user'),
        dict(type='transcript_delta', role='assistant', text='seed late', t_ms=110,
             benchmark_turn_id='seed'),
        dict(type='transcript_delta', role='assistant', text='answer', t_ms=120,
             benchmark_turn_id='answer', benchmark_parent_user_turn_id='user'),
        dict(type='audio', t_ms=150, benchmark_turn_id='answer',
             benchmark_parent_user_turn_id='user'),
        dict(type='transcript_done', role='assistant', t_ms=180,
             benchmark_turn_id='answer', benchmark_parent_user_turn_id='user'),
    ]
    stage = pilot.evidence(events, 90, 'seed', 80,
                           [dict(reason='PCM_duration_queue_drained', t_ms=300)])
    assert stage['active_user_turn_id'] == 'user'
    assert stage['first_correlated_text_ms'] == 120
    assert stage['first_correlated_pcm_ms'] == 150
    assert stage['simulated_playback_completion_from_last_nonsilent_ms'] == 220


def test_terminal_requires_every_tts_sequence():
    events = [
        dict(type='transcript_done', role='user', t_ms=100, benchmark_turn_id='user'),
        dict(type='transcript_done', role='assistant', t_ms=600,
             benchmark_parent_user_turn_id='user'),
        dict(type='audio', t_ms=700, epoch=1, seq=1,
             benchmark_parent_user_turn_id='user'),
        dict(type='audio', t_ms=750, epoch=1, seq=2,
             benchmark_parent_user_turn_id='user'),
        dict(type='latency', t_ms=800, tts=dict(epoch=1, sequence=1)),
    ]
    args = dict(input_start_ms=0, input_last_sample_ms=100,
                expected_reply=True, expected_stop=False, preserve_backchannel=False,
                playback_active=False, playback_queue_end=0, now=3)
    assert pilot.prior.terminal_state(events, **args)[0] is False
    events.append(dict(type='latency', t_ms=900, tts=dict(epoch=1, sequence=2)))
    assert pilot.prior.terminal_state(events, **args)[0] is True
    assert pilot.terminal_with_tts_drain(events, **args)[0] is False
    # The provider's final latency event can precede a buffered PCM chunk.
    events.append(dict(type='audio', t_ms=950, epoch=1, seq=2,
                       benchmark_parent_user_turn_id='user', pcm_bytes=9600))
    assert pilot.terminal_with_tts_drain(events, **args)[0] is False
    events.append(dict(type='bench_tts_sequence_drained', t_ms=960, epoch=1, seq=1,
                       pending_count=1, benchmark_parent_user_turn_id='user'))
    assert pilot.terminal_with_tts_drain(events, **args)[0] is False
    events.append(dict(type='bench_tts_sequence_drained', t_ms=970, epoch=1, seq=2,
                       pending_count=0, benchmark_parent_user_turn_id='user'))
    assert pilot.terminal_with_tts_drain(events, **args)[0] is True


def test_receipt_follows_buffered_final_pcm():
    emitted = []
    mask = SimpleNamespace(epoch=0, pending={'context': dict(epoch=0, seq=4, done=True)})

    async def emit(event):
        emitted.append(event)

    async def real_drain():
        await emit(dict(type='audio', epoch=0, seq=4, pcm_bytes=9600))
        await asyncio.sleep(0)
        mask.pending.pop('context')

    mask.drain = real_drain
    pilot.install_tts_drain_receipts(mask, emit)
    asyncio.run(mask.drain())
    assert [event['type'] for event in emitted] == ['audio', 'bench_tts_sequence_drained']
    assert emitted[-1]['pending_count'] == 0


def test_real_tts_final_message_receipt_follows_pcm():
    emitted = []

    async def emit(event):
        emitted.append(event)
        if event['type'] == 'audio':
            await asyncio.sleep(0)  # model delayed browser emission

    tts = StreamingTTS('offline-test-key', emit)
    tts.pending['context'] = dict(epoch=0, seq=4, chunks=__import__('collections').deque(),
        done=False, audible=True, text='hello', buffer='', first_text=time.monotonic(),
        first_audio=None, bytes=0, last_send=time.monotonic(), finished=True,
        phrase_count=1, caption_text='', caption_alignment_complete=True,
        delivery='neutral', turn_id='turn')
    pilot.install_tts_drain_receipts(tts, emit)
    asyncio.run(tts.output(dict(contextId='context', audio=base64.b64encode(b'\0' * 9600).decode(),
                                isFinal=True)))
    types = [event['type'] for event in emitted]
    assert types.index('latency') < types.index('audio') < types.index('bench_tts_sequence_drained')
    assert 'context' not in tts.pending
