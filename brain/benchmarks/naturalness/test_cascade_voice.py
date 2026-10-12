"""Offline tests: fake recognition, model streams, and the production event sink."""
import asyncio
import json
import logging
import math
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cascade_voice import CascadeVoice, PCMTrack, RevisionBridge, StaleTurn, incomplete_clause, is_backchannel, send_paced_pcm
from duplex.server import Conversation
from duplex.runtime import RobotRuntime


def result(text='Hello there.', errors=None):
    return SimpleNamespace(text=text, errors=errors or [], timings={})


def recognition(text, start=0, final=True, endpoint=True):
    return {'type': 'Results', 'start': start, 'duration': 1, 'is_final': final,
            'speech_final': endpoint, 'channel': {'alternatives': [{'transcript': text}]}}


class FakeClient:
    def __init__(self):
        self.model = 'fake'
        self.prompts = []
        self.sessions = 0
        self.closed = False

    def new_session(self):
        self.sessions += 1

    def ask(self, prompt, timeout, on_event):
        self.prompts.append(prompt)
        for text in ('Hello ', 'there.'):
            on_event({'type': 'message_update', 'assistantMessageEvent': {'delta': text}})
        return result()

    def close(self):
        self.closed = True


class FakeMask:
    def __init__(self):
        self.pending = {}
        self.muted = False
        self.epoch = 0
        self.texts = []
        self.finished = []
        self.begins = []

    def diagnostic(self, *args, **kwargs):
        pass

    async def begin(self, turn, **kwargs):
        self.begins.append(turn)

    async def text(self, text):
        if not self.muted:
            self.texts.append(text)

    async def finish(self, text):
        self.finished.append(text)

    async def release(self):
        pass

    async def interrupt(self):
        self.epoch += 1


class FakeSocket:
    closed = False

    def __init__(self):
        self.events = []

    async def send_json(self, event):
        self.events.append(event)


class CascadeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.runtime = RobotRuntime(Path(self.folder.name))
        self.socket = FakeSocket()
        self.conversation = Conversation({'runtime': self.runtime, 'speech_backend': 'streaming-tts'}, self.socket)
        self.conversation.mask = FakeMask()
        with patch.dict('os.environ', {'MIST_LAB_PROVIDER': 'cerebras', 'MIST_LAB_MODEL': 'gpt-oss-120b', 'MIST_LAB_FLOOR': 'selective'}):
            self.voice = CascadeVoice(self.runtime, self.folder.name, self.conversation.emit, None,
                                      self.conversation.realtime_event,
                                      expression_revision=lambda: self.conversation.expression_revision)
        self.conversation.voice = self.voice
        self.voice.client = FakeClient()
        self.voice.loop = asyncio.get_running_loop()

    async def asyncTearDown(self):
        await self.voice.close()
        await self.conversation.brain.close()

    async def wait_for(self, condition):
        for _ in range(200):
            if condition():
                return
            await asyncio.sleep(.005)
        self.fail('Timed out waiting for offline event')

    def phases(self):
        return [e.get('phase') for e in self.socket.events if e.get('type') == 'debug_model']

    async def test_leading_whitespace_does_not_start_speech(self):
        async def delta(text):
            await self.voice.model_event({'type':'message_update',
                'assistantMessageEvent':{'type':'text_delta','delta':text}},
                self.voice.revision, 'test-turn')
        await delta('\n\n')
        self.assertEqual(self.conversation.mask.begins, [])
        self.assertEqual(self.conversation.mask.texts, [])
        await delta('Hello')
        await delta(' ')
        self.assertEqual(self.conversation.mask.begins, ['test-turn'])
        self.assertEqual(self.conversation.mask.texts, ['Hello', ' '])

    async def test_stream_routes_visible_and_tts_text_once(self):
        self.voice.task(self.voice.model_worker())
        await self.voice.stt_event(recognition('Hello MIST.'))
        await self.wait_for(lambda: 'thinking_finished' in self.phases())
        self.assertEqual(self.conversation.mask.texts, ['Hello ', 'there.'])
        self.assertEqual(self.conversation.mask.finished, ['Hello there.'])
        self.assertEqual(len(self.conversation.mask.begins), 1)
        assistant = [e['text'] for e in self.socket.events if e.get('type') == 'transcript_delta' and e.get('role') == 'assistant']
        self.assertEqual(assistant, ['Hello ', 'there.'])
        self.assertEqual(self.voice.client.prompts, ['Hello MIST.'])
        self.assertFalse(self.voice.history[-1]['playback_verified'])

    async def test_cancelled_queued_background_result_never_reaches_model(self):
        self.voice.background=self.conversation.brain
        self.conversation.brain.jobs['j']={'job_id':'j','status':'complete','revision':0,'summary':'Old result'}
        await self.voice.context('Old result',job_id='j')
        self.conversation.brain.jobs['j']['status']='cancelled'
        self.voice.task(self.voice.model_worker())
        await self.wait_for(lambda:'stale_background_result_discarded' in self.phases())
        self.assertEqual(self.voice.client.prompts,[])
        self.assertEqual(self.conversation.mask.texts,[])

    async def test_cancel_background_result_after_generation_clears_pending_playback(self):
        self.voice.background=self.conversation.brain
        self.conversation.brain.jobs['j']={'job_id':'j','status':'complete','revision':0,'summary':'Result'}
        self.voice.task(self.voice.model_worker())
        await self.voice.context('Result',job_id='j')
        await self.wait_for(lambda:'thinking_finished' in self.phases())
        self.assertTrue(self.conversation.mask.texts)
        before=self.conversation.mask.epoch
        self.conversation.brain.jobs['j']['status']='cancelled'
        await self.voice.cancel_background_delivery('j')
        self.assertGreater(self.conversation.mask.epoch,before)
        self.assertIsNone(self.voice.background_delivery_job)
        with self.assertRaises(StaleTurn):
            await self.voice.model_event({'type':'message_update','assistantMessageEvent':{'delta':'stale'}},self.voice.revision,'old',job_id='j')

    async def test_background_delivery_retry_after_enqueue_error_speaks_once(self):
        self.voice.background=self.conversation.brain
        job={'job_id':'j','status':'complete','revision':0,'summary':'Current result','announced':False}
        self.conversation.brain.jobs['j']=job
        original_emit=self.voice.emit
        diagnostics=0
        async def fail_first_queue_diagnostic(event):
            nonlocal diagnostics
            if event.get('phase')=='context_queued':
                diagnostics+=1
                if diagnostics==1:
                    raise RuntimeError('Diagnostic transport failed after enqueue')
            await original_emit(event)
        self.voice.emit=fail_first_queue_diagnostic
        delivery=asyncio.create_task(self.conversation.deliver_results())
        try:
            await self.wait_for(lambda:job.get('delivery_attempts')==1)
            self.assertFalse(job['announced'])
            self.assertEqual(self.voice.requests.qsize(),1)
            job['retry_delivery_at']=0
            await self.wait_for(lambda:job['announced'])
        finally:
            delivery.cancel()
            await asyncio.gather(delivery,return_exceptions=True)
        queued=self.voice.requests.qsize()
        self.voice.task(self.voice.model_worker())
        await self.wait_for(lambda:len(self.conversation.mask.finished)==queued and self.voice.turn is None)
        self.assertEqual(job['delivery_attempts'],2)
        self.assertEqual(len(self.voice.client.prompts),1)
        self.assertEqual(self.conversation.mask.finished,['Hello there.'])
        self.assertEqual(len(self.conversation.mask.begins),1)
        self.assertEqual(len([e for e in self.socket.events if e.get('type')=='brain_delivery']),1)
        # A delayed retry after the worker drains the queue must also be harmless.
        await self.voice.context('Current result',job_id='j')
        self.assertTrue(self.voice.requests.empty())

    async def test_background_queue_rejection_can_retry_and_full_queue_accepts_duplicate(self):
        self.voice.background=self.conversation.brain
        self.conversation.brain.jobs['j']={'job_id':'j','status':'complete','revision':0,'summary':'Result'}
        for i in range(self.voice.requests.maxsize):
            await self.voice.context('Unkeyed report '+str(i))
        with self.assertRaisesRegex(RuntimeError,'queue is full'):
            await self.voice.context('Result',job_id='j')
        self.voice.requests.get_nowait()
        await self.voice.context('Result',job_id='j')
        self.assertTrue(self.voice.requests.full())
        await self.voice.context('Result',job_id='j')
        queued=[]
        while not self.voice.requests.empty():queued.append(self.voice.requests.get_nowait())
        self.assertEqual(sum(item[-1]=='j' for item in queued),1)

    async def test_context_deduplication_is_by_job_and_keeps_cancellation_guard(self):
        self.voice.background=self.conversation.brain
        for job_id in ('cancelled','current'):
            self.conversation.brain.jobs[job_id]={'job_id':job_id,'status':'complete','revision':0,'summary':'Same words'}
            await self.voice.context('Same words',job_id=job_id)
            await self.voice.context('Same words',job_id=job_id)
        self.conversation.brain.jobs['cancelled']['status']='cancelled'
        await self.voice.context('Same words',job_id='cancelled')
        self.voice.task(self.voice.model_worker())
        await self.wait_for(lambda:'thinking_finished' in self.phases())
        self.assertIn('stale_background_result_discarded',self.phases())
        self.assertEqual(len(self.voice.client.prompts),1)
        self.assertEqual(self.conversation.mask.finished,['Hello there.'])

    async def test_failed_analyst_notification_reaches_speech_once_with_no_tool_authority(self):
        self.voice.background=self.conversation.brain
        job={'job_id':'failed','status':'failed','revision':0,'summary':'UNVERIFIED_PARTIAL','announced':False}
        self.conversation.brain.jobs['failed']=job
        notice="I couldn't finish that analysis; I don't have a result."
        test=self
        class FailureClient(FakeClient):
            def ask(client,prompt,timeout,on_event):
                client.prompts.append(prompt)
                test.assertIn('could not finish',prompt)
                test.assertNotIn('UNVERIFIED_PARTIAL',prompt)
                test.assertFalse(client._bridge.allow_tools)
                on_event({'type':'message_update','assistantMessageEvent':{'delta':notice}})
                return result(notice)
        self.voice.client=FailureClient()
        self.voice.task(self.voice.model_worker())
        delivery=asyncio.create_task(self.conversation.deliver_results())
        try:
            await self.wait_for(lambda:'thinking_finished' in self.phases())
            await asyncio.sleep(.23)
            self.assertTrue(job['announced'])
            self.assertEqual(len(self.voice.client.prompts),1)
            self.assertEqual(self.conversation.mask.finished,[notice])
            self.assertEqual(len(self.conversation.mask.begins),1)
            self.assertEqual(len([e for e in self.socket.events if e.get('type')=='brain_delivery']),1)
        finally:
            delivery.cancel();await asyncio.gather(delivery,return_exceptions=True)

    async def test_failed_analyst_notice_can_be_cancelled_in_queue_or_after_generation(self):
        self.voice.background=self.conversation.brain
        jobs=self.conversation.brain.jobs
        jobs['queued']={'job_id':'queued','status':'failed','revision':0,'summary':'Failure'}
        await self.voice.context('Failure notice',job_id='queued')
        await self.conversation.handle({'type':'cancel_background','job_id':'queued'})
        self.voice.task(self.voice.model_worker())
        await self.wait_for(lambda:'stale_background_result_discarded' in self.phases())
        self.assertEqual(jobs['queued']['status'],'cancelled')
        self.assertEqual(self.voice.client.prompts,[])
        jobs['active']={'job_id':'active','status':'failed','revision':0,'summary':'Failure'}
        await self.voice.context('Failure notice',job_id='active')
        await self.wait_for(lambda:'thinking_finished' in self.phases())
        before=self.conversation.mask.epoch
        await self.conversation.handle({'type':'cancel_background','job_id':'active'})
        self.assertEqual(jobs['active']['status'],'cancelled')
        self.assertGreater(self.conversation.mask.epoch,before)
        with self.assertRaises(StaleTurn):
            await self.voice.model_event({'type':'message_update','assistantMessageEvent':{'delta':'Late failure notice'}},self.voice.revision,'late',job_id='active')

    async def test_failed_analyst_notice_cannot_cross_user_revision(self):
        self.voice.background=self.conversation.brain
        self.conversation.brain.jobs['old']={'job_id':'old','status':'failed','revision':0,'summary':'Failure'}
        await self.voice.context('Failure notice',job_id='old')
        self.conversation.user_revision=1
        self.voice.task(self.voice.model_worker())
        await self.wait_for(lambda:'stale_background_result_discarded' in self.phases())
        self.assertEqual(self.voice.client.prompts,[])
        self.assertEqual(self.conversation.mask.finished,[])

    async def test_endpoint_configuration_validates_default_and_bounds(self):
        def create():
            return CascadeVoice(self.runtime, self.folder.name, self.conversation.emit, None,
                                self.conversation.realtime_event)
        with patch('cascade_voice.load_env', return_value={}), patch.dict('os.environ', {}, clear=True):
            self.assertEqual(create().endpoint_ms, 300)
            for value in ('100', '700', '2000'):
                with patch.dict('os.environ', {'MIST_LAB_ENDPOINT_MS': value}):
                    self.assertEqual(create().endpoint_ms, int(value))
            for value in ('99', '2001', '0', '-1', '300.5', '', 'false'):
                with self.subTest(value=value), patch.dict('os.environ', {'MIST_LAB_ENDPOINT_MS': value}):
                    with self.assertRaisesRegex(ValueError, 'MIST_LAB_ENDPOINT_MS'):
                        create()

    async def test_endpoint_value_reaches_provider_ready_and_debug(self):
        self.voice.endpoint_ms = 700
        self.voice.env['DEEPGRAM_API_KEY'] = 'offline-placeholder'
        uplink = SimpleNamespace(close=AsyncMock())
        http = SimpleNamespace(ws_connect=AsyncMock(return_value=uplink), close=AsyncMock())
        def discard_task(coroutine):
            coroutine.close()
        with patch.object(self.voice, 'make_client', return_value=self.voice.client), \
                patch.object(self.voice, 'task', side_effect=discard_task), \
                patch('cascade_voice.aiohttp.ClientSession', return_value=http):
            await self.voice.start()
        query = parse_qs(urlparse(http.ws_connect.call_args.args[0]).query)
        self.assertEqual(query['endpointing'], ['700'])
        self.assertEqual(query['utterance_end_ms'], ['1000'])
        self.assertEqual([e['endpoint_ms'] for e in self.socket.events if e.get('type') == 'ready'], [700])
        debug = [e for e in self.socket.events if e.get('type') == 'debug_model']
        self.assertTrue(debug)
        self.assertTrue(all(e['endpoint_ms'] == 700 for e in debug))

    async def test_lab_rejects_invalid_endpoint_before_creating_app(self):
        from lab_server import create_lab
        for value in (99, 2001, True, 700.5, '700'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'endpoint'):
                create_lab(SimpleNamespace(endpoint_ms=value))

    async def test_lab_serves_startup_copies_and_records_effective_endpoint(self):
        from aiohttp import web
        import lab_server
        output = Path(self.folder.name) / 'lab-output'
        output.mkdir()
        fixtures = Path(self.folder.name) / 'fixtures'
        (fixtures / 'audio').mkdir(parents=True)
        (fixtures / 'manifest.json').write_text('{"fixtures":[]}', encoding='utf-8')
        args = SimpleNamespace(endpoint_ms=700, backend='cascade', model='gpt-oss-120b',
                               provider='cerebras', floor='selective', background_model='gpt-6-luna',
                               run_dir=str(output), fixtures=str(fixtures))
        logger = logging.getLogger('mist.voice')
        previous_handlers = list(logger.handlers)
        try:
            with patch.dict('os.environ', {}), patch.object(lab_server.server, 'NativeVoice'), \
                    patch.object(lab_server.server, 'Conversation'), \
                    patch.object(lab_server.server, 'create_app', return_value=web.Application()):
                app = lab_server.create_lab(args)
            routes = {route.resource.canonical: route for route in app.router.routes()}
            for url, name in (('/lab', 'browser_lab.html'), ('/lab.js', 'browser_lab.js')):
                response = await routes[url].handler(None)
                expected = output / 'sources' / 'brain' / 'benchmarks' / 'naturalness' / name
                self.assertEqual(response._path, expected)
                self.assertEqual(expected.read_bytes(), (HERE / name).read_bytes())
            manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['endpoint_ms'], 700)
        finally:
            for handler in list(logger.handlers):
                if handler not in previous_handlers:
                    logger.removeHandler(handler)
                    handler.close()

    async def test_uplink_supplies_paced_trailing_silence_after_fixture(self):
        writes = []
        complete = asyncio.Event()
        class Uplink:
            async def send_bytes(inner, pcm):
                writes.append((time.perf_counter(), pcm))
                if sum(len(data) for _, data in writes) >= 19 * 640:
                    complete.set()
            async def close(inner):
                pass
        self.voice.socket = Uplink()
        self.voice.track.append(b'\x01\x00' * 320)
        self.voice.track.append(b'\x02\x00' * 80)
        self.voice.task(self.voice.send_audio())
        await asyncio.wait_for(complete.wait(), timeout=2)
        raw = b''.join(pcm for _, pcm in writes)
        self.assertEqual(raw[:640], b'\x01\x00' * 320)
        self.assertEqual(raw[640:1280], b'\x02\x00' * 80 + b'\0' * 480)
        self.assertEqual(raw[1280:], b'\0' * (len(raw) - 1280))
        self.assertGreaterEqual((len(raw) - 1280) / 32000, .3)
        self.assertTrue(all(0 < len(pcm) <= 3200 and len(pcm) % 640 == 0 for _, pcm in writes))
        self.assertGreaterEqual(writes[-1][0] - writes[0][0], .30)

    async def test_ten_second_uplink_preserves_all_samples_under_timer_and_write_jitter(self):
        track = PCMTrack()
        expected = [(index + 1).to_bytes(2, 'little') * 320 for index in range(500)]
        writes = []
        now, produced, max_queued, wakes = 0.0, 0, 0, 0
        def clock():
            return now
        def advance(seconds):
            nonlocal now, produced, max_queued
            now += seconds
            while produced < len(expected) and produced * .02 <= now + 1e-9:
                track.append(expected[produced])
                produced += 1
                max_queued = max(max_queued, track.queue.qsize())
        async def sleep(delay):
            nonlocal wakes
            # 15.625 ms timer ticks, recurring busy-loop delays up to 187.5 ms.
            ticks = math.ceil((now + delay) / .015625) * .015625
            jitter = (.0, .015625, .03125, .09375, .1875, .0)[wakes % 6]
            wakes += 1
            advance(max(0, ticks - now) + jitter)
        async def send_bytes(pcm):
            writes.append((now, pcm))
            advance(.006)  # Slow socket writes also must not add permanent drift.
        advance(0)
        await send_paced_pcm(track, send_bytes, lambda: now >= 10.6 and track.queue.empty(),
                             clock=clock, sleep=sleep)
        frames = [pcm[offset:offset + 640] for _, pcm in writes for offset in range(0, len(pcm), 640)]
        speech = [pcm for pcm in frames if pcm != b'\0' * 640]
        self.assertEqual(speech, expected)
        self.assertLess(max_queued, 30)
        self.assertTrue(any(len(pcm) > 640 for _, pcm in writes), 'Jitter must exercise bounded batching')
        self.assertTrue(all(len(pcm) <= 3200 and len(pcm) % 640 == 0 for _, pcm in writes))
        sent = 0
        for at, pcm in writes:
            sent += len(pcm) / 640
            self.assertLessEqual(sent * .02, at + .020001, 'Never upload future audio to drain the queue')
        self.assertTrue(all(b[0] - a[0] >= .004999 for a, b in zip(writes, writes[1:])))
        self.assertGreaterEqual(sum(frame == b'\0' * 640 for frame in frames) * .02, .3)
        self.assertLessEqual(now - len(frames) * .02, .21)

    async def test_preloaded_uplink_cannot_drain_ahead_of_audio_clock(self):
        track = PCMTrack()
        for _ in range(30):
            track.append(b'\x01\x00' * 320)
        now, writes = 0.0, []
        async def sleep(delay):
            nonlocal now
            now += max(delay, .001)
        async def send_bytes(pcm):
            writes.append((now, pcm))
        await send_paced_pcm(track, send_bytes, lambda: now >= .22,
                             clock=lambda: now, sleep=sleep)
        sent_frames = sum(len(pcm) // 640 for _, pcm in writes)
        self.assertLessEqual(sent_frames, 12)
        self.assertGreaterEqual(track.queue.qsize(), 18)
        self.assertGreaterEqual(len(writes), 10)

    async def test_close_cancels_inflight_send_without_false_fatal_error(self):
        entered, closing = asyncio.Event(), asyncio.Event()
        class ClosingUplink:
            async def send_bytes(inner, pcm):
                entered.set()
                await closing.wait()
                raise ConnectionResetError('Socket closed during an in-flight send')
            async def close(inner):
                closing.set()
                await asyncio.sleep(.01)
        self.voice.socket = ClosingUplink()
        self.voice.task(self.voice.send_audio())
        await asyncio.wait_for(entered.wait(), timeout=1)
        await self.voice.close()
        await self.voice.transport_failure('stt_send_failed', ConnectionResetError())
        self.assertNotIn('stt_send_failed', self.phases())
        self.assertFalse(any(e.get('fatal') for e in self.socket.events))

    async def test_active_transport_failure_remains_visible(self):
        await self.voice.transport_failure('stt_send_failed', ConnectionResetError())
        self.assertIn('stt_send_failed', self.phases())
        self.assertTrue(any(e.get('fatal') for e in self.socket.events))

    async def test_backchannel_during_playback_preserves_floor_and_no_reply(self):
        self.conversation.playback_busy = True
        self.conversation.assistant_turn = 'old'
        await self.voice.stt_event({'type': 'SpeechStarted', 'timestamp': 1})
        await self.voice.stt_event(recognition('Yeah.'))
        self.assertEqual(self.conversation.mask.epoch, 0)
        self.assertEqual(self.voice.requests.qsize(), 0)
        self.assertIn('floor_backchannel_kept', self.phases())

    async def test_standalone_acknowledgement_is_not_suppressed(self):
        await self.voice.stt_event(recognition('Okay.'))
        self.assertEqual(self.voice.requests.qsize(), 1)
        self.assertNotIn('floor_backchannel_kept', self.phases())

    async def test_backchannel_prefix_expanding_to_correction_interrupts(self):
        self.conversation.playback_busy = True
        self.conversation.assistant_turn = 'old'
        await self.voice.stt_event(recognition('Yeah', final=False, endpoint=False))
        self.assertEqual(self.conversation.mask.epoch, 0)
        await self.voice.stt_event(recognition('Yeah, but read it slower.', final=False, endpoint=False))
        self.assertEqual(self.conversation.mask.epoch, 1)
        await self.voice.stt_event(recognition('Yeah, but read it slower.'))
        self.assertEqual(self.voice.requests.qsize(), 1)
        self.assertEqual(self.conversation.user_request_text, 'Yeah, but read it slower.')

    async def test_cancel_all_interrupts_on_vad_before_words(self):
        self.voice.floor = 'cancel_all'
        self.conversation.playback_busy = True
        self.conversation.assistant_turn = 'old'
        await self.voice.stt_event({'type': 'SpeechStarted', 'timestamp': 1})
        self.assertEqual(self.conversation.mask.epoch, 1)
        await self.voice.stt_event(recognition('Mmhm.'))
        self.assertEqual(self.voice.requests.qsize(), 1)

    async def test_incomplete_clause_waits_and_merges_continuation(self):
        self.voice.hold_s = .025
        await self.voice.stt_event(recognition('I wanted to'))
        self.assertEqual(self.voice.requests.qsize(), 0)
        self.assertIn('floor_incomplete_hold', self.phases())
        await self.voice.stt_event({'type': 'SpeechStarted', 'timestamp': 1.2})
        await self.voice.stt_event(recognition('read that again.', start=1.2))
        self.assertEqual(self.voice.requests.qsize(), 1)
        self.assertEqual(self.conversation.user_request_text, 'I wanted to read that again.')
        await asyncio.sleep(.04)
        self.assertEqual(self.voice.requests.qsize(), 1)

    async def test_incomplete_clause_hold_expires(self):
        self.voice.hold_s = .01
        await self.voice.stt_event(recognition('Because'))
        await self.wait_for(lambda: self.voice.requests.qsize() == 1)
        committed = [e for e in self.socket.events if e.get('phase') == 'user_committed']
        self.assertEqual(committed[0]['endpoint'], 'incomplete_hold_expired')

    async def test_stale_stream_and_tools_are_rejected(self):
        bridge = RevisionBridge(self.voice, self.voice.revision, 0, 'Show happy')
        old_revision = self.voice.revision
        await self.voice.interrupt()
        with self.assertRaises(StaleTurn):
            await self.voice.model_event({'type': 'message_update', 'assistantMessageEvent': {'delta': 'old'}}, old_revision, 'old')
        with self.assertRaises(StaleTurn):
            await bridge.execute({'name': 'set_expression', 'arguments': {'expression': 'happy'}})
        self.assertEqual(self.voice.bridge.receipts, [])
        self.assertEqual(self.conversation.mask.texts, [])

    async def test_revision_rechecked_after_debug_send_before_tool(self):
        original_emit = self.voice.emit
        async def interrupting_emit(event):
            await original_emit(event)
            if event.get('type') == 'debug_tool' and event.get('phase') == 'started':
                self.voice.revision += 1
        self.voice.emit = interrupting_emit
        bridge = RevisionBridge(self.voice, self.voice.revision, 0, 'Show happy')
        with self.assertRaises(StaleTurn):
            await bridge.execute({'name': 'set_expression', 'arguments': {'expression': 'happy'}})
        self.assertEqual(self.voice.bridge.receipts, [])

    async def test_new_input_revokes_queued_model_request(self):
        await self.voice.say_text('Old question.')
        await self.voice.say_text('Replacement question.')
        self.voice.task(self.voice.model_worker())
        await self.wait_for(lambda: 'thinking_finished' in self.phases())
        self.assertEqual(self.voice.client.prompts, ['Replacement question.'])
        self.assertIn('stale_queued_turn_discarded', self.phases())

    async def test_late_old_generation_cannot_cancel_replacement(self):
        ready, proceed = threading.Event(), threading.Event()
        def fresh_client():
            client = FakeClient()
            client.new_session()
            return client
        self.voice.make_client = fresh_client
        first = True
        original_ask = self.voice.client.ask
        def ask(prompt, timeout, on_event):
            nonlocal first
            if not first:
                return original_ask(prompt, timeout, on_event)
            first = False
            on_event({'type': 'message_update', 'assistantMessageEvent': {'delta': 'Old beginning. '}})
            ready.set()
            if not proceed.wait(2):
                raise RuntimeError('Test synchronization expired')
            on_event({'type': 'message_update', 'assistantMessageEvent': {'delta': 'Stale ending.'}})
            return result('Old beginning. Stale ending.')
        self.voice.client.ask = ask
        self.voice.task(self.voice.model_worker())
        await self.voice.say_text('Read the old passage.')
        await self.wait_for(ready.is_set)
        await self.voice.say_text('Actually just say hello.')
        proceed.set()
        await self.wait_for(lambda: 'thinking_finished' in self.phases())
        self.assertNotIn('Stale ending.', self.conversation.mask.texts)
        self.assertEqual(self.conversation.mask.texts[-2:], ['Hello ', 'there.'])
        self.assertIn('Read the old passage.', self.voice.client.prompts[-1])
        self.assertIn('Actually just say hello.', self.voice.client.prompts[-1])
        self.assertIn('interrupted_generation_discarded', self.phases())
        self.assertEqual(self.voice.client.sessions, 1)

    async def test_cerebras_correction_does_not_wait_for_stale_request(self):
        old_client = self.voice.client
        started, release = threading.Event(), threading.Event()
        def blocked_ask(prompt, timeout, on_event):
            old_client.prompts.append(prompt)
            started.set()
            if not release.wait(3):
                raise RuntimeError('Test synchronization expired')
            on_event({'type': 'message_update', 'assistantMessageEvent': {'delta': 'Stale answer.'}})
            return result('Stale answer.')
        old_client.ask = blocked_ask
        replacement = FakeClient()
        self.voice.make_client = lambda: replacement
        self.voice.task(self.voice.model_worker())
        try:
            await self.voice.say_text('Old question.')
            await self.wait_for(started.is_set)
            await self.voice.interrupt()
            await self.wait_for(lambda: self.voice.client is None)
            await self.voice.submit_text('Corrected question.')
            await self.wait_for(lambda: 'thinking_finished' in self.phases())
            self.assertIs(self.voice.client, replacement)
            self.assertFalse(old_client.closed)
            self.assertIn('Corrected question.', replacement.prompts[0])
            self.assertNotIn('Stale answer.', self.conversation.mask.texts)
        finally:
            release.set()
        await self.wait_for(lambda: old_client.closed)
        self.assertIs(self.voice.client, replacement)
        self.assertNotIn('Stale answer.', self.conversation.mask.texts)

    async def test_background_context_is_delivered_without_tool_authority(self):
        self.voice.task(self.voice.model_worker())
        await self.voice.context('{"result":"Battery unavailable"}')
        await self.wait_for(lambda: 'thinking_finished' in self.phases())
        self.assertIn('Battery unavailable', self.voice.client.prompts[0])
        with self.assertRaises(ValueError):
            await self.voice.client._bridge.execute({'name': 'stop_robot', 'arguments': {}})
        self.assertFalse(self.runtime.estop)

    async def test_real_runtime_receipt_and_background_stub_are_disclosed(self):
        bridge = RevisionBridge(self.voice, self.voice.revision, 0, 'Read the sensors')
        await bridge.execute({'name': 'get_sensor_snapshot', 'arguments': {}})
        self.assertEqual(self.voice.bridge.receipts[-1]['name'], 'get_sensor_snapshot')
        await bridge.execute({'name': 'start_background_task', 'arguments': {'question': 'Compare the two options'}})
        events = [e for e in self.socket.events if e.get('type') == 'tool']
        self.assertEqual(events[-1]['background_mode'], 'evaluation_stub')
        self.assertTrue(events[-1]['result']['fixture'])


class PureTests(unittest.TestCase):
    def test_pcm_bounds_are_atomic(self):
        track = PCMTrack()
        track.append(b'\0' * 640)
        self.assertEqual(track.queue.qsize(), 1)
        for bad in (b'1', b'\0' * 6402, 'text'):
            with self.assertRaises(ValueError):
                track.append(bad)
        for _ in range(track.queue.maxsize - 2):
            track.append(b'\0' * 640)
        with self.assertRaises(ValueError):
            track.append(b'\0' * 1280)
        self.assertEqual(track.queue.qsize(), track.queue.maxsize - 1)
        self.assertEqual(track.statistics()['rejected_samples'], 640)
        self.assertLessEqual(track.statistics()['capacity_ms'], 2000)

    def test_floor_rules_are_explicit(self):
        self.assertTrue(is_backchannel('Mm-hm.'))
        self.assertTrue(is_backchannel('Yeah.'))
        self.assertFalse(is_backchannel('Yeah, but stop.'))
        self.assertFalse(is_backchannel('No.'))
        self.assertTrue(incomplete_clause('I was going to...'))
        self.assertFalse(incomplete_clause('I want to stop.'))


if __name__ == '__main__':
    unittest.main()
