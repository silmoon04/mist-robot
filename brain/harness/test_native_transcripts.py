"""Replay captured native interruption ordering; no provider or hardware calls."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest

BRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN))
sys.path.insert(0, str(BRAIN/'harness'))
from duplex.runtime import RobotRuntime
from eval_luna_native import TextRecorder
from duplex.server import Conversation as ProductionConversation

TRACE = BRAIN/'results/luna_native_20260922_refined'
NATIVE = json.loads((TRACE/'native_events.json').read_text(encoding='utf-8'))
REPORT = json.loads((TRACE/'report.json').read_text(encoding='utf-8'))
RECORDED_TTS = json.loads((TRACE/'tts_recorder.json').read_text(encoding='utf-8'))
INTERRUPT_AT = REPORT['interruption_at_s']
STORY = next(e['turn'] for e in NATIVE if e['type'] == 'turn.done' and e['turn']['role'] == 'assistant' and 'toe-kick' in e['turn']['transcript'])
QUIET = next(e['turn'] for e in NATIVE if e['type'] == 'turn.done' and e['turn']['role'] == 'assistant' and 'quiet until' in e['turn']['transcript'])


def conversation_class():
    candidate = os.environ.get('MIST_TRANSCRIPT_CANDIDATE')
    if not candidate: return ProductionConversation
    # Keep production-relative import paths while testing an unapplied candidate.
    module = types.ModuleType('mist_transcript_candidate')
    module.__file__ = str(BRAIN/'duplex/server.py')
    exec(compile(Path(candidate).read_text(encoding='utf-8'), module.__file__, 'exec'), module.__dict__)
    return module.Conversation


class Socket:
    closed = False
    def __init__(self): self.events = []; self.at = 0
    async def send_json(self, event): self.events.append({**event, 'trace_at': self.at})


class Voice:
    async def interrupt(self): pass


class TranscriptRegression(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.socket = Socket()
        self.conversation = conversation_class()({'runtime': RobotRuntime(self.directory.name), 'speech_backend':'streaming-tts'}, self.socket)
        self.conversation.mask = TextRecorder('', self.conversation.emit)
        self.conversation.voice = Voice()

    async def asyncTearDown(self):
        await self.conversation.brain.close()
        self.directory.cleanup()

    async def replay(self):
        ordered = [(e['t_s'], e) for e in NATIVE]
        ordered.append((INTERRUPT_AT, None))
        for at, event in sorted(ordered, key=lambda pair:pair[0]):
            self.socket.at = at
            if event is None: await self.conversation.barge_in('explicit_stop')
            else: await self.conversation.realtime_event(event)

    def assistant(self, kind):
        return [e for e in self.socket.events if e['type'] == kind and e.get('role') == 'assistant']

    async def test_captured_interruption_suppresses_old_visible_fragments(self):
        await self.replay()
        quiet_user_start = next(e['t_s'] for e in NATIVE if e['type'] == 'turn.created' and e['turn']['role'] == 'user' and e['t_s'] > INTERRUPT_AT)
        stale = [e for e in self.assistant('transcript_delta') if INTERRUPT_AT < e['trace_at'] < quiet_user_start]
        self.assertEqual(stale, [], 'Old interrupted story must not continue on screen')

    async def test_captured_interrupted_completion_is_not_visible(self):
        await self.replay()
        self.assertFalse(any(e['text'] == STORY['transcript'] for e in self.assistant('transcript_done')))

    async def test_new_reply_keeps_authoritative_opening_words_once(self):
        await self.replay()
        created = next(e['t_s'] for e in NATIVE if e['type'] == 'turn.created' and e['turn']['id'] == QUIET['id'])
        done = next(e['t_s'] for e in NATIVE if e['type'] == 'turn.done' and e['turn']['id'] == QUIET['id'])
        text = ''.join(e['text'] for e in self.assistant('transcript_delta') if created <= e['trace_at'] <= done)
        self.assertEqual(text, QUIET['transcript'])

    async def test_all_accepted_captured_replies_reconstruct_exactly(self):
        await self.replay()
        for item in NATIVE:
            if item['type'] != 'turn.done' or item['turn']['role'] != 'assistant' or item['turn']['id'] == STORY['id']: continue
            turn = item['turn']
            created = next(e['t_s'] for e in NATIVE if e['type'] == 'turn.created' and e['turn']['id'] == turn['id'])
            text = ''.join(e['text'] for e in self.assistant('transcript_delta') if created <= e['trace_at'] <= item['t_s'])
            with self.subTest(turn=turn['id']): self.assertEqual(text, turn['transcript'])

    async def test_predictive_tts_order_and_content_are_unchanged(self):
        await self.replay()
        def signature(values):
            return [{k:v for k,v in event.items() if k != 'at'} for event in values if event['name'].startswith('tts_')]
        self.assertEqual(signature(self.conversation.mask.events), signature(RECORDED_TTS))

    async def test_user_transcripts_stay_unchanged(self):
        await self.replay()
        expected = [e['item']['text'] for e in NATIVE if e['type'] == 'input_transcript.added']
        actual = [e['text'] for e in self.socket.events if e['type'] == 'transcript_delta' and e.get('role') == 'user']
        self.assertEqual(actual, expected)

    async def test_turn_stream_without_predictive_copy_keeps_first_words(self):
        for event in [
            {'type':'turn.created','turn':{'role':'assistant','id':'new','start_ms':100,'transcript':'Hello'}},
            {'type':'turn.delta','turn_id':'new','delta':' there'},
            {'type':'turn.done','turn':{'role':'assistant','id':'new','transcript':'Hello there'}},
        ]: await self.conversation.realtime_event(event)
        self.assertEqual(''.join(e['text'] for e in self.assistant('transcript_delta')), 'Hello there')

    async def test_old_completion_cannot_finish_new_tts(self):
        await self.conversation.realtime_event({'type':'turn.created','turn':{'role':'assistant','id':'new','transcript':'New reply','start_ms':300}})
        before = list(self.conversation.mask.events)
        await self.conversation.realtime_event({'type':'turn.done','turn':{'role':'assistant','id':'old','transcript':'Old reply','start_ms':100}})
        self.assertEqual(self.conversation.mask.events, before)
        self.assertFalse(self.conversation.assistant_done)
        self.assertEqual(self.assistant('transcript_done'), [])

    async def test_predictive_words_prewarm_tts_without_unattributed_ui(self):
        await self.conversation.realtime_event({'type':'output_transcript.added','start_ms':100,'item':{'text':'Hello'}})
        self.assertEqual(self.assistant('transcript_delta'), [])
        self.assertEqual([e['text'] for e in self.conversation.mask.events if e['name'] == 'tts_text'], ['Hello'])
        self.assertTrue(any(e['name'] == 'tts_begin' and not e['audible'] for e in self.conversation.mask.events))

    async def test_late_tagged_old_delta_does_not_join_new_reply(self):
        await self.conversation.realtime_event({'type':'turn.created','turn':{'role':'assistant','id':'new','transcript':'New','start_ms':300}})
        await self.conversation.realtime_event({'type':'turn.delta','turn_id':'old','delta':' OLD'})
        await self.conversation.realtime_event({'type':'turn.delta','turn_id':'new','delta':' reply'})
        self.assertEqual(''.join(e['text'] for e in self.assistant('transcript_delta')), 'New reply')


if __name__ == '__main__': unittest.main(verbosity=2)
