"""Provider protocol replay; no API connection or billing."""
import asyncio
import time

import pytest

try:
    from .streaming_asr_20260930 import Nova3ASR, FluxASR, ScribeRealtimeASR, FluxScribeShadowASR
except ImportError:
    from streaming_asr_20260930 import Nova3ASR, FluxASR, ScribeRealtimeASR, FluxScribeShadowASR


async def replay(adapter, packets):
    emitted = []
    adapter._callback = emitted.append
    for packet in packets:
        await adapter.process_raw(packet)
    return emitted


@pytest.mark.asyncio
async def test_nova_segment_deltas_and_silence_endpoint():
    asr = Nova3ASR('secret')
    events = await replay(asr, [
        {'type': 'SpeechStarted'},
        {'type': 'Results', 'start': 0, 'duration': .4, 'is_final': False,
         'channel': {'alternatives': [{'transcript': 'Um I'}]}},
        {'type': 'Results', 'start': 0, 'duration': .4, 'is_final': True,
         'channel': {'alternatives': [{'transcript': 'Um I', 'words': [{'word': 'Um', 'start': 0, 'end': .2}]}]}},
        {'type': 'Results', 'start': 0, 'duration': .4, 'is_final': True,
         'channel': {'alternatives': [{'transcript': 'Um I'}]}},
        {'type': 'Results', 'start': .4, 'duration': .5, 'is_final': True, 'speech_final': True,
         'channel': {'alternatives': [{'transcript': 'agree'}]}},
    ])
    assert [e['type'] for e in events] == ['speech_start', 'partial', 'final', 'final', 'turn_end']
    assert events[-1]['segment'] == 'Um I agree'
    assert events[-1]['transcript'] == 'Um I agree'
    assert events[-1]['metadata']['source'] == 'silence_endpoint'
    assert len(asr.raw_events) == 5


@pytest.mark.asyncio
async def test_flux_cumulative_updates_and_resumption():
    asr = FluxASR('secret')
    events = await replay(asr, [
        {'type': 'TurnInfo', 'event': 'StartOfTurn', 'turn_index': 7, 'transcript': 'Um'},
        {'type': 'TurnInfo', 'event': 'Update', 'turn_index': 7, 'transcript': 'Um I'},
        {'type': 'TurnInfo', 'event': 'TurnResumed', 'turn_index': 7, 'transcript': 'Um I mean'},
        {'type': 'TurnInfo', 'event': 'EndOfTurn', 'turn_index': 7,
         'transcript': 'Um I mean yes', 'trigger': 'model',
         'words': [{'word': 'Um', 'start': 0, 'end': .2}]},
        {'type': 'TurnInfo', 'event': 'EndOfTurn', 'turn_index': 7,
         'transcript': 'Um I mean yes', 'trigger': 'model'},
    ])
    assert [e['type'] for e in events] == ['speech_start', 'partial', 'turn_resumed', 'final', 'turn_end']
    assert events[0]['transcript'] == 'Um'
    assert events[-1]['segment'] == 'Um I mean yes'
    assert events[-1]['turn_id'] == 7
    assert events[-1]['cumulative'] is True
    assert 'eager_eot_threshold' not in asr.url
    assert 'eot_timeout_ms=8000' in asr.url


@pytest.mark.asyncio
async def test_scribe_commit_then_delayed_timestamps_no_duplicate_final():
    asr = ScribeRealtimeASR('secret')
    events = await replay(asr, [
        {'message_type': 'partial_transcript', 'text': 'Uh I'},
        {'message_type': 'committed_transcript', 'text': 'Uh I think'},
        {'message_type': 'committed_transcript_with_timestamps', 'text': 'Uh I think',
         'words': [{'text': 'Uh', 'start': 0, 'end': .2}]},
        {'message_type': 'partial_transcript', 'text': 'yes'},
        {'message_type': 'committed_transcript', 'text': 'yes'},
    ])
    assert [e['type'] for e in events] == [
        'speech_start', 'partial', 'final', 'turn_end', 'alignment',
        'speech_start', 'partial', 'final', 'turn_end']
    assert events[2]['words'][0]['text'] == 'Uh'
    assert events[-1]['transcript'] == 'Uh I think yes'
    assert events[-1]['turn_id'] == 1
    assert 'vad_silence_threshold_secs=0.5' in asr.url
    assert 'no_verbatim=false' in asr.url


@pytest.mark.asyncio
async def test_silence_sent_and_secrets_redacted():
    asr = ScribeRealtimeASR('secret')

    class Socket:
        def __init__(self):
            self.sent = []

        async def send_json(self, packet):
            self.sent.append(packet)

    asr._ws = Socket()
    await asr.send_pcm(b'\0' * 3200)
    assert asr._ws.sent[0]['audio_base_64']
    assert asr._ws.sent[0]['sample_rate'] == 16000
    assert len(asr._ws.sent) == 1
    assert 'secret' not in str(asr.url)
    assert 'secret' not in str(await replay(asr, [
        {'message_type': 'session_started', 'token': 'secret', 'audio_base_64': 'sensitive'}]))
    assert asr.raw_events[-1]['token'] == '[redacted]'


