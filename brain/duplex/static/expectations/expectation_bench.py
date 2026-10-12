"""Replay expectation cases through the selected voice model's real text/tool setup."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import random
import sys
import tempfile
import time

HERE=Path(__file__).resolve().parent
BRAIN=HERE.parents[1]
ROOT=BRAIN.parent
for directory in (BRAIN,BRAIN/'harness',HERE):
    if str(directory) not in sys.path:sys.path.insert(0,str(directory))
import runner

LIMITS=[
    'Text and isolated application-tool receipts only; no ASR, TTS, browser, speaker or physical robot.',
    'One model session per case; actual generated history is retained within each case.',
    'The foreground prompt and settings come from CascadeVoice.make_client; background tools are labelled stubs.',
    'For Codex, the saved prompt is the base prompt; the frozen Codex client source adds session instructions.',
    'A completed request is not a semantic pass. Meaning criteria require review; voice naturalness is unmeasured.',
]


def save(path,value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def sha(data):return hashlib.sha256(data).hexdigest()


def architecture(identifier):
    from duplex.live_studio import ARCHITECTURES
    value=next((dict(item) for item in ARCHITECTURES if item['id']==identifier),None)
    if value is None or value['provider']=='native':
        raise ValueError('Choose a configured text architecture; native voice requires audio evidence')
    return value


def production_client(runtime,directory,configuration):
    from benchmarks.naturalness.cascade_voice import CascadeVoice
    async def unused(*args):raise RuntimeError('The text benchmark cannot emit voice events')
    options={key:configuration[key] for key in ('provider','model','reasoning_effort','max_output_tokens',
             'floor','endpoint_ms','incomplete_hold_ms','conversation_policy','parallel_tool_calls')}
    voice=CascadeVoice(runtime,directory,unused,unused,unused,**options)
    return voice.make_client()


def run_case(case,repeat,directory,configuration,client_factory=production_client,timeout=45):
    directory.mkdir(parents=True,exist_ok=False)
    reason=runner.unsupported_reason(case)
    row={'case_id':case['id'],'repeat':repeat,'category':case['category'],'split':case['split'],
         'mode':case['mode'],'status':'unsupported' if reason else 'completed','turns':[],
         'expected_turns':len(case.get('turns',[])),'attempted_turns':0,'completed_turns':0,'semantic_pass':None,
         'human_review':'pending','evidence_mode':'text_only' if not reason else 'none',
         'limitations':LIMITS,'checks':[],'errors':[]}
    if reason:
        row['unsupported_reason']=reason
        save(directory/'sample.json',row)
        return row
    from duplex.runtime import RobotRuntime
    from eval_luna_conversations import RuntimeBridge,state_snapshot
    client=None
    with tempfile.TemporaryDirectory(prefix='mist-expectation-') as temporary:
        runtime=RobotRuntime(Path(temporary))
        bridge=RuntimeBridge(runtime)
        try:
            client=client_factory(runtime,directory,configuration)
            client._bridge=bridge
            row['backend']=client.backend_info
            prompt=getattr(client,'prompt',getattr(client,'_system_prompt',None))
            if not isinstance(prompt,str):raise ValueError('The client does not expose its system prompt')
            row['system_prompt_scope']='effective_provider_system_prompt' if hasattr(client,'prompt') else 'base_before_codex_session_instructions'
            (directory/'system_prompt.frozen.txt').write_bytes(prompt.encode('utf-8'))
            row['system_prompt_sha256']=sha(prompt.encode())
            for index,step in enumerate(case['turns']):
                bridge.prepare(step.get('sensor_profile','none'),step['user'])
                before=state_snapshot(runtime)
                start=time.perf_counter()
                events=[]
                def capture(event):
                    kind=event.get('type')
                    if kind=='message_update':
                        delta=event.get('assistantMessageEvent',{}).get('delta','')
                        if delta:events.append({'event':'text_delta','delta':delta,'t_ms':(time.perf_counter()-start)*1000})
                    elif kind in ('tool_execution_start','tool_execution_end'):
                        events.append({'event':kind,'t_ms':(time.perf_counter()-start)*1000,
                            **{key:event[key] for key in ('toolName','toolCallId','args','result','isError') if key in event}})
                # Only the utterance is sent. Review criteria and expectations stay outside the model input.
                row['attempted_turns']+=1
                result=None
                turn_errors=[]
                try:
                    result=client.ask(step['user'],timeout=timeout,on_event=capture)
                except Exception as error:
                    turn_errors.append(type(error).__name__+': '+str(error)[:400])
                generation_ms=(time.perf_counter()-start)*1000
                tools=[asdict(tool) for tool in result.tool_calls] if result else []
                # An exception may follow an already executed action. Preserve the receipt and
                # streamed prefix, without claiming the response completed successfully.
                if result is None:
                    tools=[{'name':r['name'],'args':r['arguments'],'is_error':r['is_error']}
                           for r in bridge.receipts]
                reply=result.text if result else ''.join(e['delta'] for e in events if e['event']=='text_delta')
                if result:turn_errors.extend(result.errors)
                after=state_snapshot(runtime)
                checks=runner.objective_checks(step.get('expect',{}),reply,tools,before,after)
                text_event=next((event for event in events if event['event']=='text_delta' and event['delta'].strip()),None)
                turn={'turn_id':str(index+1),'user':step['user'],'text':reply,'tools':tools,
                    'status':'failed' if turn_errors else 'completed',
                    'receipts':list(bridge.receipts),'checks':checks,'errors':turn_errors,
                    'events':events,'clock_id':f'local_turn_{index+1}',
                    'first_nonblank_text_ms':text_event['t_ms'] if text_event else None,
                    'total_ms':generation_ms,
                    'provider_timings':result.timings if result else {},'input_tokens':result.input_tokens if result else None,
                    'output_tokens':result.output_tokens if result else None,'state_before':before,'state_after':after,
                    'spoken_audio':None,'visible_expressions':None}
                row['turns'].append(turn)
                row['checks'].extend({**check,'turn_id':str(index+1)} for check in checks)
                row['completed_turns']+=int(not turn_errors)
                if turn_errors:
                    row['errors'].extend(turn_errors);row['status']='failed'
                save(directory/'sample.partial.json',row)
                if turn_errors:break
        except Exception as error:
            row['status']='failed';row['errors'].append(type(error).__name__+': '+str(error)[:400])
        finally:
            if client:
                try:client.close()
                except Exception as error:
                    message=type(error).__name__+': '+str(error)[:400]
                    row['cleanup_errors']=[message];row['errors'].append(message);row['status']='failed'
    save(directory/'sample.json',row)
    return row


def render(record,suite,directory):
    lookup={case['id']:case for case in suite['cases']}
    sections=[]
    for sample in record['samples']:
        case=lookup[sample['case_id']]
        criteria=''.join('<li>'+html.escape(str(item))+'</li>' for item in case.get('review_criteria',case.get('rubric',[])))
        turns=[]
        for turn in sample['turns']:
            failures=[check['name'] for check in turn['checks'] if check.get('passed') is False]
            turns.append('<p><b>You:</b> '+html.escape(turn['user'])+'</p><p><b>MIST:</b> '+html.escape(turn['text'])+'</p>'+
                '<details><summary>Tools and measurements</summary><pre>'+html.escape(json.dumps({
                    'first_text_ms':turn['first_nonblank_text_ms'],'total_ms':turn['total_ms'],
                    'receipts':turn['receipts'],'objective_failures':failures,'errors':turn['errors']},indent=2,ensure_ascii=False))+'</pre></details>')
        sections.append('<section><h2>'+html.escape(case.get('title',case['id']))+'</h2><small>'+html.escape(
            f"{case['id']} · {sample['status']} · {case['mode']}")+'</small><ul>'+criteria+'</ul>'+''.join(turns)+
            '<p>'+html.escape(sample.get('unsupported_reason','Meaning review is separate from transport and tool checks.'))+'</p></section>')
    counts=dict(Counter(sample['status'] for sample in record['samples']))
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>MIST · Conversation checks</title>
<style>body{max-width:960px;margin:30px auto;padding:0 22px;background:#f5f5ef;color:#263832;font:15px/1.6 system-ui}h1{font-size:23px}h2{font-size:17px}section{border-top:1px solid #cbd8d1;padding:20px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}a{color:#176f63}p{white-space:pre-wrap}small{color:#59655f}</style>
<h1>Conversation checks</h1><p>Actual replies from fresh text sessions. They use the selected voice model's prompt and tool setup, without audio or a display. Completed requests still need meaning review.</p>'''
    page+='<p>'+html.escape(json.dumps(counts))+'</p><p><a href="run.json">Raw results</a> · <a href="cases.frozen.json">Cases and review criteria</a></p>'
    page+=''.join(sections)+'</html>'
    (directory/'report.html').write_text(page,encoding='utf-8')
    save(directory/'summary.json',{'status_counts':counts,'cases':len(record['samples']),
         'objective_failures':sum(check.get('passed') is False for sample in record['samples'] for check in sample['checks']),
         'semantic_pass_rate':None,'human_naturalness':None,'limits':LIMITS})


def run(args,client_factory=production_client):
    suite,digest=runner.checked_suite(args.suite)
    suite_bytes=args.suite.read_bytes()
    if sha(suite_bytes)!=digest:raise ValueError('Suite changed while being loaded; use a stable file')
    cases=runner.select(suite,args.split,args.ids,args.limit)
    configuration=architecture(args.architecture)
    if args.repeats<1 or args.timeout<=0:raise ValueError('Positive repeats and timeout required')
    schedule=[(case,index+1) for case in cases for index in range(args.repeats)]
    random.Random(args.seed).shuffle(schedule)
    if not args.live:
        plan={'status':'planned','architecture':configuration,'suite_sha256':digest,
              'schedule':[{'case_id':case['id'],'repeat':repeat,'unsupported_reason':runner.unsupported_reason(case)} for case,repeat in schedule],
              'limits':LIMITS,'provider_calls':0}
        print(json.dumps(plan,indent=2,ensure_ascii=True));return 0
    directory=args.output.resolve();directory.mkdir(parents=True,exist_ok=False)
    (directory/'cases.frozen.json').write_bytes(suite_bytes)
    source_paths=[Path(__file__),HERE/'runner.py',HERE/'cascade_voice.py',HERE/'cerebras_client.py',
         BRAIN/'harness/eval_luna_conversations.py',BRAIN/'harness/codex_client.py',
         BRAIN/'duplex/live_studio.py',BRAIN/'duplex/runtime.py',BRAIN/'duplex/background.py',
         BRAIN/'duplex/conversation_policy.py',BRAIN/'duplex/persona.txt',
         BRAIN/'duplex/expression_policy.py',BRAIN/'duplex/expression_requests.py',
         BRAIN/'duplex/memory_requests.py',BRAIN/'duplex/motion_requests.py',BRAIN/'duplex/face_map.json']
    hashes={}
    for path in source_paths:
        relative=path.relative_to(ROOT);data=path.read_bytes();hashes[relative.as_posix()]=sha(data)
        target=directory/'sources'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    record={'manifest':{'created_utc':datetime.now(timezone.utc).isoformat(),'architecture':configuration,
             'suite_sha256':digest,'source_hashes':hashes,'seed':args.seed,'repeats':args.repeats,
             'timeout_s':args.timeout,'limits':LIMITS,'adapter':'production-foreground-text'},
             'schedule':[{'case_id':case['id'],'repeat':repeat} for case,repeat in schedule],
             'status':'running','samples':[]}
    save(directory/'run.json',record)
    for case,repeat in schedule:
        row=run_case(case,repeat,directory/'samples'/f"{case['id']}-r{repeat}",configuration,client_factory,args.timeout)
        record['samples'].append(row);save(directory/'run.json',record);render(record,suite,directory)
        print(json.dumps({'case':case['id'],'repeat':repeat,'status':row['status'],'semantic_pass':None}),flush=True)
    record['status']='finished';save(directory/'run.json',record)
    return int(any(sample['status']=='failed' for sample in record['samples']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',type=Path,default=HERE/'expectation_cases.json')
    parser.add_argument('--architecture',default='qwen-assist')
    parser.add_argument('--split',choices=['dev','validation','holdout','all'],default='dev')
    parser.add_argument('--ids');parser.add_argument('--limit',type=int)
    parser.add_argument('--repeats',type=int,default=1);parser.add_argument('--seed',type=int,default=240924)
    parser.add_argument('--timeout',type=float,default=45);parser.add_argument('--live',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.live and args.output is None:parser.error('--live requires a new --output directory')
    return run(args)


if __name__=='__main__':raise SystemExit(main())
