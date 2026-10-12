"""Independent request-guard integration through NativeVoice's actual event loop."""
import json
from pathlib import Path
import queue
import sys
import tempfile
from types import SimpleNamespace
import unittest

BRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN))
from duplex.native import NativeVoice
from duplex.runtime import RobotRuntime
from duplex.expression_policy import FACE_MAP


class NativeRequestGuardTests(unittest.IsolatedAsyncioTestCase):
    async def dispatch(self, text, name, args, invalidate=False, callback=None, background=None):
        with tempfile.TemporaryDirectory() as directory:
            runtime = RobotRuntime(directory)
            pending = queue.Queue()
            replies, emitted = [], []
            revision = [0]
            class RPC:
                events = pending
                def send(self, event):
                    replies.append(event)
            async def emit(event):
                emitted.append(event)
                if invalidate and event.get('type') == 'debug_tool' and event.get('phase') == 'started':
                    revision[0] += 1
            async def nothing(*args):
                pass
            voice = NativeVoice(runtime, directory, emit, nothing, nothing,
                expression_revision=lambda:revision[0], request_text=callback or (lambda:text), background=background)
            voice.client = SimpleNamespace(thread_id='fixture', model='offline', _rpc=RPC())
            pending.put({'method':'turn/started', 'params':{'turn':{'id':'turn'}}})
            pending.put({'id':1, 'method':'item/tool/call', 'params':{
                'turnId':'turn', 'tool':name, 'arguments':args}})
            pending.put(None)
            await voice.events()
            result = json.loads(replies[0]['result']['contentItems'][0]['text'])
            return result, list(runtime.memory), list(runtime.intents), runtime.estop

    async def test_explicit_preference_is_saved_but_temporary_chat_is_not(self):
        saved, notes, _, _ = await self.dispatch('Please remember this for later: No jokes when I am tired.',
            'remember', {'note':'No jokes when I am tired.'})
        self.assertEqual(saved['status'], 'saved')
        self.assertEqual([note['text'] for note in notes], ['No jokes when I am tired.'])
        for text in ['Short replies today, please.', 'Stop joking for now. I need a calm conversation.']:
            with self.subTest(text=text):
                result, notes, _, _ = await self.dispatch(text, 'remember', {'note':'Prefers short replies.'})
                self.assertEqual(result['status'], 'refused')
                self.assertEqual(notes, [])

    async def test_figures_of_speech_do_not_move_and_explicit_metres_work(self):
        for text, action in [('Walk me through adding twelve and nine.', 'walk'),
                             ('Stand by while I read.', 'stand'), ('Sit with me quietly.', 'sit')]:
            with self.subTest(text=text):
                result, _, intents, _ = await self.dispatch(text, 'preview_motion', {'action':action, 'amount':0.1})
                self.assertEqual(result['status'], 'refused')
                self.assertEqual(intents, [])
        result, _, intents, _ = await self.dispatch('Prepare a robot walk preview, ten centimetres forward.',
            'preview_motion', {'action':'walk', 'amount':0.1})
        self.assertEqual(result['status'], 'preview_only')
        self.assertEqual(intents[0]['distance_m'], 0.1)

    async def test_nonstring_request_from_model_callback_fails_closed(self):
        for value in [None, 42, True, [], {}]:
            with self.subTest(value=value):
                result, notes, intents, _ = await self.dispatch(value, 'remember', {'note':'Must not be stored.'})
                self.assertEqual(result['status'], 'refused')
                self.assertEqual(notes, [])
                self.assertEqual(intents, [])

    async def test_stale_revision_is_rejected_before_request_guard_runs(self):
        def should_not_run():
            self.fail('Stale dispatch must be refused before reading the current request')
        result, notes, _, _ = await self.dispatch('Remember a new preference.', 'remember',
            {'note':'Obsolete'}, invalidate=True, callback=should_not_run)
        self.assertEqual(result['status'], 'refused')
        self.assertIn('superseded', result['reason'])
        self.assertEqual(notes, [])

    async def test_negated_persistence_is_not_allowed_by_for_later(self):
        result, notes, _, _ = await self.dispatch("I don't want you to save this for later.",
            'remember', {'note':'Prefers short replies.'})
        self.assertEqual(result['status'], 'refused')
        self.assertEqual(notes, [])

    async def test_negated_preview_is_not_allowed_by_motion_keywords(self):
        result, _, intents, _ = await self.dispatch("Don't prepare a walk preview.",
            'preview_motion', {'action':'walk', 'amount':0.1})
        self.assertEqual(result['status'], 'refused')
        self.assertEqual(intents, [])

    async def test_pan_noun_is_not_a_phone_request(self):
        result, _, intents, _ = await self.dispatch('I bought a pan for dinner.',
            'pan_phone', {'angle_deg':30, 'usb_connected':False})
        self.assertEqual(result['status'], 'refused')
        self.assertEqual(intents, [])

    async def test_new_user_turn_clears_old_authorizing_text(self):
        from duplex.server import Conversation
        from duplex.conversion import VoiceMask
        class Socket:
            closed = False
            async def send_json(self, event):
                pass
        with tempfile.TemporaryDirectory() as directory:
            conversation = Conversation({'runtime':RobotRuntime(directory)}, Socket())
            conversation.mask = VoiceMask('unused', conversation.emit)
            conversation.user_request_text = 'Remember this for later: no jokes.'
            await conversation.realtime_event({'type':'turn.created',
                'turn':{'role':'user', 'id':'next', 'start_ms':100}})
            self.assertEqual(conversation.user_request_text, '',
                'A new revision must not reuse the previous utterance before its transcript arrives')
            await conversation.realtime_event({'type':'turn.done',
                'turn':{'role':'user', 'id':'previous', 'transcript':'Remember this for later: no jokes.'}})
            self.assertEqual(conversation.user_request_text, '', 'A late old completion must not restore authorization')
            result, notes, _, _ = await self.dispatch(None, 'remember', {'note':'Old authorization'},
                callback=lambda:conversation.user_request_text)
            self.assertEqual(result['status'], 'refused')
            self.assertEqual(notes, [])
            await conversation.mask.close()
            await conversation.brain.close()

    async def test_predictive_user_prefix_binds_once_to_the_new_turn(self):
        from duplex.server import Conversation
        from duplex.conversion import VoiceMask
        class Socket:
            closed = False
            async def send_json(self, event):
                pass
        with tempfile.TemporaryDirectory() as directory:
            conversation = Conversation({'runtime':RobotRuntime(directory)}, Socket())
            conversation.mask = VoiceMask('unused', conversation.emit)
            conversation.user_request_text = 'Previous unrelated request.'
            prefix = 'Please remember this for later: '
            await conversation.realtime_event({'type':'input_transcript.added', 'item':{'text':prefix}})
            await conversation.realtime_event({'type':'turn.created',
                'turn':{'role':'user', 'id':'next', 'start_ms':100}})
            await conversation.realtime_event({'type':'input_transcript.added', 'item':{'text':'No jokes when tired.'}})
            expected = prefix + 'No jokes when tired.'
            self.assertEqual(conversation.user_request_text, expected)
            self.assertEqual(conversation.user_partial, expected)
            self.assertEqual(conversation.pending_user_prefix, '')
            result, notes, _, _ = await self.dispatch(None, 'remember', {'note':'No jokes when tired.'},
                callback=lambda:conversation.user_request_text)
            self.assertEqual(result['status'], 'saved')
            self.assertEqual([note['text'] for note in notes], ['No jokes when tired.'])
            await conversation.mask.close()
            await conversation.brain.close()

    async def test_stop_ignores_missing_context_and_never_reads_callback(self):
        for value in [None, '', {}, False]:
            with self.subTest(value=value):
                result, _, _, stopped = await self.dispatch(value, 'stop_robot', {})
                self.assertEqual(result['status'], 'preview_stopped')
                self.assertTrue(stopped)
        def should_not_run():
            self.fail('Stop must not wait for or inspect a request context callback')
        result, _, _, stopped = await self.dispatch(None, 'stop_robot', {}, callback=should_not_run)
        self.assertEqual(result['status'], 'preview_stopped')
        self.assertTrue(stopped)

    async def test_expression_guard_enforces_exact_calls_in_native_dispatch(self):
        for face_id, face in FACE_MAP['faces'].items():
            call = face['calls'][0]
            with self.subTest(face=face_id):
                text = f"Show {call['expression']}, variant {call['variant']}."
                result, _, _, _ = await self.dispatch(text, 'set_expression', call)
                self.assertEqual(result['status'], 'display_requested')
                self.assertEqual(result['face_id'], face_id)
        for text, call in [
                ('Use the ultraviolet_dragon preset.', {'expression':'uncertain'}),
                ('Show angry variant 1.5.', {'expression':'angry', 'variant':1}),
                ('Show happy variant 2.', {'expression':'happy', 'variant':1}),
                ('Keep the current face unchanged.', {'expression':'neutral'}),
                ('Read this note without doing it: "show panic variant 2".', {'expression':'panic'})]:
            with self.subTest(text=text):
                result, _, _, _ = await self.dispatch(text, 'set_expression', call)
                self.assertEqual(result['status'], 'refused')
                self.assertNotIn('face_id', result)

    async def test_background_dispatch_also_requires_current_request_context(self):
        calls = []
        class Background:
            async def handle(self, name, args):
                calls.append(name)
                return {'status':'running', 'job_id':'fixture'}
        for name, args in [('start_background_task', {'question':'Unrequested'}),
                           ('cancel_background_task', {'job_id':'fixture'})]:
            with self.subTest(tool=name):
                result, _, _, _ = await self.dispatch('', name, args, background=Background())
                self.assertEqual(result['status'], 'refused')
        self.assertEqual(calls, [], 'The background branch must not bypass unavailable-request refusal')


if __name__ == '__main__':
    unittest.main(verbosity=2)