def test_sample_rates():
    assert 'sample_rate=16000' in Nova3ASR('key').url
    assert 'sample_rate=24000' in FluxASR('key', sample_rate=24000).url
    assert 'audio_format=pcm_24000' in ScribeRealtimeASR('key', sample_rate=24000).url
    assert 'filler_words=true' in Nova3ASR('key').url
    assert 'vad_events=true' in Nova3ASR('key').url
    assert 'language=en-GB' in Nova3ASR('key').url
    with pytest.raises(ValueError):
        Nova3ASR('key', sample_rate=22050)


@pytest.mark.asyncio
async def test_flux_packs_80ms_and_flushes_remainder():
    asr = FluxASR('secret')

    class Socket:
        def __init__(self):
            self.sent = []

        async def send_bytes(self, value):
            self.sent.append(value)

        async def send_json(self, value):
            self.sent.append(value)

    asr._ws = Socket()
    for _ in range(5):
        await asr.send_pcm(b'\0' * 640)
    assert [len(value) for value in asr._ws.sent] == [2560]
    await asr._finish_stream()
    assert len(asr._ws.sent[1]) == 640
    assert asr._ws.sent[2] == {'type': 'CloseStream'}
    timing = asr.timing_summary
    assert timing['input_pcm_bytes'] == 3200
    assert timing['wire_pcm_bytes'] == 3200
    assert timing['wire_send_count'] == 2
    assert timing['max_buffered_frames_20ms'] == 4


@pytest.mark.asyncio
async def test_unexpected_ws_close_yields_error():
    asr = Nova3ASR('secret')
    events = []
    asr._callback = events.append

    class Socket:
        def __aiter__(self):
            async def empty():
                if False:
                    yield None
            return empty()

    asr._ws = Socket()
    await asr._read_loop()
    assert events[-1]['type'] == 'error'
    assert events[-1]['metadata']['code'] == 'unexpected_websocket_close'


@pytest.mark.asyncio
async def test_shadow_is_diagnostic_only_and_primary_continues():
    flux = FluxASR('key')
    scribe = ScribeRealtimeASR('key')
    sent = []

    async def start_flux(callback):
        flux._callback = callback

    async def start_scribe(callback):
        scribe._callback = callback

    async def send_flux(pcm):
        sent.append(('flux', pcm))

    async def send_scribe(pcm):
        sent.append(('scribe', pcm))

    async def closed():
        pass

    flux.start, scribe.start = start_flux, start_scribe
    flux.send_pcm, scribe.send_pcm = send_flux, send_scribe
    flux.close = scribe.close = closed
    wrapper = FluxScribeShadowASR('key', 'key', flux=flux, scribe=scribe)
    events = []
    await wrapper.start(events.append)
    await wrapper.send_pcm(b'\0' * 640)
    await wrapper.scribe.process_raw({'message_type': 'committed_transcript', 'text': 'ignore me'})
    await wrapper.flux.process_raw({'type': 'TurnInfo', 'event': 'EndOfTurn',
                                    'turn_index': 0, 'transcript': 'answer me'})
    await wrapper.close()
    assert any(e['type'] == 'turn_end' and e['text'] == 'answer me' for e in events)
    assert not any(e['type'] == 'turn_end' and e['text'] == 'ignore me' for e in events)
    assert any(e['type'] == 'shadow' and e['metadata']['original_event_type'] == 'turn_end'
               for e in events)
    assert {who for who, _ in sent} == {'flux', 'scribe'}
    assert 'flux' in wrapper.timing_summary
    assert 'scribe_shadow' in wrapper.timing_summary


@pytest.mark.asyncio
async def test_first_text_and_non_silent_wire_timing():
    asr = Nova3ASR('key')
    asr._opened_at = time.monotonic()

    class Socket:
        async def send_bytes(self, value):
            await asyncio.sleep(.001)

    asr._ws = Socket()
    await asr.send_pcm(b'\0' * 640)
    await asr.send_pcm(b'\1' * 640)
    await asr.process_raw({'type': 'Results', 'start': 0, 'duration': .02,
                           'is_final': False,
                           'channel': {'alternatives': [{'transcript': 'hi'}]}})
    timing = asr.timing_summary
    assert timing['wire_send_count'] == 2
    assert timing['wire_pcm_bytes'] == 1280
    assert timing['first_send_start_after_open_s'] is not None
    assert timing['first_send_end_after_open_s'] >= timing['first_send_start_after_open_s']
    assert timing['first_non_silent_send_after_open_s'] > timing['first_send_start_after_open_s']
    assert timing['first_text_receive_after_open_s'] is not None
    assert timing['max_send_await_ms'] >= 1
