import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import reasoning_pair
from reasoning_suite import write_suite


class PairTests(unittest.TestCase):
    def test_paired_settings_blind_review_and_failure_retention(self):
        observed=[]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);suite=root/'suite';output=root/'results'
            write_suite(suite,'dev',13)
            args=SimpleNamespace(suite=suite,output=output,ids=None,families='referent_repair',limit=None,repeats=1,seed=13,timeout=10,max_output_tokens=2048,live=True)
            def fake(case,repeat,folder,config,prompt,**kwargs):
                observed.append((case['id'],dict(config),prompt))
                failed=case['variant']=='unanchored' and config['reasoning']=='low'
                return {'case_id':case['id'],'repeat':repeat,'model_input':case['model_input'],'status':'failed' if failed else 'completed','text':'<script>fictional reply</script>','errors':['fixture failure'] if failed else [],'semantic_pass':None}
            with patch.object(reasoning_pair.evaluation,'evaluate_sample',side_effect=fake):
                self.assertEqual(reasoning_pair.run(args),1)
                with self.assertRaises(FileExistsError):reasoning_pair.run(args)
            record=json.loads((output/'run.json').read_text(encoding='utf-8'))
            self.assertEqual(len(record['samples']),6)
            self.assertTrue(any(s['status']=='failed' for s in record['samples']))
            for cid in {x[0] for x in observed}:
                left,right=[r for r in observed if r[0]==cid]
                self.assertEqual({left[1]['reasoning'],right[1]['reasoning']},{'low','high'})
                self.assertEqual(left[2],right[2])
                self.assertEqual({k:v for k,v in left[1].items() if k!='reasoning'},{k:v for k,v in right[1].items() if k!='reasoning'})
            document=(output/'review.html').read_text(encoding='utf-8')
            self.assertNotIn('<script>fictional reply</script>',document)
            self.assertIn('&lt;script&gt;',document)
            self.assertNotIn('candidate',document)
            self.assertNotIn('baseline',document)
            self.assertTrue((output/'answer_key.private.json').exists())
            self.assertIsNone(record['manifest']['meaning_score'])


if __name__=='__main__':unittest.main()
