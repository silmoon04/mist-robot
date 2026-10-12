"""Offline CascadeVoice integration tests for captions and listening cues."""
import asyncio
import base64
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'benchmarks' / 'naturalness'))

from test_cascade_voice import FakeClient, FakeMask, FakeSocket, recognition, result
from cascade_voice import CascadeVoice
from duplex.listener_feedback import ListenerFeedback
from duplex.listener_backchannels import BackchannelDecision
from duplex.runtime import RobotRuntime
from duplex.server import Conversation


OPEN_CLAUSE = 'I have been thinking about what you said earlier, because'
FIRST_SEGMENT = 'I have been thinking about what you said earlier'
SECOND_SEGMENT = 'and it is still on my mind, because'
MERGED_FINAL = FIRST_SEGMENT + ' ' + SECOND_SEGMENT


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def prebuilt_clip(_cue):
    return {
        'text': 'Mhm.',
        'pcm': 'offline-prebuilt-pcm',
        'sample_rate': 24000,
        'duration_s': .42,
        'mouth_cues': [{'time': 0, 'viseme': 'MBP', 'amount': .25}],
    }


class ListenerIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.runtime = RobotRuntime(Path(self.folder.name))
        self.socket = FakeSocket()
        self.conversation = Conversation({'runtime': self.runtime, 'speech_backend': 'streaming-tts'}, self.socket)
        self.conversation.mask = FakeMask()
        with patch.dict('os.environ', {
            'MIST_LAB_PROVIDER': 'cerebras',
            'MIST_LAB_MODEL': 'gpt-oss-120b',
            'MIST_LAB_FLOOR': 'selective',
        }):
            self.voice = CascadeVoice(
                self.runtime, self.folder.name, self.conversation.emit, None,
                self.conversation.realtime_event,
                expression_revision=lambda: self.conversation.expression_revision,
            )
        self.conversation.voice = self.voice
        self.voice.client = FakeClient()
        self.voice.loop = asyncio.get_running_loop()
        self.clock = FakeClock(100.0)
        self.voice.listener.clock = self.clock
        self.voice.listener.lookup = prebuilt_clip
        self.assertIsInstance(self.voice.listener, ListenerFeedback)

    async def asyncTearDown(self):
        await self.voice.close()
        await self.conversation.brain.close()

    async def wait_for(self, predicate, message='Timed out waiting for listener event'):
        for _ in range(200):
            if predicate():
                return
            await asyncio.sleep(.005)
        self.fail(message)

    def events(self, kind):
        return [event for event in self.socket.events if event.get('type') == kind]

    async def start_floor(self):
        await self.voice.stt_event({'type': 'SpeechStarted', 'timestamp': self.clock.now})

    async def partial(self, text, *, start=0.0):
        await self.voice.stt_event(recognition(text, start=start, final=False, endpoint=False))

    async def test_partials_replace_merge_and_commit_once_without_early_model_history(self):
        self.voice.task(self.voice.model_worker())
        await self.start_floor()
        await self.partial('I have been thinking about what you')
        first = self.events('user_transcript')[-1]
        self.assertEqual(first['text'], 'I have been thinking about what you')
        self.assertFalse(first['final'])

        await self.partial('I have been thinking about what you said')
        revised = self.events('user_transcript')[-1]
        self.assertEqual(revised['text'], 'I have been thinking about what you said')
        self.assertGreater(revised['revision'], first['revision'])

        await self.voice.stt_event(recognition(FIRST_SEGMENT, start=0, final=True, endpoint=False))
        await self.partial('and it is still on my mind', start=1.2)
        await self.partial(SECOND_SEGMENT + ' perhaps', start=1.2)
        merged = self.events('user_transcript')[-1]
        self.assertEqual(merged['text'], FIRST_SEGMENT + ' ' + SECOND_SEGMENT + ' perhaps')
        self.assertEqual(merged['text'].count('perhaps'), 1)
        self.assertFalse(merged['final'])
        self.assertEqual(self.voice.client.prompts, [])
        self.assertEqual(self.voice.history, [])
        self.assertTrue(self.voice.requests.empty())

        await self.voice.stt_event(recognition(SECOND_SEGMENT, start=1.2, final=True, endpoint=True))
        await self.voice.endpoint('duplicate_endpoint')
        await self.wait_for(lambda: any(e.get('phase') == 'thinking_finished' for e in self.events('debug_model')))

        finals = [e for e in self.events('user_transcript') if e['final']]
        self.assertEqual(len(finals), 1)
        self.assertEqual(finals[0]['text'], MERGED_FINAL)
        self.assertEqual(len([e for e in self.events('transcript_done') if e.get('role') == 'user']), 1)
        self.assertEqual(self.voice.client.prompts, [MERGED_FINAL])
        self.assertEqual([entry['text'] for entry in self.voice.history if entry['role'] == 'user'], [MERGED_FINAL])

    async def test_sustained_open_partial_emits_one_quiet_positive_cue_without_model_turn(self):
        await self.start_floor()
        self.clock.advance(4.6)
        await self.partial(OPEN_CLAUSE)
        revision_before_cue = self.voice.revision
        epoch_before_cue = self.conversation.mask.epoch
        expression_revision_before_cue = self.conversation.expression_revision
        self.clock.advance(.45)
        await self.wait_for(lambda: len(self.events('listener_cue')) == 1)

        cue = self.events('listener_cue')[0]
        self.assertEqual(cue['text'], 'Mhm.')
        self.assertEqual(cue['reason'], 'sustained_floor_at_natural_pause')
        self.assertEqual(cue['transcript_revision'], self.events('user_transcript')[-1]['revision'])
        self.assertFalse(cue['final']) if 'final' in cue else None
        self.assertEqual(self.voice.client.prompts, [])
        self.assertEqual(self.voice.history, [])
        self.assertTrue(self.voice.requests.empty())
        self.assertEqual(self.conversation.mask.epoch, epoch_before_cue)
        self.assertEqual(self.voice.revision, revision_before_cue)
        self.assertEqual(self.conversation.expression_revision, expression_revision_before_cue)
        self.assertEqual(cue['epoch'], epoch_before_cue)
        self.assertEqual(self.conversation.mask.begins, [])
        self.assertEqual(self.conversation.mask.texts, [])
        self.assertEqual(self.conversation.mask.finished, [])
        self.assertIsNone(self.voice.turn)

    async def test_lookup_uses_the_policy_selected_cue(self):
        await self.start_floor()
        self.clock.advance(4.6)
        await self.partial(OPEN_CLAUSE)
        decision = BackchannelDecision(True, 'uh_huh', 'test_selected_cue', 'test',
                                       self.voice.listener.floor_id, self.clock.now,
                                       self.clock.now + .35, OPEN_CLAUSE.casefold())
        looked_up = []
        self.voice.listener.lookup = lambda cue: looked_up.append(cue) or {
            'text': 'Uh-huh.', 'pcm': 'offline-uh-huh-pcm', 'sample_rate': 24000,
            'duration_s': .31, 'mouth_cues': [],
        }
        with patch.object(self.voice.listener.policy, 'evaluate', return_value=decision):
            self.assertTrue(await self.voice.listener.try_cue())

        self.assertEqual(looked_up, ['uh_huh'])
        self.assertEqual(self.events('listener_cue')[-1]['text'], 'Uh-huh.')
        self.assertEqual(self.events('listener_cue')[-1]['reason'], 'test_selected_cue')

    async def test_floor_quiet_phrases_reset_per_floor_while_practice_persists(self):
        for phrase in ('Let me finish this long complicated explanation, because',
                       'Let me talk through this long complicated explanation, because',
                       'Let me speak about this long complicated explanation, because'):
            await self.start_floor()
            self.clock.advance(5.1)
            await self.partial(phrase)
            self.assertTrue(self.voice.listener.floor_quiet, phrase)
            self.assertFalse(self.voice.listener.practice, phrase)
            self.assertFalse(await self.voice.listener.try_cue(), phrase)
            self.assertEqual(self.events('listener_feedback')[-1]['reason'], 'user_requested_quiet')

            await self.voice.listener.finish(phrase)
            await self.start_floor()
            self.assertFalse(self.voice.listener.floor_quiet, 'a completed floor must not leave quiet latched')

        # A real speaking-practice request is a session preference and survives
        # the floor boundary, unlike a one-floor "let me ..." request.
        self.clock.advance(5.1)
        practice_text = 'I want speaking practice for this long complicated explanation, because'
        await self.partial(practice_text)
        self.assertTrue(self.voice.listener.practice)
        await self.voice.listener.finish(practice_text)
        await self.start_floor()
        self.assertFalse(self.voice.listener.floor_quiet)
        self.assertTrue(self.voice.listener.practice)

        self.clock.advance(5.1)
        continued_practice = 'I am still presenting this long complicated explanation, because'
        await self.partial(continued_practice)
        self.clock.advance(.45)
        self.assertFalse(await self.voice.listener.try_cue())
        self.assertEqual(self.events('listener_feedback')[-1]['reason'], 'user_requested_quiet')
        self.assertTrue(self.voice.listener.practice)

        end_practice = 'Let us finish the practice and return to normal chatting, because'
        await self.partial(end_practice)
        self.assertFalse(self.voice.listener.practice)
        self.assertFalse(self.voice.listener.floor_quiet)

    async def test_speech_started_does_not_publish_an_empty_caption(self):
        await self.start_floor()
        self.assertEqual(self.events('user_transcript'), [])
        self.assertEqual(self.events('transcript_delta'), [])
        self.assertEqual(self.events('transcript_done'), [])

        await self.partial('A real caption has arrived')
        self.assertEqual([event['text'] for event in self.events('user_transcript')],
                         ['A real caption has arrived'])

    async def test_user_resumption_before_playback_cancels_the_candidate(self):
        await self.start_floor()
        self.clock.advance(4.6)
        await self.partial(OPEN_CLAUSE)
        self.clock.advance(.45)
        await self.wait_for(lambda: len(self.events('listener_cue')) == 1)
        cue_id = self.events('listener_cue')[0]['cue_id']

        await self.voice.stt_event({'type': 'SpeechStarted', 'timestamp': self.clock.now})
        cancellations = self.events('listener_cue_cancel')
        self.assertEqual(len(cancellations), 1)
        self.assertEqual(cancellations[0]['cue_id'], cue_id)
        self.assertEqual(cancellations[0]['reason'], 'speech_resumed')
        self.assertIsNone(self.voice.listener.pending)
        self.assertEqual(self.events('listener_cue_state'), [])

    async def test_started_cue_finishes_during_same_floor_continuation(self):
        await self.start_floor()
        self.clock.advance(4.6)
        await self.partial(OPEN_CLAUSE)
        self.clock.advance(.45)
        await self.wait_for(lambda: len(self.events('listener_cue')) == 1)
        cue_id = self.events('listener_cue')[0]['cue_id']
        await self.voice.listener.receipt({'cue_id': cue_id, 'phase': 'started'})

        await self.voice.stt_event({'type': 'SpeechStarted', 'timestamp': self.clock.now})
        await self.partial(OPEN_CLAUSE + ' I think')
        self.assertEqual(self.events('listener_cue_cancel'), [])
        self.assertEqual(self.voice.listener.pending_id, cue_id)
        self.assertEqual(self.voice.listener.floor_id, self.events('listener_cue')[0]['utterance_id'])

        await self.voice.listener.receipt({'cue_id': cue_id, 'phase': 'ended'})
        self.assertIsNone(self.voice.listener.pending_id)
        receipts = [e for e in self.events('listener_feedback') if e.get('phase') == 'ended']
        self.assertEqual(len(receipts), 1)

    async def test_finalized_full_stop_never_gets_a_cue(self):
        await self.start_floor()
        self.clock.advance(4.6)
        await self.partial('I have been thinking about what you said earlier and it is still on my mind.')
        await self.voice.listener.finish('I have been thinking about what you said earlier and it is still on my mind.')
        self.clock.advance(.5)
        self.assertFalse(await self.voice.listener.try_cue())
        self.assertEqual(self.events('listener_cue'), [])
        self.assertTrue(self.events('user_transcript')[-1]['final'])

    async def test_question_partial_does_not_get_a_cue(self):
        utterance = 'I have been thinking about what you said earlier, because what do you think?'
        await self.start_floor()
        self.clock.advance(4.6)
        await self.partial(utterance)
        self.clock.advance(.45)
        self.assertFalse(await self.voice.listener.try_cue())
        self.assertEqual(self.events('listener_cue'), [])

    async def test_explicit_quiet_request_does_not_get_a_cue(self):
        utterance = 'Please stay quiet while I finish explaining this long complicated idea, because'
        await self.start_floor()
        self.clock.advance(4.6)
        await self.partial(utterance)
        self.clock.advance(.45)
        self.assertFalse(await self.voice.listener.try_cue())
        self.assertEqual(self.events('listener_cue'), [])

    async def test_disable_config_cancels_feedback_but_mic_packets_remain_accepted(self):
        await self.start_floor()
        self.clock.advance(4.6)
        await self.partial(OPEN_CLAUSE)
        self.clock.advance(.45)
        await self.wait_for(lambda: len(self.events('listener_cue')) == 1)
        cue_id = self.events('listener_cue')[0]['cue_id']

        await self.conversation.handle({'type': 'listener_ack_config', 'enabled': False})
        self.assertFalse(self.voice.listener.enabled)
        cancellation = self.events('listener_cue_cancel')[-1]
        self.assertEqual(cancellation['cue_id'], cue_id)
        self.assertEqual(cancellation['reason'], 'disabled')

        pcm = b'\0\0' * 320
        before = self.voice.track.queue.qsize()
        await self.conversation.handle({'type': 'mic', 'pcm': base64.b64encode(pcm).decode('ascii')})
        self.assertEqual(self.voice.track.queue.qsize(), before + 1)
        self.clock.advance(.5)
        self.assertFalse(await self.voice.listener.try_cue())
        self.assertEqual(len(self.events('listener_cue')), 1)


if __name__ == '__main__':
    unittest.main()
