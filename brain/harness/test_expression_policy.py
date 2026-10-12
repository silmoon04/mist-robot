"""Tool-boundary contracts for expression requests. No model or voice-provider calls."""
import json
import sys
import tempfile
import unittest
import queue
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from duplex.expression_policy import FACE_MAP, normalize_expression, expression_parameters
from duplex.runtime import RobotRuntime, specs


class ExpressionContractTests(unittest.TestCase):
    def test_default_is_persistent_but_requested_flash_is_timed(self):
        self.assertTrue(normalize_expression({'expression':'sad'})['persistent'])
        self.assertFalse(normalize_expression({'expression':'sad','duration_ms':900})['persistent'])

    def test_all_forty_faces_have_valid_calls(self):
        covered = set()
        for name, preset in FACE_MAP['expressions'].items():
            for variant, face_id in enumerate([preset['primary'], *preset['alts']]):
                value = normalize_expression({'expression': name, 'variant': variant})
                self.assertEqual(value['face_id'], face_id)
                covered.add(face_id)
        self.assertEqual(covered, set(FACE_MAP['faces']))
        self.assertEqual(len(covered), 40)

    def test_invalid_commands_are_rejected(self):
        commands = [None, [], {}, 'happy', {'expression': '__proto__'}, {'expression': 0}]
        for field, values in [('variant', [-1, 99, .5, True, None, '1']),
                              ('duration_ms', [float('nan'), float('inf'), True, None, '1200', 1.2])]:
            commands += [{'expression': 'happy', field: value} for value in values]
        commands += [{'expression': 'happy', 'face_id': 'forged'}, {'expression': 'happy', 'command': 'move'}]
        for command in commands:
            with self.subTest(command=command), self.assertRaises(ValueError):
                normalize_expression(command)

    def test_duration_is_bounded(self):
        self.assertEqual(normalize_expression({'expression': 'happy', 'duration_ms': -1})['duration_ms'], 400)
        self.assertEqual(normalize_expression({'expression': 'happy', 'duration_ms': 10**20})['duration_ms'], 6000)
        self.assertEqual(normalize_expression({'expression': 'happy', 'duration_ms': 1600})['duration_ms'], 1600)

    def test_runtime_returns_the_validated_variant_and_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = RobotRuntime(directory)
            result = runtime.call('set_expression', {'expression': 'happy', 'variant': 1, 'duration_ms': 1700})
            self.assertEqual(result, {'status': 'display_requested', 'expression': 'happy', 'variant': 1,
                                     'duration_ms': 1700, 'persistent': False, 'face_id': FACE_MAP['expressions']['happy']['alts'][0]})

    def test_schema_stays_small_and_preserves_the_minimal_call(self):
        spec = next(item for item in specs() if item['name'] == 'set_expression')
        self.assertEqual(spec['inputSchema']['required'], ['expression'])
        self.assertFalse(spec['inputSchema']['additionalProperties'])
        self.assertEqual(set(expression_parameters()), {'expression', 'variant', 'duration_ms'})
        self.assertIn('uncertain', expression_parameters()['expression']['enum'])
        self.assertEqual(len(specs()), 7)


class ExpressionIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setup_conversation(self, directory):
        from duplex.server import Conversation
        from duplex.conversion import VoiceMask
        events=[]
        class Socket:
            closed=False
            async def send_json(self,event):events.append(event)
        conversation=Conversation({'runtime':RobotRuntime(directory)},Socket())
        conversation.mask=VoiceMask('not-a-real-key',conversation.emit)
        return conversation,events

    async def test_refused_or_old_receipts_do_not_change_the_face(self):
        with tempfile.TemporaryDirectory() as directory:
            conversation,events=self.setup_conversation(directory)
            await conversation.emit({'type':'tool','name':'set_expression','result':{'status':'refused'},'expression_revision':0})
            conversation.expression_revision=1
            await conversation.emit({'type':'tool','name':'set_expression',
                                     'result':{'status':'display_requested','expression':'happy'},'expression_revision':0})
            self.assertFalse(any(event['type']=='face' for event in events))

    async def test_manual_variant_and_duration_reach_browser_without_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            conversation,events=self.setup_conversation(directory)
            await conversation.handle({'type':'expression','expression':'happy','variant':1,'duration_ms':1750})
            self.assertEqual(events[-1],{'type':'face','expression':'happy','variant':1,'duration_ms':1750,
                                         'persistent':False,'epoch':0,'expression_revision':0,'source':'manual'})
            with self.assertRaises(ValueError):
                await conversation.handle({'type':'expression','expression':'bad','variant':1000})
            self.assertEqual(len(events),1)

    async def test_barge_in_during_tool_dispatch_cannot_restore_old_face(self):
        from duplex.native import NativeVoice
        with tempfile.TemporaryDirectory() as directory:
            conversation,events=self.setup_conversation(directory)
            replies=[]
            notifications=queue.Queue()
            class RPC:
                def __init__(self):self.events=notifications
                def send(self,event):replies.append(event)
                def request(self,*args,**kwargs):return {}
            async def emit(event):
                if event.get('type')=='debug_tool' and event.get('phase')=='started' and event.get('call_id')=='old-call':
                    await conversation.barge_in('test_interruption')
                await conversation.emit(event)
            async def nothing(*args):pass
            voice=NativeVoice(conversation.runtime,directory,emit,nothing,nothing,
                              expression_revision=lambda:conversation.expression_revision)
            voice.client=SimpleNamespace(thread_id='test-thread',model='offline-test',_rpc=RPC())
            conversation.voice=voice
            for event in [
                {'method':'turn/started','params':{'turn':{'id':'old'}}},
                {'id':1,'method':'item/tool/call','params':{'turnId':'old','callId':'old-call','tool':'set_expression','arguments':{'expression':'angry'}}},
                {'method':'turn/started','params':{'turn':{'id':'new'}}},
                {'id':2,'method':'item/tool/call','params':{'turnId':'new','callId':'new-call','tool':'set_expression','arguments':{'expression':'curious','variant':1,'duration_ms':1600}}},
                {'id':3,'method':'item/tool/call','params':{'turnId':'old','callId':'late-old-call','tool':'set_expression','arguments':{'expression':'panic'}}},
                None,
            ]:notifications.put(event)
            await voice.events()
            face_events=[event for event in events if event['type']=='face']
            self.assertEqual(len(face_events),1)
            self.assertEqual(face_events[0]['expression'],'curious')
            self.assertEqual(face_events[0]['variant'],1)
            self.assertEqual(face_events[0]['duration_ms'],1600)
            self.assertEqual(face_events[0]['epoch'],1)
            self.assertEqual(face_events[0]['expression_revision'],1)
            self.assertEqual([reply['result']['success'] for reply in replies],[False,True,False])


if __name__ == '__main__':
    unittest.main(verbosity=2)
