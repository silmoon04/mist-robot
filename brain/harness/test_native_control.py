"""Independent event-order regressions. No provider, microphone or actuator calls."""
import asyncio
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


class ControlEventOrderTests(unittest.IsolatedAsyncioTestCase):
    async def run_trace(self, events):
        with tempfile.TemporaryDirectory() as directory:
            runtime = RobotRuntime(directory)
            notifications = queue.Queue()
            replies = []
            emitted = []
            revision = [0]
            background_calls = []
            class Background:
                async def handle(self, name, args):
                    background_calls.append((name, args))
                    return {'status':'running', 'job_id':'fixture-job'}
            class RPC:
                def __init__(self):
                    self.events = notifications
                def send(self, event):
                    replies.append(event)
            async def emit(event):
                emitted.append(event)
                if event.get('type') == 'debug_tool' and event.get('phase') == 'started' and event.get('call_id') == 'invalidate':
                    revision[0] = 1
            async def nothing(*args):
                pass
            voice = NativeVoice(runtime, directory, emit, nothing, nothing,
                                expression_revision=lambda: revision[0], background=Background())
            voice.client = SimpleNamespace(thread_id='fixture', model='offline', _rpc=RPC())
            for event in events + [None]:
                notifications.put(event)
            await voice.events()
            return runtime.estop, list(runtime.intents), list(runtime.memory), replies, emitted, background_calls

    def call(self, number, name, args=None, turn='old', call_id=None):
        return {'id':number, 'method':'item/tool/call', 'params':{
            'turnId':turn, 'callId':call_id or str(number), 'tool':name, 'arguments':args or {}}}

    def started(self, turn):
        return {'method':'turn/started', 'params':{'turn':{'id':turn}}}

    async def test_stop_bypasses_exhausted_tool_budget(self):
        trace = [self.started('old')]
        trace += [self.call(i, 'get_sensor_snapshot') for i in range(1, 13)]
        trace += [self.call(13, 'stop_robot')]
        stopped, _, _, replies, _, _ = await self.run_trace(trace)
        self.assertTrue(stopped, 'A stop must not be refused after 12 ordinary tool calls')
        self.assertTrue(replies[-1]['result']['success'])

    async def test_superseded_motion_call_has_no_intent(self):
        trace = [self.started('old'),
                 self.call(1, 'get_sensor_snapshot', call_id='invalidate'),
                 self.started('new'),
                 self.call(2, 'preview_motion', {'action':'walk', 'amount':0.1}, turn='old')]
        _, intents, _, replies, _, _ = await self.run_trace(trace)
        self.assertEqual(intents, [], 'An old turn must not prepare a movement after interruption')
        self.assertFalse(replies[-1]['result']['success'])

    async def test_superseded_memory_call_does_not_write(self):
        trace = [self.started('old'),
                 self.call(1, 'get_sensor_snapshot', call_id='invalidate'),
                 self.started('new'),
                 self.call(2, 'remember', {'note':'Old request that was corrected'}, turn='old')]
        _, _, notes, replies, _, _ = await self.run_trace(trace)
        self.assertEqual(notes, [], 'An old turn must not save a superseded preference')
        self.assertFalse(replies[-1]['result']['success'])

    async def test_stop_from_superseded_turn_still_stops(self):
        trace = [self.started('old'),
                 self.call(1, 'get_sensor_snapshot', call_id='invalidate'),
                 self.started('new'), self.call(2, 'stop_robot', turn='old')]
        stopped, _, _, replies, _, _ = await self.run_trace(trace)
        self.assertTrue(stopped)
        self.assertTrue(replies[-1]['result']['success'])

    async def test_superseded_pan_and_background_changes_are_refused(self):
        trace = [self.started('old'),
                 self.call(1, 'get_sensor_snapshot', call_id='invalidate'),
                 self.started('new'),
                 self.call(2, 'pan_phone', {'angle_deg':30, 'usb_connected':False}, turn='old'),
                 self.call(3, 'start_background_task', {'question':'Old question'}, turn='old'),
                 self.call(4, 'cancel_background_task', {'job_id':'fixture-job'}, turn='old')]
        _, intents, _, replies, _, background_calls = await self.run_trace(trace)
        self.assertEqual(intents, [])
        self.assertEqual(background_calls, [])
        self.assertTrue(all(not reply['result']['success'] for reply in replies))

    async def test_interruption_inside_debug_emit_prevents_action_dispatch(self):
        for tool, args in [
                ('remember', {'note':'Superseded'}),
                ('preview_motion', {'action':'stand'}),
                ('pan_phone', {'angle_deg':30, 'usb_connected':False}),
                ('set_expression', {'expression':'happy'}),
                ('start_background_task', {'question':'Superseded'}),
                ('cancel_background_task', {'job_id':'fixture-job'})]:
            with self.subTest(tool=tool):
                trace = [self.started('old'), self.call(1, tool, args, call_id='invalidate')]
                _, intents, notes, replies, emitted, background_calls = await self.run_trace(trace)
                self.assertEqual(intents, [])
                self.assertEqual(notes, [])
                self.assertEqual(background_calls, [])
                self.assertFalse(replies[0]['result']['success'])
                receipt = next(event for event in emitted if event.get('type') == 'tool')
                self.assertEqual(receipt['result']['status'], 'refused')

    async def test_old_calls_do_not_consume_current_turn_budget(self):
        trace = [self.started('old'), self.call(1, 'get_sensor_snapshot', call_id='invalidate'),
                 self.started('new')]
        trace += [self.call(i, 'get_sensor_snapshot', turn='old') for i in range(2, 22)]
        trace += [self.call(i, 'get_sensor_snapshot', turn='new') for i in range(22, 34)]
        trace += [self.call(34, 'get_sensor_snapshot', turn='new'), self.call(35, 'stop_robot', turn='new')]
        stopped, _, _, replies, _, _ = await self.run_trace(trace)
        by_id = {reply['id']:reply['result']['success'] for reply in replies}
        self.assertTrue(all(not by_id[i] for i in range(1, 22)))
        self.assertTrue(all(by_id[i] for i in range(22, 34)))
        self.assertFalse(by_id[34])
        self.assertTrue(by_id[35])
        self.assertTrue(stopped)

    async def test_valid_current_actions_work_after_old_calls_are_rejected(self):
        trace = [self.started('old'), self.call(1, 'get_sensor_snapshot', call_id='invalidate'),
                 self.started('new'),
                 self.call(2, 'remember', {'note':'Old value'}, turn='old'),
                 self.call(3, 'remember', {'note':'Corrected value'}, turn='new'),
                 self.call(4, 'pan_phone', {'angle_deg':-20, 'usb_connected':False}, turn='new'),
                 self.call(5, 'start_background_task', {'question':'Current question'}, turn='new')]
        _, intents, notes, replies, _, background_calls = await self.run_trace(trace)
        self.assertEqual([note['text'] for note in notes], ['Corrected value'])
        self.assertEqual([intent['action'] for intent in intents], ['phone_pan'])
        self.assertEqual(background_calls, [('start_background_task', {'question':'Current question'})])
        self.assertEqual([reply['result']['success'] for reply in replies], [False, False, True, True, True])

    async def test_direct_stop_works_while_background_dispatch_is_waiting(self):
        from duplex.server import Conversation
        from duplex.conversion import VoiceMask
        entered, release = asyncio.Event(), asyncio.Event()
        class Background:
            async def handle(self, name, args):
                entered.set()
                await release.wait()
                return {'status':'running', 'job_id':'fixture-job'}
        class Socket:
            closed = False
            async def send_json(self, event):
                pass
        notifications = queue.Queue()
        class RPC:
            def __init__(self):
                self.events = notifications
            def send(self, event):
                pass
            def request(self, *args, **kwargs):
                return {}
        async def nothing(*args):
            pass
        with tempfile.TemporaryDirectory() as directory:
            conversation = Conversation({'runtime':RobotRuntime(directory)}, Socket())
            conversation.mask = VoiceMask('unused', conversation.emit)
            conversation.voice = NativeVoice(conversation.runtime, directory, conversation.emit, nothing, nothing,
                expression_revision=lambda:conversation.expression_revision, background=Background())
            conversation.voice.client = SimpleNamespace(thread_id='fixture', model='offline', _rpc=RPC())
            for event in [self.started('old'), self.call(1, 'start_background_task', {'question':'Slow dispatch'}), None]:
                notifications.put(event)
            task = asyncio.create_task(conversation.voice.events())
            await asyncio.wait_for(entered.wait(), 1)
            try:
                await asyncio.wait_for(conversation.handle({'type':'stop_robot'}), 1)
                self.assertTrue(conversation.runtime.estop)
                self.assertFalse(task.done(), 'The stop must work before slow dispatch returns')
            finally:
                release.set()
                await asyncio.wait_for(task, 1)
                await conversation.mask.close()
                await conversation.brain.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
