import hashlib
import json
from pathlib import Path
import unittest

from expand_suite import additions
from runner import checked_suite, unsupported_reason

HERE = Path(__file__).resolve().parent


class ExpansionTests(unittest.TestCase):
    def test_original_cases_and_digest_preserved(self):
        original = (HERE/'cases.json').read_bytes()
        base = json.loads(original)
        expanded, _ = checked_suite(HERE/'cases_v2.json')
        self.assertEqual(expanded['cases'][:len(base['cases'])], base['cases'])
        self.assertEqual(expanded['parent_suite_sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(expanded['cases'][len(base['cases']):], additions())

    def test_fault_and_audio_conditions_cannot_silently_pass_text(self):
        new = additions()
        self.assertEqual(len(new),18)
        self.assertEqual(sum(unsupported_reason(c) is None for c in new),12)
        for case in new:
            if case.get('measurement_plan',{}).get('status') == 'fixture_not_implemented':
                self.assertIsNotNone(unsupported_reason(case))
            self.assertEqual(case['split'],'dev')
            self.assertTrue(case['paired_control'])
            self.assertTrue(case['provenance']['research_workers'])


if __name__ == '__main__':
    unittest.main()
