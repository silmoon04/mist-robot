import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tool_worker_comparison_20260928 as bench


class ToolWorkerComparisonTests(unittest.TestCase):
    def test_offline_runner_exercises_full_budget_and_persists_actual_token_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            records, info = bench.run_benchmark(Path(temp), live=False)
            self.assertEqual(len(records), 24)
            self.assertTrue(all(r['completed'] and r['tool_correct'] and r['answer_correct'] for r in records))
            self.assertTrue(all(r['cumulative_turn_input_tokens'] == 30 and r['cumulative_turn_output_tokens'] == 8 for r in records))
            self.assertEqual(len({r['order'] for r in records}), 24)
            self.assertTrue(any(r['scenario'] == 'long_context_read' for r in records))
            self.assertTrue(any(r['scenario'] == 'dependent_two_reads' for r in records))
            stored = json.loads((Path(temp) / 'results.json').read_text(encoding='utf-8'))
            self.assertEqual(len(stored['records']), 24)
            self.assertTrue(all(value['provider'] == 'offline_fake' for value in info.values()))
            with (Path(temp) / 'results.csv').open(encoding='utf-8', newline='') as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 24)

    def test_run_one_retains_model_errors_and_does_not_mark_output_completed(self):
        client = bench.FakeClient()
        client.ask = lambda *args, **kwargs: SimpleNamespace(total_s=1.2, text='provisional', errors=['provider timeout'], tool_calls=[])
        row = bench.run_one(client, bench.ARMS[0], bench.SCENARIOS[0], 1, True, 1)
        self.assertFalse(row['completed'])
        self.assertEqual(row['errors'], ['provider timeout'])
        self.assertIsNone(row['public_answer_s'])
        self.assertFalse(row['tool_correct'])

    def test_run_one_retains_raised_provider_error(self):
        client = bench.FakeClient()
        client.ask = lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError('fixture timeout'))
        row = bench.run_one(client, bench.ARMS[0], bench.SCENARIOS[0], 1, True, 1)
        self.assertFalse(row['completed'])
        self.assertEqual(row['errors'], ['TimeoutError: fixture timeout'])
        self.assertIsNone(row['public_answer_s'])

    def test_tool_evidence_requires_exact_arguments_and_receipt(self):
        scenario = bench.SCENARIOS[1]
        events = []
        for name, args in zip(scenario['tools'], scenario['arguments']):
            events.append({'phase': 'result', 'name': name, 'arguments': args,
                           'result': {'content': [{'text': json.dumps(bench.MOCK_RESULTS[name])}]},
                           'is_error': False})
        self.assertTrue(bench.tool_evidence_correct({'tool_events': events}, scenario))
        events[1]['arguments'] = {'part_name': 'invented'}
        self.assertFalse(bench.tool_evidence_correct({'tool_events': events}, scenario))

    def test_atomic_json_replaces_complete_document(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'state.json'
            path.write_text('{"old":true}', encoding='utf-8')
            bench.atomic_json(path, {'new': [1, 2, 3]})
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), {'new': [1, 2, 3]})
            self.assertEqual(sorted(p.name for p in Path(temp).iterdir()), ['state.json'])

    def test_request_budget_refuses_oversized_runs(self):
        arms = bench.ARMS[:3]
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'at most 24'):
                bench.run_benchmark(Path(temp), live=False, arms=arms, repetitions=3)

    def test_percentage_fact_check_accepts_unicode_spacing_without_leaking_rubric(self):
        self.assertTrue(bench.answer_fact_present('Battery is 73\u202f% and grounded.', '73%'))
        self.assertTrue(bench.answer_fact_present('Battery is 73 percent.', '73%'))
        self.assertFalse(bench.answer_fact_present('Battery is 37%.', '73%'))


if __name__ == '__main__':
    unittest.main()
