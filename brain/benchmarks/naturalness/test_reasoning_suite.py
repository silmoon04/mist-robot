"""Generation and oracle-isolation tests only. No provider calls or model ratings."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reasoning_suite as suite


class ReasoningSuiteTests(unittest.TestCase):
    def test_reproducible_and_seed_sensitive(self):
        a = suite.generate('dev', 17)
        self.assertEqual(a, suite.generate('dev', 17))
        self.assertNotEqual(a['model_cases'], suite.generate('dev', 18)['model_cases'])
        self.assertEqual(a['manifest']['public_sha256'], suite.digest(a['model_cases']))
        self.assertEqual(a['manifest']['private_sha256'], suite.digest(a['private_oracles']))

    def test_count_coverage_and_whole_contrast_groups(self):
        for split in ('dev', 'heldout'):
            bundle = suite.generate(split, 4)
            cases = bundle['model_cases']['cases']
            self.assertEqual(len(cases), 24)
            self.assertEqual(len({c['id'] for c in cases}), 24)
            self.assertEqual({c['family'] for c in cases}, set(suite.FAMILIES))
            for family in suite.FAMILIES:
                rows = [c for c in cases if c['family'] == family]
                self.assertEqual(len(rows), 3)
                self.assertEqual(len({c['contrast_group'] for c in rows}), 1)
                self.assertEqual({c['split'] for c in rows}, {split})
            self.assertEqual(set(bundle['private_oracles']['oracles']), {c['id'] for c in cases})

    def test_heldout_has_distinct_entities_groups_and_prompts(self):
        for seed in (0, 17, 987):
            dev, held = suite.generate('dev', seed), suite.generate('heldout', seed)
            self.assertTrue(set(dev['manifest']['entities']).isdisjoint(held['manifest']['entities']))
            self.assertTrue(set(dev['manifest']['scenario_groups']).isdisjoint(held['manifest']['scenario_groups']))
            dev_queries = {c['model_input']['dialogue'][-1]['content'] for c in dev['model_cases']['cases']}
            held_queries = {c['model_input']['dialogue'][-1]['content'] for c in held['model_cases']['cases']}
            self.assertTrue(dev_queries.isdisjoint(held_queries))
            encoded = json.dumps(held['model_cases']).casefold()
            for source_entity in ('claude', 'mimecast', 'anthropic'):
                self.assertNotIn(source_entity, encoded)

    def test_split_membership_does_not_depend_on_seed(self):
        for split in ('dev', 'heldout'):
            group_sets = [{c['scenario_group'] for c in suite.generate(split, n)['model_cases']['cases']}
                          for n in (1, 7, 90)]
            self.assertEqual(group_sets[0], group_sets[1])
            self.assertEqual(group_sets[1], group_sets[2])

    def test_payload_whitelist_blocks_oracle_and_metadata(self):
        bundle = suite.generate('dev', 17)
        case = copy.deepcopy(bundle['model_cases']['cases'][0])
        case['private_oracle'] = 'PRIVATE_CANARY'
        case['model_input']['oracle'] = 'PRIVATE_CANARY'
        case['title'] = 'PRIVATE_CANARY'
        payload = suite.model_payload(case)
        self.assertEqual(set(payload), {'context', 'dialogue', 'tools'})
        self.assertNotIn('PRIVATE_CANARY', json.dumps(payload))
        payload['context']['new'] = True
        self.assertNotIn('new', case['model_input']['context'])

    def test_runner_export_excludes_oracle_and_has_valid_schema(self):
        for split in ('dev', 'heldout'):
            bundle = suite.generate(split, 17)
            for oracle in bundle['private_oracles']['oracles'].values():
                oracle['meaning_review']['criteria'].append('PRIVATE_CANARY')
            exported = suite.runner_suite(bundle)
            self.assertNotIn('PRIVATE_CANARY', json.dumps(exported))
            for case in exported['cases']:
                self.assertEqual(case['split'], 'holdout' if split == 'heldout' else 'dev')
                self.assertEqual(case['mode'], 'text')
                self.assertEqual(case['turns'][0]['expect'], {})
                self.assertTrue(case['turns'][0]['user'])
            # Validate against the real existing runner without starting a model.
            spec = importlib.util.spec_from_file_location('reasoning_runner_validation', HERE / 'runner.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'runner.json'
                path.write_text(json.dumps(exported), encoding='utf-8')
                checked, _ = module.checked_suite(path)
                self.assertEqual(len(checked['cases']), 24)

    def test_every_oracle_is_bound_to_model_input_and_needs_review(self):
        for split in ('dev', 'heldout'):
            bundle = suite.generate(split, 17)
            for case in bundle['model_cases']['cases']:
                oracle = bundle['private_oracles']['oracles'][case['id']]
                self.assertEqual(oracle['model_input_sha256'], suite.digest(case['model_input']))
                self.assertIsNone(oracle['meaning_review']['rating'])
                self.assertTrue(oracle['meaning_review']['no_keyword_grading'])
                self.assertGreaterEqual(len(oracle['meaning_review']['criteria']), 1)
                self.assertEqual(case['model_input']['dialogue'][-1]['role'], 'user')

    def test_contrasts_reject_always_ask_abstain_or_act(self):
        bundle = suite.generate('heldout', 17)
        oracles = bundle['private_oracles']['oracles']
        def decisions(family):
            return {oracles[c['id']]['intended_response_class'] for c in bundle['model_cases']['cases'] if c['family'] == family}
        self.assertEqual(decisions('referent_repair'), {'answer_using_corrected_referent', 'focused_clarification', 'follow_explicit_new_topic'})
        self.assertEqual(decisions('evidence_calibration'), {'answer_from_dated_evidence', 'state_current_unknown_with_known_boundary', 'labelled_forecast'})
        self.assertEqual(decisions('unfinished_multi_intent'), {'wait_without_committing_actions', 'act_and_answer_complete_request', 'answer_without_withdrawn_action'})

    def test_missing_or_malformed_tool_trace_is_unmeasured(self):
        oracle = {'objective_tool_checks': [{'kind': 'no_calls'}]}
        for calls, complete in [(None, True), ([], False), ([{'name': 'x'}], True), ('no calls', True)]:
            result = suite.grade_tool_trace(oracle, calls, complete=complete)
            self.assertEqual(result['status'], 'unmeasured')
            self.assertIsNone(result['meaning_score'])

    def test_tool_order_duplicates_and_arguments_are_checked(self):
        expected = [{'name': 'get_sensor_snapshot', 'args': {}}, {'name': 'set_expression', 'args': {'expression': 'curious'}}]
        oracle = {'objective_tool_checks': [{'kind': 'exact_call_sequence', 'calls': expected}]}
        self.assertEqual(suite.grade_tool_trace(oracle, expected, complete=True)['status'], 'pass')
        for bad in [list(reversed(expected)), expected + [expected[-1]], expected[:1],
                    [expected[0], {'name': 'set_expression', 'args': {'expression': 'happy'}}]]:
            self.assertEqual(suite.grade_tool_trace(oracle, bad, complete=True)['status'], 'fail')
        no_calls = {'objective_tool_checks': [{'kind': 'no_calls'}]}
        self.assertEqual(suite.grade_tool_trace(no_calls, [], complete=True)['status'], 'pass')
        self.assertEqual(suite.grade_tool_trace(no_calls, expected, complete=True)['status'], 'fail')
        no_motion = {'objective_tool_checks': [{'kind': 'forbidden_names', 'names': ['preview_motion']}]}
        self.assertEqual(suite.grade_tool_trace(no_motion, expected, complete=True)['status'], 'pass')
        self.assertEqual(suite.grade_tool_trace(no_motion, [{'name': 'preview_motion', 'args': {}}], complete=True)['status'], 'fail')

    def test_unknown_check_is_not_silently_a_pass(self):
        with self.assertRaises(ValueError):
            suite.grade_tool_trace({'objective_tool_checks': [{'kind': 'keyword_magic'}]}, [], complete=True)

    def test_cli_writes_separate_files_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'frozen'
            result = subprocess.run([sys.executable, str(HERE / 'reasoning_suite.py'), '--split', 'heldout', '--seed', '71', '--output', str(output)], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout)['cases'], 24)
            self.assertEqual({p.name for p in output.iterdir()}, {'manifest.json', 'model_cases.json', 'private_oracles.json', 'runner_cases.json'})
            public = json.loads((output / 'model_cases.json').read_text(encoding='utf-8'))
            private = json.loads((output / 'private_oracles.json').read_text(encoding='utf-8'))
            self.assertNotIn('oracles', public)
            self.assertEqual(len(private['oracles']), 24)
            with self.assertRaises(FileExistsError):
                suite.write_suite(output, 'dev', 1)

    def test_invalid_generation_arguments(self):
        for split, seed in [('holdout', 1), ('all', 1), ('dev', -1), ('dev', True), ('dev', 2**32)]:
            with self.assertRaises(ValueError):
                suite.generate(split, seed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
