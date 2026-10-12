"""Pure final_matrix parser checks; no simulation or report generation."""
from copy import deepcopy
import unittest
import report_results as report
from locomotion.sensor_sim import SimulatedIMU


def fixture():
    case = {'case_id': 'toy-stop', 'command_name': 'stop', 'seed': 6000000001,
            'status': 'ready', 'env_kwargs': {'command': [0, 0, 0], 'terrain': 'flat',
            'payload': .155, 'sensor_mode': 'mpu6050', 'randomize': False}}
    declaration = {**deepcopy(case), 'steps': 960,
                   'resolved_sensor_profile': SimulatedIMU().profile,
                   'sensor_distribution_shift': False}
    sources = {'locomotion/mist_env.py': 'a'*64}
    row = {**deepcopy(case), 'passed': True, 'checks': {v: True for v in report.FLAGS.values()},
           'criteria': report.CRITERIA, 'acceptance_version': report.VERSION,
           'source_hashes': sources, 'samples': 960, 'metrics': {'body_velocity_rmse_m_s': .001}}
    receipt = {'schema': 1, 'purpose': 'untouched final simulation test; no checkpoint selection',
               'source_hashes': sources, 'criteria': report.CRITERIA, 'steps': 960,
               'wrapper_sha256': 'b'*64, 'ordered_resolved_cases': [declaration],
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


if __name__ == '__main__':
    unittest.main()
