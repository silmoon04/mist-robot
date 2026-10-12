"""Pure final_matrix parser checks; no simulation or report generation."""
from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import report_results as report
from locomotion.sensor_sim import SimulatedIMU


def fixture():
    case = {'case_id': 'toy-stop', 'command_name': 'stop', 'seed': 6000000001,
            'status': 'ready', 'env_kwargs': {'command': [0, 0, 0], 'terrain': 'flat',
            'payload': .155, 'sensor_mode': 'mpu6050', 'randomize': False}}
    declaration = {**deepcopy(case), 'steps': 960,
                   'resolved_sensor_profile': SimulatedIMU().profile,
                   'sensor_distribution_shift': False}
    sources = report.read(report.HERE / 'handoff/frozen_sources.json')
    row = {**deepcopy(case), 'passed': True, 'checks': {v: True for v in report.FLAGS.values()},
           'criteria': report.CRITERIA, 'acceptance_version': report.VERSION,
           'source_hashes': sources, 'samples': 960, 'metrics': {'body_velocity_rmse_m_s': .001}}
    receipt = {'schema': 1, 'purpose': 'untouched final simulation test; no checkpoint selection',
               'source_hashes': sources, 'criteria': report.CRITERIA, 'steps': 960,
               'wrapper_sha256': report.digest(report.HERE / 'final_matrix.py'), 'ordered_resolved_cases': [declaration],
               'results': [row], 'total_cases': 1, 'passed_cases': 1}
    receipt['suite_sha256'] = report.identity({'criteria': receipt['criteria'],
                                            'cases': receipt['ordered_resolved_cases'], 'steps': 960})
    return receipt


class ParserTests(unittest.TestCase):
    def test_documented_schema_roundtrip(self):
        import json
        receipt = json.loads(json.dumps(fixture()))
        indexed = report.validate_cases(receipt)
        self.assertEqual(report.summarize(list(indexed.values()))['strict_passes'], 1)

    def test_rejects_old_cases_schema(self):
        receipt = fixture()
        receipt['cases'] = receipt.pop('results')
        with self.assertRaises(KeyError): report.validate_cases(receipt)

    def test_rejects_count_suite_and_ordered_metadata_tamper(self):
        for edit in ('total', 'pass', 'suite', 'seed', 'environment', 'source', 'score', 'profile'):
            with self.subTest(edit=edit):
                r = fixture()
                if edit == 'total': r['total_cases'] = 2
                if edit == 'pass': r['passed_cases'] = 0
                if edit == 'suite': r['ordered_resolved_cases'][0]['seed'] += 1
                if edit == 'seed': r['results'][0]['seed'] += 1
                if edit == 'environment': r['results'][0]['env_kwargs']['payload'] = .08
                if edit == 'source': r['results'][0]['source_hashes'] = {'other': 'c'*64}
                if edit == 'score': r['results'][0]['checks']['velocity'] = False
                if edit == 'profile': r['ordered_resolved_cases'][0]['resolved_sensor_profile']['transport_delay_s'] = .08
                with self.assertRaises(ValueError): report.validate_cases(r)

    def test_execution_errors_are_unknown_not_zero_metrics(self):
        r = fixture()
        r['results'][0] = {k: v for k, v in r['results'][0].items()
                           if k in ('case_id', 'command_name', 'seed', 'status', 'env_kwargs')}
        r['results'][0].update(execution_error='probe error', passed=False)
        r['passed_cases'] = 0
        indexed = report.validate_cases(r)
        rows = [fixture()['results'][0], *indexed.values()]
        summary = report.summarize(rows)
        self.assertEqual(summary['execution_errors'], 1)
        self.assertEqual(summary['velocity_metric_cases'], 1)
        self.assertEqual(summary['unknown_flags'], 1)

    def test_real_final_producer_schema(self):
        receipt = report.read(report.HERE / 'runs/final_baseline_all.json')
        indexed = report.validate_cases(receipt)
        self.assertEqual(len(indexed), 239)
        self.assertEqual(report.summarize(list(indexed.values()))['strict_passes'], 20)

    def test_numpy_bool_requires_producer_json_conversion(self):
        import numpy as np
        receipt = fixture()
        receipt['results'][0]['passed'] = np.bool_(True)
        receipt['results'][0]['checks']['velocity'] = np.bool_(True)
        receipt['passed_cases'] = np.int64(1)
        with self.assertRaises(ValueError):
            report.validate_cases(receipt)
        # final_matrix.json_native and train.json_value use scalar.item().
        serialized = json.loads(json.dumps(receipt, default=lambda value: value.item()))
        self.assertEqual(report.validate_cases(serialized)['toy-stop']['passed'], True)

    def test_boolean_count_and_metric_rejected(self):
        receipt = fixture()
        receipt['passed_cases'] = True
        with self.assertRaises(ValueError):
            report.validate_cases(receipt)
        receipt = fixture()
        receipt['results'][0]['metrics']['body_velocity_rmse_m_s'] = True
        with self.assertRaises(ValueError):
            report.summarize(receipt['results'])


