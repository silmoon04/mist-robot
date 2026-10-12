import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hard_worker_comparison_20260929 as bench
import hard_tasks_20260929 as tasks


class HardWorkerComparisonTests(unittest.TestCase):
    def test_plan_is_bounded_paired_and_deterministic(self):
        cases = tasks.suite()
        first = bench.plan(cases)
        self.assertEqual(first, bench.plan(cases))
        self.assertEqual(len(first), 48)
        self.assertEqual(len({(x['case_id'], x['arm_id'], x['repetition']) for x in first}), 48)
        self.assertEqual({x['order'] for x in first}, set(range(1, 49)))
        with self.assertRaises(ValueError):
            bench.plan(cases, repetitions=3)

    def test_bridge_scopes_records_and_keeps_every_submission(self):
        bridge = bench.FictionalBridge()
        bridge.set_turn({'one': {'number': 1}})
        ok = bridge.request('call', {'name': 'read_record', 'arguments': {'id': 'one'}})
        bad = bridge.request('call', {'name': 'read_record', 'arguments': {'id': 'two'}})
        self.assertFalse(ok['isError'])
        self.assertTrue(bad['isError'])
        bridge.request('call', {'name': 'submit_answer', 'arguments': {'answer': {'value': 1}}})
        bridge.request('call', {'name': 'submit_answer', 'arguments': {'answer': {'value': 2}}})
        self.assertEqual(bridge.reads, ['one'])
        self.assertEqual(bridge.submissions, [{'value': 1}, {'value': 2}])
        bridge.set_turn({'two': {'number': 2}})
        self.assertEqual(bridge.reads, [])
        self.assertEqual(bridge.submissions, [])
        self.assertTrue(bridge.request('call', {'name': 'read_record', 'arguments': {'id': 'one'}})['isError'])

    def test_final_submission_scored_and_failed_turn_not_replaced(self):
        case = tasks.suite()[-1]
        client = bench.OfflineClient(lambda i: {'votes_for': 99, 'votes_against': 0, 'venue': 'Secret Room'})
        row = bench.run_sample(case, bench.ARMS[0], 1, 1, client, tasks.evaluate)
        self.assertEqual(len(row['turns']), len(case['turns']))
        self.assertFalse(row['complete'])
        self.assertFalse(row['turns'][0]['verdict']['passed'])
        self.assertEqual(row['turns'][0]['submission_count'], 1)
        self.assertEqual(row['turns'][0]['reads'], ['meeting_minutes'])

    def test_malformed_submission_keeps_receipt_and_failed_verdict(self):
        case = next(case for case in tasks.suite() if case['family'] == 'conversation_state_compaction')
        client = bench.OfflineClient(lambda i: {'meeting_day': 'Thursday', 'do_not': [{}],
                                                 'unfinished': [], 'completed_receipts': []})
        row = bench.run_sample(case, bench.ARMS[0], 1, 1, client, tasks.evaluate)
        self.assertFalse(row['complete'])
        self.assertEqual(row['turns'][0]['submission_count'], 1)
        self.assertFalse(row['turns'][0]['accepted_correct_final'])
        self.assertTrue(row['turns'][0]['scored'])
        self.assertIn('valid_outcome', row['turns'][0]['verdict']['reasons'])

    def test_scorer_exception_is_unscored_and_keeps_tool_evidence(self):
        case = tasks.suite()[-1]
        client = bench.OfflineClient(lambda i: case['turns'][i]['_reference'])
        def broken_scorer(*args):
            raise RuntimeError('oracle bug')
        row = bench.run_sample(case, bench.ARMS[0], 1, 1, client, broken_scorer)
        self.assertFalse(row['complete'])
        self.assertFalse(row['turns'][0]['scored'])
        self.assertEqual(row['turns'][0]['score_error'], 'RuntimeError: oracle bug')
        self.assertEqual(row['turns'][0]['submission_count'], 1)

    def test_offline_freezes_plan_without_provider_calls_or_oracle_leak(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'plan'
            manifest, rows = bench.run(folder, live=False)
            self.assertEqual(rows, [])
            self.assertEqual(len(manifest['ordered_samples']), 48)
            self.assertEqual(manifest['suite_digest'], tasks.suite_digest())
            text = (folder / 'manifest.json').read_text(encoding='utf-8')
            self.assertNotIn('_reference', text)
            self.assertNotIn('"_reference"', text)
            with self.assertRaises(FileExistsError):
                bench.run(folder, live=False)

    def test_blind_packet_omits_model_cost_and_score(self):
        case = tasks.suite()[-1]
        client = bench.OfflineClient(lambda i: case['turns'][i]['_reference'])
        row = bench.run_sample(case, bench.ARMS[0], 1, 1, client, tasks.evaluate)
        packet, key = bench.blind_packet([row])
        self.assertTrue(row['complete'])
        self.assertEqual(len(key), 1)
        data = json.dumps(packet)
        for forbidden in ('qwen_none', 'cerebras', 'priority', 'verdict', 'total_s', 'input_tokens'):
            self.assertNotIn(forbidden, data)


if __name__ == '__main__':
    unittest.main()
