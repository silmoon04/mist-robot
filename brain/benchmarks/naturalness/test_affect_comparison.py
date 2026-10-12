"""Offline contracts for the bounded affect comparison runner."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'brain'))
sys.path.insert(0, str(ROOT / 'brain' / 'harness'))
from benchmarks.naturalness import affect_comparison as bench


class FakeSpeaker:
    reader_constructed = threading.Event()
    speaker_call_seen = threading.Event()
    error_result = False
    expect_reader = False

    def __init__(self, **kwargs):
        self.run_dir = Path(kwargs['run_dir'])
        self.messages = []
        self._specs = []
        self._selected = set()
        self._bridge = None

    def new_session(self):
        self.messages = []

    def ask(self, prompt, timeout=45, on_event=None):
        if FakeSpeaker.expect_reader and not FakeSpeaker.reader_constructed.is_set():
            raise AssertionError('Reader must start before the speaker request')
        FakeSpeaker.speaker_call_seen.set()
        raw_path = self.run_dir.parent / 'raw.json'
        if not raw_path.exists():
            raise AssertionError('Per-run raw record must be created before model output')
        on_event({'type': 'message_update', 'assistantMessageEvent': {'type': 'text_delta', 'delta': '  '}})
        on_event({'type': 'message_update', 'assistantMessageEvent': {'type': 'text_delta', 'delta': 'That sounds rough. I can stay with you.'}})
        raw = json.loads(raw_path.read_text(encoding='utf-8'))
        if 'That sounds rough.' not in ''.join(raw['speaker_deltas']):
            raise AssertionError('Streamed text must be persisted before speaker aggregation')
        errors = ['fake-provider-failure'] if FakeSpeaker.error_result else []
        return SimpleNamespace(text='That sounds rough. I can stay with you.', errors=errors,
                               tool_calls=[], timings={'http_requests': []}, input_tokens=5,
                               output_tokens=7, total_s=0.2, ttft_s=0.1)

    def close(self):
        return None


class FakeReader:
    snapshots = []

    def __init__(self, **kwargs):
        FakeSpeaker.reader_constructed.set()
        self.kwargs = kwargs

    def decide_with_trace(self, snapshot):
        FakeReader.snapshots.append(snapshot)
        face = snapshot['current_face']
        decision = {'change': False, 'expression': face['expression'], 'variant': face['variant'],
                    'delivery': 'gentle', 'evidence': [{'record_id': 'current_user',
                                                        'quote': snapshot['current_user'][:30]}]}
        return decision, {'status': 'accepted', 'elapsed_ms': 1.0,
                          'model': self.kwargs['model'], 'reasoning_effort': self.kwargs['reasoning_effort']}


class AffectComparisonOfflineTests(unittest.TestCase):
    def setUp(self):
        FakeSpeaker.reader_constructed.clear()
        FakeSpeaker.speaker_call_seen.clear()
        FakeSpeaker.error_result = False
        FakeSpeaker.expect_reader = False
        FakeReader.snapshots.clear()

    def case(self):
        context, current = bench.frozen_turn({
            'history': [{'role': 'user', 'text': 'I am glad you are here.'},
                        {'role': 'assistant', 'text': 'I can stay with you.'},
                        {'role': 'user', 'text': 'The stand collapsed. I feel low.'}],
            'speaker_phrase_for_alignment': 'NEVER SEND THIS CANNED PHRASE',
            'discriminates': ['NEVER SEND THESE CRITERIA'],
            'review_questions': ['NEVER SEND THIS RUBRIC']})
        return {'id': 'offline', 'context': context, 'current_user': current,
                'face_override': False}

    def test_all_three_arms_take_real_return_path_and_save_raw_incrementally(self):
        with tempfile.TemporaryDirectory(prefix='affect-comparison-', dir=ROOT) as temp:
            case = self.case()
            for arm, model, effort in (
                ('qwen_single_speaker', None, None),
                ('qwen_director_qwen_speaker', 'qwen-3.8-27b', 'none'),
                ('gpt_oss_director_qwen_speaker', 'gpt-oss-120b', 'low'),
            ):
                FakeSpeaker.reader_constructed.clear()
                FakeSpeaker.expect_reader = model is not None
                result = bench.call_speaker(case, arm, Path(temp), director_model=model,
                                            director_effort=effort, speaker_factory=FakeSpeaker,
                                            director_factory=FakeReader if model else None)
                self.assertEqual(result['speaker']['answer'], 'That sounds rough. I can stay with you.')
                raw = json.loads((ROOT / result['raw_path']).read_text(encoding='utf-8'))
                self.assertEqual(raw['status'], 'complete')
                self.assertEqual(raw['speaker_result']['text'], result['speaker']['answer'])
                self.assertNotIn('NEVER SEND', json.dumps(raw))
                self.assertTrue(FakeSpeaker.speaker_call_seen.is_set())
                if model:
                    self.assertEqual(raw['director_result']['trace']['model'], model)
                    self.assertEqual(FakeReader.snapshots[-1]['speaker_text'], '')
                    self.assertEqual(FakeReader.snapshots[-1]['current_user'], case['current_user'])
                else:
                    self.assertIsNone(raw['director_result'])

    def test_provider_errors_survive_raw_write(self):
        FakeSpeaker.error_result = True
        with tempfile.TemporaryDirectory(prefix='affect-comparison-error-', dir=ROOT) as temp:
            result = bench.call_speaker(self.case(), 'qwen_single_speaker', Path(temp),
                                        speaker_factory=FakeSpeaker)
            raw = json.loads((ROOT / result['raw_path']).read_text(encoding='utf-8'))
        self.assertEqual(raw['speaker_result']['errors'], ['fake-provider-failure'])
        self.assertEqual(result['speaker']['errors'], ['fake-provider-failure'])

    def test_reader_worker_is_started_before_first_speaker_text(self):
        with tempfile.TemporaryDirectory(prefix='affect-comparison-order-', dir=ROOT) as temp:
            result = bench.call_speaker(self.case(), 'qwen_director_qwen_speaker', Path(temp),
                                        director_model='qwen-3.8-27b', director_effort='none',
                                        speaker_factory=FakeSpeaker, director_factory=FakeReader)
        self.assertLess(result['director']['reader_started_ms'],
                        result['speaker']['first_nonblank_ms'])


if __name__ == '__main__':
    unittest.main()
