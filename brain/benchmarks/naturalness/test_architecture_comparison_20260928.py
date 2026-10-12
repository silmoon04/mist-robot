import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from brain.benchmarks.naturalness.architecture_comparison_20260928 import (
    check_assertions, make_schedule, summarize_turn, sample,
)
from brain.duplex.live_studio import ARCHITECTURES
from brain.harness.codex_client import CodexTurnResult


class ArchitectureComparisonTests(unittest.TestCase):
    def test_schedule_is_complete_paired_and_reproducible(self):
        cases = [{'id': 'one'}, {'id': 'two'}]
        arms = ['a', 'b', 'c']
        first = make_schedule(cases, arms, 2, 29)
        self.assertEqual(first, make_schedule(cases, arms, 2, 29))
        self.assertEqual(len(first), 12)
        for repeat in range(2):
            for case in cases:
                self.assertEqual({row['arm'] for row in first if row['repeat'] == repeat
                                  and row['case_id'] == case['id']}, set(arms))

    def test_turn_keeps_tool_timing_and_incomplete_usage(self):
        events = [
            {'at_ms': 100, 'event': {'type': 'transcript_delta', 'role': 'assistant', 'text': 'Hi'}},
            {'at_ms': 110, 'event': {'type': 'debug_tool', 'phase': 'started', 'name': 'recall'}},
            {'at_ms': 130, 'event': {'type': 'debug_tool', 'phase': 'finished', 'name': 'recall',
                                     'success': True, 'result': {'status': 'ok'}}},
            {'at_ms': 200, 'event': {'type': 'transcript_done', 'role': 'assistant', 'text': 'Hi there'}},
            {'at_ms': 201, 'event': {'type': 'debug_model', 'phase': 'thinking_finished',
                                     'timings': {'http_requests': [
                                         {'round': 0, 'usage': {'prompt_tokens': 10,
                                          'completion_tokens': 5, 'completion_tokens_details': {'reasoning_tokens': 2}}},
                                         {'round': 1}]}}},
        ]
        turn = summarize_turn(events, 'Hello', 0)
        self.assertEqual(turn['first_nonempty_text_ms'], 100)
        self.assertEqual(turn['first_tool_start_ms'], 110)
        self.assertEqual(turn['first_completed_tool_ms'], 130)
        self.assertEqual(turn['usage']['reasoning_tokens'], 2)
        self.assertFalse(turn['usage_complete'])
        self.assertEqual(turn['usage']['rounds_missing_usage'], 1)

    def test_assertions_keep_unknown_separate_from_failure(self):
        case = {'assertions': [{'turn_index': 0, 'kind': 'tool_not_called', 'name': '*'},
                               {'turn_index': 0, 'kind': 'text_contains', 'any_of': ['hello']},
                               {'turn_index': 0, 'kind': 'human_judgement'}]}
        outcome = check_assertions(case, [{'text': 'Hello.', 'tool_calls': []}])
        self.assertEqual([row['pass'] for row in outcome], [True, True, None])


class TrialPathTests(unittest.IsolatedAsyncioTestCase):
    async def test_typed_turn_through_trial_conversation_without_audio(self):
        class Client:
            def ask(self, prompt, timeout, on_event):
                result = CodexTurnResult(prompt=prompt)
                result.text = 'Hello there.'
                result.timings = {'http_requests': [{'round': 0, 'usage': {
                    'prompt_tokens': 20, 'completion_tokens': 3}}]}
                result.input_tokens = 20
                result.output_tokens = 3
                result.total_s = .01
                on_event({'type': 'message_update', 'assistantMessageEvent': {
                    'type': 'text_delta', 'delta': result.text}})
                return result
            def close(self): pass
        architecture = next(a for a in ARCHITECTURES if a['id'] == 'qwen-low')
        case = {'id': 'smoke', 'turns': [{'user': 'Hello'}], 'assertions': []}
        with tempfile.TemporaryDirectory() as directory:
            with patch('benchmarks.naturalness.cascade_voice.CascadeVoice.make_client',
                       return_value=Client()):
                outcome = await sample('smoke', architecture, case, Path(directory))
        self.assertEqual(outcome['status'], 'complete')
        self.assertEqual(outcome['turns'][0]['text'], 'Hello there.')
        self.assertEqual(outcome['turns'][0]['usage']['input_tokens'], 20)


if __name__ == '__main__': unittest.main()
