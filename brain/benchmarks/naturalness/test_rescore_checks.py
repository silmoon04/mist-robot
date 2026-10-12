import json
from pathlib import Path
import tempfile
import unittest

import runner
from rescore_checks import rescore


class RescoreTests(unittest.TestCase):
    def test_derived_scoring_preserves_source_events_and_tool_requirements(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            suite={'cases':[{'id':'test','split':'dev','category':'numbers','mode':'text','turns':[{'user':'Multiply','expect':{'contains_any':['fifty-six'],'required_tools':['recall']}}]}]}
            runner.save(root/'cases.frozen.json',suite)
            checks=[{'name':'contains_any','passed':False,'critical':False},{'name':'required_tool:recall','passed':False,'critical':False}]
            events=[{'name':'first_text','t_ms':12,'clock_id':'c','case_id':'test','turn_id':'1'}]
            run={'manifest':{'suite_sha256':runner.sha((root/'cases.frozen.json').read_bytes())},'samples':[{'case_id':'test','repeat':1,'events':events,'checks':checks,'turns':[{'turn_id':'1','text':'Fifty\u2011six.','tools':[],'state_before':{},'state_after':{},'checks':checks}]}]}
            runner.save(root/'run.json',run)
            before=(root/'run.json').read_bytes()
            rescore(root/'run.json',root/'derived.json')
            self.assertEqual((root/'run.json').read_bytes(),before)
            after=json.loads((root/'derived.json').read_bytes())
            self.assertEqual(after['samples'][0]['events'],events)
            turn=after['samples'][0]['turns'][0]
            current={c['name']:c['passed'] for c in turn['checks']}
            self.assertTrue(current['contains_any'])
            self.assertFalse(current['required_tool:recall'])
            self.assertEqual(turn['original_checks'],checks)
            self.assertEqual(after['manifest']['regrading']['parent_run_sha256'],runner.sha(before))
            with self.assertRaises(ValueError):
                rescore(root/'run.json',root/'derived.json')


if __name__=='__main__':
    unittest.main()
