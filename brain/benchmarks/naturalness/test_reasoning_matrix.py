"""Offline matrix checks. Fake client responses are not reasoning evidence."""
import argparse
from collections import Counter
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reasoning_matrix as matrix
from reasoning_suite import write_suite


CONDITIONS = [
    {'id': 'oss-low', 'provider': 'cerebras', 'model': 'gpt-oss-120b', 'reasoning': 'low'},
    {'id': 'oss-high', 'provider': 'cerebras', 'model': 'gpt-oss-120b', 'reasoning': 'high'},
    {'id': 'qwen-none', 'provider': 'cerebras', 'model': 'qwen-3.8-27b', 'reasoning': 'none'},
    {'id': 'qwen-low', 'provider': 'cerebras', 'model': 'qwen-3.8-27b', 'reasoning': 'low'},
]


class MatrixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.suite = self.root / 'suite'
        write_suite(self.suite, 'dev', 2409)

    def args(self, **changes):
        values = dict(suite=self.suite, output=self.root / 'matrix', condition_values=CONDITIONS,
                      ids=None, families='referent_repair', limit=1, repeats=3, seed=2409,
                      timeout=45, max_output_tokens=4096, live=False)
        values.update(changes)
        return argparse.Namespace(**values)

    def run_matrix(self, args, factory=None):
        with contextlib.redirect_stdout(io.StringIO()):
            if factory is None:
                return matrix.run(args, client_factory=lambda *x: self.fail('Unexpected provider call'))
            return matrix.run(args, client_factory=factory)

    def test_schedule_complete_paired_reproducible_and_position_balanced(self):
        for count in (1, 9, 12, 21):
            cases = [{'id': f'case-{n}'} for n in range(count)]
            schedule = matrix.schedule_matrix(cases, CONDITIONS, 3, 2409)
            self.assertEqual(schedule, matrix.schedule_matrix(cases, CONDITIONS, 3, 2409))
            self.assertEqual(len(schedule), count * 3)
            observed = Counter((b['case_id'], b['repeat'], cid) for b in schedule for cid in b['order'])
            self.assertEqual(len(observed), count * 3 * 4)
            self.assertEqual(set(observed.values()), {1})
            positions = matrix.order_counts(schedule, CONDITIONS)
            for values in positions.values():
                self.assertLessEqual(max(values) - min(values), 1)
            for block in schedule:
                self.assertEqual(set(block['order']), {c['id'] for c in CONDITIONS})
        self.assertNotEqual(matrix.schedule_matrix(cases, CONDITIONS, 3, 1), matrix.schedule_matrix(cases, CONDITIONS, 3, 2))

    def test_condition_validation_blocks_per_condition_budget_and_unsafe_ids(self):
        self.assertEqual(matrix.validate_conditions({'conditions': CONDITIONS}), CONDITIONS)
        bad = copy.deepcopy(CONDITIONS); bad[0]['max_output_tokens'] = 999
        with self.assertRaises(ValueError): matrix.validate_conditions(bad)
        bad = copy.deepcopy(CONDITIONS); bad[1]['id'] = bad[0]['id']
        with self.assertRaises(ValueError): matrix.validate_conditions(bad)
        for invalid in ('../outside', '', 'x/y'):
            bad = copy.deepcopy(CONDITIONS); bad[0]['id'] = invalid
            with self.assertRaises(ValueError): matrix.validate_conditions(bad)
        bad = copy.deepcopy(CONDITIONS); bad[0]['provider'] = 'unknown'
        with self.assertRaises(ValueError): matrix.validate_conditions(bad)

    def test_dry_plan_no_api_and_all_inputs_configs_frozen(self):
        args = self.args()
        self.assertEqual(self.run_matrix(args), 0)
        run = json.loads((args.output / 'run.json').read_text())
        self.assertEqual(run['status'], 'planned')
        self.assertEqual(run['status_counts'], {'planned': 12})
        self.assertTrue(all(c['max_output_tokens'] == 4096 and c['new_session_per_sample']
                            for c in run['manifest']['effective_configs'].values()))
        self.assertEqual(len(run['manifest']['input_hashes']), 1)
        for relative, expected in run['manifest']['source_hashes'].items():
            self.assertEqual(matrix.evaluation.sha((args.output / 'sources' / relative).read_bytes()), expected)
        self.assertTrue((args.output / 'condition_key.private.json').is_file())
        with self.assertRaises(FileExistsError): self.run_matrix(args)

    def test_private_oracles_never_read_and_settings_same_across_fresh_clients(self):
        (self.suite / 'private_oracles.json').write_text('SECRET_ORACLE_NOT_JSON', encoding='utf-8')
        clients, prompts, configs = [], [], []
        class Fake:
            backend_info = {'provider': 'fake_offline'}
            def __init__(self): self.new = self.closed = self.asked = 0
            def new_session(self): self.new += 1
            def ask(self, prompt, timeout):
                self.asked += 1; prompts.append(prompt)
                return SimpleNamespace(text='Offline test answer', tool_calls=[], errors=[], ttft_s=.1,
                    total_s=.3, timings={}, input_tokens=10, output_tokens=3, cache_read_tokens=0)
            def close(self): self.closed += 1
        def factory(config, system, folder):
            configs.append(config); client = Fake(); clients.append(client); return client
        args = self.args(live=True, repeats=2)
        self.assertEqual(self.run_matrix(args, factory), 0)
        self.assertEqual(len(clients), 8)
        self.assertTrue(all((c.new, c.asked, c.closed) == (1, 1, 1) for c in clients))
        self.assertEqual(len(set(prompts)), 1)
        self.assertTrue(all(c['max_output_tokens'] == 4096 and c['timeout_s'] == 45 for c in configs))
        self.assertFalse(any('SECRET_ORACLE' in p or 'meaning_review' in p for p in prompts))
        summary = json.loads((args.output / 'latency-summary.json').read_text())
        self.assertEqual({s['ttft']['count'] for s in summary['conditions'].values()}, {2})
        self.assertEqual({s['semantic_pass'] for s in summary['conditions'].values()}, {None})

    def test_errors_retained_once_without_retry_and_other_conditions_continue(self):
        created, asked = [], []
        class Fake:
            backend_info = {'provider': 'fake_offline'}
            def __init__(self, config): self.config = config
            def new_session(self): pass
            def close(self): pass
            def ask(self, prompt, timeout):
                asked.append(self.config['reasoning'])
                if self.config['reasoning'] == 'high': raise RuntimeError('Offline simulated failure')
                return SimpleNamespace(text='Fake complete', tool_calls=[], errors=[], ttft_s=.2,
                    total_s=.4, timings={}, input_tokens=1, output_tokens=1, cache_read_tokens=0)
        def factory(config, *args): created.append(config); return Fake(config)
        args = self.args(live=True, repeats=3)
        self.assertEqual(self.run_matrix(args, factory), 1)
        self.assertEqual(len(created), 12); self.assertEqual(len(asked), 12)
        run = json.loads((args.output / 'run.json').read_text())
        self.assertEqual(run['status_counts'], {'completed': 9, 'failed': 3})
        self.assertEqual(sum('Offline simulated failure' in str(s['errors']) for s in run['samples']), 3)
        summary = matrix.latency_summary(run)
        self.assertEqual(summary['conditions']['oss-high']['ttft']['count'], 0)
        self.assertEqual(summary['conditions']['oss-high']['error_samples'], 3)

    def test_latency_excludes_failed_and_invalid_values_and_does_not_grade_semantics(self):
        condition = CONDITIONS[0]
        def row(status, ttft, total, errors=None, tools=None):
            return dict(condition_id=condition['id'], status=status, ttft_s=ttft, total_s=total,
                        errors=errors or [], tools=tools or [])
        rows = [row('completed', 1, 2), row('completed', 2, 4), row('failed', .001, .01, ['failed']),
                row('unsupported', .1, .2), row('completed', None, 6), row('completed', float('nan'), -1),
                row('completed', 5, 1), row('completed', .2, .4, tools=[{'name': 'unexpected'}])]
        summary = matrix.latency_summary({'manifest': {'conditions': [condition]}, 'samples': rows})['conditions'][condition['id']]
        self.assertEqual(summary['ttft'], {'count': 2, 'median_s': 1.5, 'p90_s': 1.9})
        self.assertEqual(summary['total']['count'], 3)
        self.assertEqual(summary['total']['median_s'], 4)
        self.assertEqual(summary['error_samples'], 1)
        self.assertEqual(summary['unexpected_tool_samples'], 1)
        self.assertEqual(summary['invalid_timing_order_samples'], 1)
        self.assertIsNone(summary['semantic_pass'])

    def test_blind_review_has_context_and_answers_but_no_settings_times_or_errors(self):
        args = self.args(repeats=1)
        self.run_matrix(args)
        record = json.loads((args.output / 'run.json').read_text())
        for row in record['samples']:
            row.update(text='<script>bad()</script> Full response.', status='completed', ttft_s=12345,
                       total_s=54321, errors=['PRIVATE_PROVIDER_ERROR'], backend={'model': 'PRIVATE_MODEL'})
        matrix.blind_review(record, args.output, 99)
        page = (args.output / 'review.html').read_text(encoding='utf-8')
        blind = json.loads((args.output / 'review_inputs.blind.json').read_text(encoding='utf-8'))
        encoded = json.dumps(blind)
        for forbidden in ['oss-low', 'oss-high', 'qwen-none', 'qwen-low', 'PRIVATE_PROVIDER_ERROR',
                          'PRIVATE_MODEL', 'ttft_s', 'total_s', '12345', '54321']:
            self.assertNotIn(forbidden, page)
            self.assertNotIn(forbidden, encoded)
        self.assertIn('&lt;script&gt;bad()', page)
        self.assertIn('dialogue', encoded); self.assertIn('Full response.', encoded)
        key = json.loads((args.output / 'condition_key.private.json').read_text())
        answers = next(iter(key['comparisons'].values()))['answers']
        self.assertEqual({r['condition_id'] for r in answers.values()}, {c['id'] for c in CONDITIONS})

    def test_tool_cases_are_unsupported_and_no_api_is_created(self):
        args = self.args(live=True, families='action_receipts', repeats=1, limit=None)
        self.assertEqual(self.run_matrix(args), 0)
        run = json.loads((args.output / 'run.json').read_text())
        self.assertEqual(run['status_counts'], {'unsupported': 12})
        self.assertTrue(all(s['execution']['tool_contract'] == 'unmeasured' for s in run['samples']))

    def test_adapter_exception_is_retained_and_remaining_samples_continue(self):
        args = self.args(live=True, repeats=1)
        with patch.object(matrix.evaluation, 'evaluate_sample', side_effect=RuntimeError('adapter failed')) as call:
            self.assertEqual(self.run_matrix(args), 1)
        self.assertEqual(call.call_count, 4)
        record = json.loads((args.output / 'run.json').read_text())
        self.assertTrue(all('adapter failed' in s['errors'][0] for s in record['samples']))

    def test_suite_hash_rejected_before_run_directory(self):
        path = self.suite / 'model_cases.json'
        path.write_text(path.read_text().replace('reference index', 'changed index'), encoding='utf-8')
        args = self.args()
        with self.assertRaisesRegex(ValueError, 'hash'): self.run_matrix(args)
        self.assertFalse(args.output.exists())

    def test_cli_condition_document_and_default_plan(self):
        conditions = self.root / 'conditions.json'
        conditions.write_text(json.dumps({'conditions': CONDITIONS}), encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            code = matrix.main(['--suite', str(self.suite), '--output', str(self.root / 'cli'),
                               '--conditions', str(conditions), '--families', 'referent_repair', '--limit', '1'])
        self.assertEqual(code, 0)
        run = json.loads((self.root / 'cli/run.json').read_text())
        self.assertEqual(run['manifest']['planned_samples'], 12)
        self.assertFalse(run['manifest']['live'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
