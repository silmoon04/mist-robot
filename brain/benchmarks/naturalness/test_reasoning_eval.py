"""Offline adapter integrity; fake output is never model evaluation evidence."""
import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reasoning_eval as evaluation
from reasoning_suite import write_suite, digest


class ReasoningEvalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.suite = self.root/'suite'
        write_suite(self.suite, 'dev', 17)

    def args(self, **changes):
        values = dict(suite=self.suite,output=self.root/'out',provider='cerebras',model=None,reasoning='low',
                      ids=None,families='referent_repair',limit=1,repeats=1,timeout=10,max_output_tokens=1024,live=False)
        values.update(changes)
        return argparse.Namespace(**values)

    def test_suite_hash_mismatch_is_rejected_before_output(self):
        path=self.suite/'model_cases.json'
        data=json.loads(path.read_text(encoding='utf-8'))
        data['cases'][0]['model_input']['context']['modified']=True
        path.write_text(json.dumps(data),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'hash'):
            evaluation.run(self.args())
        self.assertFalse((self.root/'out').exists())

    def test_family_limit_id_selection(self):
        public,_=evaluation.load_suite(self.suite)
        cases=evaluation.select_cases(public,families='referent_repair,metacommunication',limit=4)
        self.assertEqual(len(cases),4)
        self.assertLessEqual({c['family'] for c in cases},{'referent_repair','metacommunication'})
        self.assertEqual(evaluation.select_cases(public,ids=cases[0]['id'])[0]['id'],cases[0]['id'])
        with self.assertRaises(ValueError):evaluation.select_cases(public,families='not_a_family')

    def test_dry_run_never_creates_a_provider_and_refuses_overwrite(self):
        with patch.object(evaluation,'make_client',side_effect=AssertionError('provider forbidden')):
            evaluation.run(self.args(),client_factory=lambda *a: self.fail('provider called'))
        saved=json.loads((self.root/'out/run.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['samples'][0]['status'],'planned')
        self.assertIsNone(saved['samples'][0]['semantic_pass'])
        with self.assertRaises(FileExistsError):evaluation.run(self.args())

    def test_no_private_oracle_or_metadata_leaks_to_fake_client(self):
        private=self.suite/'private_oracles.json'
        private.write_text('PRIVATE_ORACLE_SENTINEL_NOT_VALID_JSON',encoding='utf-8')
        public_path=self.suite/'model_cases.json'
        public=json.loads(public_path.read_text(encoding='utf-8'))
        for case in public['cases']:case['review_secret']='HIDDEN_CASE_METADATA_SENTINEL'
        public_path.write_text(json.dumps(public),encoding='utf-8')
        manifest_path=self.suite/'manifest.json'
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest['public_sha256']=digest(public)
        manifest_path.write_text(json.dumps(manifest),encoding='utf-8')
        prompts=[]
        class Fake:
            backend_info={'provider':'offline_fake'}
            def new_session(self):pass
            def ask(self,prompt,timeout):
                prompts.append(prompt)
                return SimpleNamespace(text='Fixture answer',tool_calls=[],errors=[],ttft_s=.1,total_s=.2,
                    timings={},input_tokens=2,output_tokens=2,cache_read_tokens=0)
            def close(self):pass
        self.assertEqual(evaluation.run(self.args(live=True),client_factory=lambda *a:Fake()),0)
        self.assertEqual(len(prompts),1)
        for sentinel in ('PRIVATE_ORACLE_SENTINEL','HIDDEN_CASE_METADATA_SENTINEL','intended_response_class','meaning_review'):
            self.assertNotIn(sentinel,prompts[0])
        self.assertIn('dialogue',prompts[0]);self.assertIn('context',prompts[0])
        saved=json.loads((self.root/'out/run.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['samples'][0]['quality'],'unrated')

    def test_tool_cases_unsupported_without_client_or_score(self):
        args=self.args(live=True,families='action_receipts',limit=None)
        evaluation.run(args,client_factory=lambda *a:self.fail('provider called'))
        data=json.loads((args.output/'run.json').read_text(encoding='utf-8'))
        self.assertTrue(all(s['status']=='unsupported' and s['tool_behavior_assessed'] is False for s in data['samples']))

    def test_provider_failure_is_retained_and_following_samples_run(self):
        args=self.args(live=True,limit=2)
        code=evaluation.run(args,client_factory=lambda *a:(_ for _ in ()).throw(RuntimeError('fake failure')))
        self.assertEqual(code,1)
        data=json.loads((args.output/'run.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data['samples']),2)
        self.assertEqual(data['status_counts'],{'failed':2})
        self.assertTrue(all('fake failure' in s['errors'][0] for s in data['samples']))


if __name__=='__main__':unittest.main()