class PausedTests(unittest.TestCase):
    def periodic(self, algorithm='ppo'):
        return report.read(report.HERE / f'runs/{algorithm}_51200/evaluation_periodic_51200.json')

    def test_real_training_schema_is_distinct_from_final_matrix(self):
        for algorithm, passes in (('ppo', 6), ('sac', 0)):
            with self.subTest(algorithm=algorithm):
                receipt = self.periodic(algorithm)
                measured = report.validate_periodic(receipt)
                self.assertEqual((measured['strict_passes'], measured['total']), (passes, 72))
                self.assertFalse(measured['eligible'])
                self.assertEqual(measured['fall_fraction'], 0)
                self.assertIn('not recorded', measured['checkpoint_binding'])
                with self.assertRaises(ValueError):
                    report.validate_cases(receipt)
        with self.assertRaises(ValueError):
            report.validate_periodic(fixture())

    def test_periodic_tamper_is_rejected(self):
        for edit in ('eligible', 'suite', 'acceptance', 'string_bool', 'fall'):
            with self.subTest(edit=edit):
                receipt = self.periodic()
                if edit == 'eligible': receipt['eligible'] = True
                if edit == 'suite': receipt['episodes'][0]['seed'] += 1
                if edit == 'acceptance': receipt['episodes'][0]['acceptance']['passed'] = False
                if edit == 'string_bool': receipt['episodes'][0]['acceptance']['checks']['velocity'] = 'true'
                if edit == 'fall': receipt['fall_fraction'] = .5
                with self.assertRaises(ValueError):
                    report.validate_periodic(receipt)

    def test_paused_report_preserves_real_inputs_and_missing_artifacts(self):
        inputs = [report.HERE / 'handoff/PAUSED_STATE.json',
                  report.HERE / 'runs/ppo_51200/evaluation_periodic_51200.json',
                  report.HERE / 'runs/sac_51200/evaluation_periodic_51200.json']
        before = [report.digest(path) for path in inputs]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'report'
            summary = report.generate(mode='paused', output_dir=output)
            self.assertEqual(summary, report.read(output / 'result_summary.json'))
            self.assertEqual(summary['mode'], 'paused')
            self.assertFalse(summary['hardware_qualified'])
            self.assertFalse(summary['checkpoint_selection'])
            self.assertEqual(summary['untouched_final_tests'], {})
            for name, passes, updates in (('PPO', 6, 245), ('SAC', 0, 25343)):
                candidate = summary['policies'][name]
                self.assertEqual(candidate['recorded_timesteps'], 51200)
                self.assertEqual(candidate['optimizer_updates'], updates)
                self.assertEqual(candidate['periodic_validation']['strict_passes'], passes)
                self.assertEqual(candidate['final_test_status'], 'not_supplied')
                self.assertEqual(len(candidate['missing_final_artifacts']), 2)
                self.assertNotIn('training_summary', candidate)
            self.assertIn('does not record checkpoint or source hashes', (output / 'RESULTS.md').read_text())
            with self.assertRaises(FileExistsError):
                report.generate(mode='paused', output_dir=output)
        self.assertEqual(before, [report.digest(path) for path in inputs])

    def test_paused_output_scope_and_explicit_final_validation(self):
        with self.assertRaises(ValueError):
            report.generate(mode='paused')
        with self.assertRaises(ValueError):
            report.generate(mode='paused', output_dir=report.HERE / 'runs/new_report')
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'report'
            with self.assertRaises(ValueError):
                report.generate(mode='paused', output_dir=output,
                                final_receipts={'ppo': report.HERE / 'runs/final_baseline_all.json'})
            self.assertFalse(output.exists())

    def final_error_fixture(self):
        # An in-memory all-error receipt exercises final_matrix's exception path.
        # Use real declarations and artifact hashes; no policy measurements are invented.
        receipt = report.read(report.HERE / 'runs/final_baseline_all.json')
        receipt['ordered_resolved_cases'] = [case for case in receipt['ordered_resolved_cases']
                                           if case['env_kwargs']['sensor_mode'] == 'mpu6050']
        state = report.read(report.HERE / 'handoff/PAUSED_STATE.json')
        checkpoint = report.HERE.parent / state['checkpoints']['ppo']['path']
        record = report.read(checkpoint.with_suffix('.provenance.json'))
        receipt.update(controller='ppo', checkpoint=str(checkpoint),
                       checkpoint_sha256=record['checkpoint_sha256'],
                       checkpoint_envelope_sha256=record['envelope_sha256'],
                       wrapper_sha256=report.digest(report.HERE / 'final_matrix.py'))
        declared = record['envelope']['experiment']['sensor']
        for case in receipt['ordered_resolved_cases']:
            case['sensor_distribution_shift'] = declared['mode'] != case['env_kwargs']['sensor_mode'] or declared['profile'] != case['resolved_sensor_profile']
        receipt['results'] = [{k: case[k] for k in ('case_id', 'command_name', 'seed', 'status', 'env_kwargs')}
                              | {'passed': False, 'execution_error': 'test worker exception'}
                              for case in receipt['ordered_resolved_cases']]
        receipt['total_cases'], receipt['passed_cases'] = 131, 0
        receipt['suite_sha256'] = report.identity({'criteria': receipt['criteria'],
            'cases': receipt['ordered_resolved_cases'], 'steps': receipt['steps']})
        return receipt

    def test_explicit_all_error_final_receipt_reports_unknown_metrics(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'final_errors.json'
            path.write_text(json.dumps(self.final_error_fixture()))
            summary = report.generate(mode='paused', output_dir=Path(temporary) / 'report',
                                      final_receipts={'ppo': path})
            final = summary['untouched_final_tests']['PPO']['summary']
            self.assertEqual(final['execution_errors'], 131)
            self.assertEqual(final['unknown_flags'], 131)
            self.assertEqual(final['velocity_metric_cases'], 0)
            self.assertIsNone(final['velocity_rmse_median_m_s'])
            self.assertFalse(summary['checkpoint_selection'])

    def test_paused_cli_prints_bounded_counts_and_keeps_full_evidence_file(self):
        for with_final in (False, True):
            with self.subTest(with_final=with_final), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / 'report'
                argv = ['report_results.py', '--mode', 'paused', '--output-dir', str(output)]
                if with_final:
                    final = Path(temporary) / 'final_errors.json'
                    final.write_text(json.dumps(self.final_error_fixture()))
                    argv += ['--ppo-final', str(final)]
                captured = io.StringIO()
                with patch.object(report.sys, 'argv', argv), redirect_stdout(captured):
                    report.main()
                self.assertLess(len(captured.getvalue()), 4096)
                printed = json.loads(captured.getvalue())
                saved = report.read(output / 'result_summary.json')
                self.assertEqual(printed['status'], 'report_written')
                self.assertFalse(printed['hardware_qualified'])
                self.assertFalse(printed['checkpoint_selection'])
                self.assertEqual(printed['output_files'],
                                 {name: str((output / name).resolve())
                                  for name in ('result_summary.json', 'RESULTS.md')})
                for name in ('PPO', 'SAC'):
                    self.assertEqual(printed['policies'][name]['periodic_validation'],
                                     {key: saved['policies'][name]['periodic_validation'][key]
                                      for key in ('strict_passes', 'total', 'execution_errors')})
                self.assertNotIn('checkpoint_record', captured.getvalue())
                self.assertNotIn('ordered_resolved_cases', captured.getvalue())
                self.assertIn('envelope', saved['policies']['PPO']['checkpoint_record'])
                if with_final:
                    self.assertEqual(printed['policies']['PPO']['untouched_final_test'],
                                     {'strict_passes': 0, 'total': 131, 'execution_errors': 131})
                    self.assertEqual(len(saved['untouched_final_tests']['PPO']['lineage']['ordered_resolved_cases']), 131)
                else:
                    self.assertEqual(printed['policies']['PPO']['final_test_status'], 'not_supplied')
                    self.assertNotIn('untouched_final_test', printed['policies']['PPO'])

    def test_explicit_final_rejects_changed_frozen_contract_and_artifacts(self):
        for edit in ('order', 'horizon', 'command', 'status', 'checkpoint', 'source', 'wrapper', 'shift'):
            with self.subTest(edit=edit), tempfile.TemporaryDirectory() as temporary:
                receipt = self.final_error_fixture()
                if edit == 'order':
                    receipt['ordered_resolved_cases'].reverse()
                    receipt['results'].reverse()
                if edit == 'horizon':
                    receipt['steps'] = 1000
                    for case in receipt['ordered_resolved_cases']: case['steps'] = 1000
                if edit == 'command':
                    receipt['ordered_resolved_cases'][0]['command_name'] = 'forward'
                    receipt['results'][0]['command_name'] = 'forward'
                if edit == 'status':
                    receipt['ordered_resolved_cases'][0]['status'] = 'other'
                    receipt['results'][0]['status'] = 'other'
                if edit == 'checkpoint': receipt['checkpoint_sha256'] = '0' * 64
                if edit == 'source': receipt['source_hashes'] = {'locomotion/mist_env.py': report.digest(report.HERE / 'mist_env.py')}
                if edit == 'wrapper': receipt['wrapper_sha256'] = '0' * 64
                if edit == 'shift': receipt['ordered_resolved_cases'][0]['sensor_distribution_shift'] = not receipt['ordered_resolved_cases'][0]['sensor_distribution_shift']
                receipt['suite_sha256'] = report.identity({'criteria': receipt['criteria'],
                    'cases': receipt['ordered_resolved_cases'], 'steps': receipt['steps']})
                path = Path(temporary) / 'final.json'
                path.write_text(json.dumps(receipt))
                with self.assertRaises(ValueError):
                    report.generate(mode='paused', output_dir=Path(temporary) / 'report', final_receipts={'ppo': path})
                self.assertFalse((Path(temporary) / 'report').exists())

    def test_default_complete_still_requires_finished_inputs(self):
        with self.assertRaises(FileNotFoundError):
            report.generate()

    def test_real_checkpoint_bytes_envelope_and_saved_counts(self):
        state = report.read(report.HERE / 'handoff/PAUSED_STATE.json')
        sources = report.read(report.HERE / 'handoff/frozen_sources.json')
        for algorithm in ('ppo', 'sac'):
            expected = state['checkpoints'][algorithm]
            checkpoint = report.HERE.parent / expected['path']
            record = report.validate_candidate(checkpoint, expected, algorithm, sources, report.HERE.parent)
            self.assertEqual(record['checkpoint_sha256'], report.digest(checkpoint))
            for field in ('sha256', 'recorded_timesteps', 'optimizer_updates'):
                bad = deepcopy(expected)
                bad[field] = '0' * 64 if field == 'sha256' else expected[field] + 1
                with self.assertRaises(ValueError):
                    report.validate_candidate(checkpoint, bad, algorithm, sources, report.HERE.parent)

    def test_source_content_verification_has_no_placeholder_allowance(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            source = repo / 'source.py'
            source.write_text('value = 42\n')
            hashes = {'source.py': report.digest(source)}
            report.validate_sources(hashes, repo)
            source.write_text('value = 43\n')
            with self.assertRaises(ValueError): report.validate_sources(hashes, repo)
            with self.assertRaises(ValueError): report.validate_sources({'source.py': 'a' * 64}, repo)
            with self.assertRaises(ValueError): report.evidence_path(repo, '../outside.py')


if __name__ == '__main__':
    unittest.main()
