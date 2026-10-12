"""Contracts for replaying conversation expectations without pretending to play audio."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import expectation_bench as bench


class FakeClient:
    def __init__(self, fail=False):
        self.prompt='production prompt'
        self.backend_info={'provider':'fixture'}
        self.inputs=[]
        self.closed=False
        self.fail=fail

    def ask(self, text, timeout, on_event):
        self.inputs.append(text)
        on_event({'type':'message_update','assistantMessageEvent':{'delta':'A reply.'}})
        return SimpleNamespace(text='A reply.',tool_calls=[],errors=['transport failed'] if self.fail else [],
            timings={'streamed_visible_text':'A reply.'},input_tokens=10,output_tokens=3,
            ttft_s=.02,total_s=.03)

    def close(self):self.closed=True


def case(identifier='one', mode='text'):
    return {'id':identifier,'category':'repair','mode':mode,'split':'dev',
            'review_criteria':['PRIVATE GRADING SENTINEL'],
            'turns':[{'user':'A name was misheard.','expect':{}},
                     {'user':'I meant a different name.','expect':{}}]}


class Tests(unittest.TestCase):
    def test_codex_interface_prompt_is_captured(self):
        client=FakeClient()
        client._system_prompt=client.prompt
        del client.prompt
        with tempfile.TemporaryDirectory() as temp:
            row=bench.run_case(case(),1,Path(temp)/'codex',{'id':'fixture'},lambda *args:client)
            self.assertEqual(row['status'],'completed')
            self.assertEqual(len(client.inputs),2)

    def test_partial_tool_evidence_survives_transport_exception(self):
        class RaisingClient(FakeClient):
            def ask(self,text,timeout,on_event):
                self._bridge.request('call',{'name':'set_expression','arguments':{'expression':'happy'}})
                on_event({'type':'message_update','assistantMessageEvent':{'delta':'Some words'}})
                raise RuntimeError('Transport ended')
        with tempfile.TemporaryDirectory() as temp:
            row=bench.run_case(case(),1,Path(temp)/'partial',{'id':'fixture'},lambda *args:RaisingClient())
            self.assertEqual(row['status'],'failed')
            self.assertEqual(row['attempted_turns'],1)
            self.assertEqual(row['completed_turns'],0)
            self.assertEqual(row['turns'][0]['receipts'][0]['name'],'set_expression')
            self.assertEqual(row['turns'][0]['text'],'Some words')

    def test_cleanup_failure_does_not_erase_evidence(self):
        class ClosingClient(FakeClient):
            def close(self):raise RuntimeError('Close failed')
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)/'cleanup'
            row=bench.run_case(case(),1,directory,{'id':'fixture'},lambda *args:ClosingClient())
            self.assertEqual(row['status'],'failed')
            self.assertEqual(row['completed_turns'],2)
            self.assertTrue(row['cleanup_errors'])
            self.assertEqual(json.loads((directory/'sample.json').read_text(encoding='utf-8'))['status'],'failed')

    def test_suite_cannot_change_between_validation_and_freeze(self):
        from unittest.mock import patch
        original=bench.runner.checked_suite
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'suite.json'
            path.write_text(json.dumps({'cases':[case()]}),encoding='utf-8')
            def change_after_parse(p):
                value=original(p)
                path.write_text(json.dumps({'cases':[case('different')]}),encoding='utf-8')
                return value
            with patch.object(bench.runner,'checked_suite',change_after_parse):
                with self.assertRaisesRegex(ValueError,'Suite changed'):
                    bench.run(SimpleNamespace(suite=path))

    def test_fresh_case_sessions_actual_turn_history_and_no_rubric_leak(self):
        clients=[]
        def factory(runtime, folder, architecture):
            client=FakeClient();clients.append(client);return client
        with tempfile.TemporaryDirectory() as temp:
            for identifier in ['one','two']:
                row=bench.run_case(case(identifier),1,Path(temp)/identifier,{'id':'fixture'},factory)
                self.assertEqual(row['status'],'completed')
                self.assertIsNone(row['semantic_pass'])
                self.assertEqual(row['evidence_mode'],'text_only')
            self.assertEqual(len(clients),2)
            self.assertTrue(all(c.closed for c in clients))
            self.assertEqual(clients[0].inputs,['A name was misheard.','I meant a different name.'])
            self.assertNotIn('PRIVATE GRADING SENTINEL',repr(clients[0].inputs))

    def test_audio_case_never_falls_back_to_text_and_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            def factory(*args):self.fail('Audio must not contact the text provider')
            row=bench.run_case(case(mode='timed_audio'),1,Path(temp)/'audio',{'id':'fixture'},factory)
            self.assertEqual(row['status'],'unsupported')
            self.assertIsNone(row['semantic_pass'])

    def test_failed_turn_is_retained_and_followup_is_not_sent(self):
        client=FakeClient(fail=True)
        with tempfile.TemporaryDirectory() as temp:
            row=bench.run_case(case(),1,Path(temp)/'failed',{'id':'fixture'},lambda *args:client)
            self.assertEqual(row['status'],'failed')
            self.assertEqual(len(client.inputs),1)
            self.assertEqual(row['turns'][0]['errors'],['transport failed'])
            self.assertTrue(client.closed)
            self.assertEqual(row['expected_turns'],2)

    def test_missing_capability_fixture_is_explicitly_unsupported(self):
        scenario=case();scenario['fixtures']={'clock':'controlled_clock'}
        with tempfile.TemporaryDirectory() as temp:
            row=bench.run_case(scenario,1,Path(temp)/'clock',{'id':'fixture'},lambda *args:self.fail())
            self.assertEqual(row['status'],'unsupported')
            self.assertIn('fixture',row['unsupported_reason'])

    def test_no_overwrite_of_case_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)/'case'
            bench.run_case(case(),1,directory,{'id':'fixture'},lambda *args:FakeClient())
            with self.assertRaises(FileExistsError):
                bench.run_case(case(),1,directory,{'id':'fixture'},lambda *args:FakeClient())

    def test_production_factory_forwards_the_selected_architecture(self):
        from unittest.mock import patch
        made=[]
        class Voice:
            def __init__(self,*args,**kwargs):made.append(kwargs)
            def make_client(self):return FakeClient()
        configuration={'id':'qwen-assist','provider':'cerebras','model':'qwen-3.8-27b',
            'reasoning_effort':'low','max_output_tokens':4096,'floor':'selective','endpoint_ms':500,
            'incomplete_hold_ms':900,'conversation_policy':'responsive','parallel_tool_calls':True}
        with tempfile.TemporaryDirectory() as temp,patch('benchmarks.naturalness.cascade_voice.CascadeVoice',Voice):
            bench.production_client(SimpleNamespace(memory=[]),Path(temp),configuration)
        for field in ['model','reasoning_effort','max_output_tokens','conversation_policy','parallel_tool_calls']:
            self.assertEqual(made[0][field],configuration[field])


if __name__=='__main__':unittest.main()
