"""Paired low/high effort snapshots with fixed inputs and an unscored blind review."""
import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import random
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import reasoning_eval as evaluation
from experiment import schedule_pairs


def review(record, output, seed):
    lookup={(s['case_id'],s['repeat'],s['arm']):s for s in record['samples']}
    rng=random.Random(seed+1);answer_key={};sections=[]
    for index,block in enumerate(record['schedule']):
        key=f'pair-{index+1}';order=['baseline','candidate'];rng.shuffle(order)
        answer_key[key]={letter:arm for letter,arm in zip(['A','B'],order)}
        rows=[lookup.get((block['case_id'],block['repeat'],arm)) for arm in order]
        if not all(rows):continue
        payload=html.escape(json.dumps(rows[0]['model_input'],ensure_ascii=False,indent=2))
        columns=''.join('<article><h3>'+letter+'</h3><p>'+html.escape(row.get('text') or '[No response]')+'</p><small>'+html.escape(row['status'])+'</small></article>' for letter,row in zip(['A','B'],rows))
        sections.append(f'<section data-pair="{key}"><h2>{key}</h2><details><summary>Conversation and evidence</summary><pre>{payload}</pre></details><div class="answers">{columns}</div><label>More useful and correct <select><option value="">Unrated</option><option>A</option><option>B</option><option>Both adequate</option><option>Both wrong</option><option>Cannot judge</option></select></label><label>What supports that judgment?<textarea placeholder="Point to the misunderstanding, unsupported claim or successful repair."></textarea></label></section>')
    page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Reasoning comparison</title><style>body{max-width:1050px;margin:30px auto;padding:0 22px;background:#f6f6f1;color:#26322e;font:15px/1.6 system-ui}h1{font-size:22px}h2{font-size:17px}h3{font-size:16px}section{padding:22px 0;border-bottom:1px solid #ccd5ce}.answers{display:grid;grid-template-columns:1fr 1fr;gap:20px}article{background:white;padding:16px;border:1px solid #d2dbd4;border-radius:8px}pre{white-space:pre-wrap;font-size:12px}p{white-space:pre-wrap}label{display:block;margin:12px 0}textarea{display:block;width:95%;min-height:65px}button,select,textarea{font:inherit;padding:7px}small{color:#64716a}@media(max-width:650px){.answers{grid-template-columns:1fr}}</style><h1>Reasoning comparison</h1><p>Compare the answers against the full conversation and evidence. Model settings are hidden. These are text decisions, not voice-quality ratings. No answer has been marked correct automatically.</p>'''+''.join(sections)+'''<button id="save">Download ratings</button><script>document.getElementById('save').onclick=()=>{const ratings=[...document.querySelectorAll('section[data-pair]')].map(s=>({pair:s.dataset.pair,choice:s.querySelector('select').value,reason:s.querySelector('textarea').value}));const url=URL.createObjectURL(new Blob([JSON.stringify({version:1,ratings},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='reasoning-ratings.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};</script>'''
    (output/'review.html').write_text(page,encoding='utf-8')
    evaluation.save(output/'answer_key.private.json',answer_key)


def run(args,client_factory=evaluation.make_client):
    public,manifest=evaluation.load_suite(args.suite)
    cases=evaluation.select_cases(public,args.ids,args.families,args.limit)
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    raw=(evaluation.BRAIN/'duplex/persona.txt').read_bytes()
    prompt=raw.decode('utf-8').replace("Your voice is being converted to the owner's MIST voice.","Your words are spoken through the owner's MIST streaming TTS voice.")+evaluation.CASCADE_WRAPPER
    config={'provider':'cerebras','model':'gpt-oss-120b','timeout_s':args.timeout,'max_output_tokens':args.max_output_tokens,'concurrency':1,'tools':[]}
    schedule=schedule_pairs(cases,args.repeats,args.seed)
    record={'manifest':{'created_utc':datetime.now(timezone.utc).isoformat(),'suite_sha256':manifest['public_sha256'],'config':config,'baseline_effort':'low','candidate_effort':'high','repeats':args.repeats,'seed':args.seed,'live':args.live,'system_prompt_sha256':evaluation.sha(prompt.encode()),'meaning_score':None,'limits':['Development pilot; no held-out improvement claim.','Fixed prefixes, not adaptive conversations or acoustic evaluation.','Transport success is not semantic correctness.','Tool-bearing cases are unsupported.','Same completion cap includes provider reasoning tokens in both arms.']},'schedule':schedule,'samples':[]}
    evaluation.save(output/'model_cases.frozen.json',public);evaluation.save(output/'suite_manifest.frozen.json',manifest)
    (output/'system_prompt.frozen.txt').write_text(prompt,encoding='utf-8')
    source_hashes={}
    for path in (Path(__file__),HERE/'reasoning_eval.py',HERE/'reasoning_suite.py',HERE/'cerebras_client.py',HERE/'experiment.py',evaluation.BRAIN/'duplex/persona.txt'):
        relative=path.relative_to(evaluation.ROOT);target=output/'sources'/relative;target.parent.mkdir(parents=True,exist_ok=True);data=path.read_bytes();target.write_bytes(data);source_hashes[relative.as_posix()]=evaluation.sha(data)
    record['manifest']['source_hashes']=source_hashes
    lookup={c['id']:c for c in cases}
    evaluation.save(output/'run.json',record)
    for block in schedule:
        for arm in block['order']:
            folder=output/arm/(block['case_id']+'-r'+str(block['repeat']));folder.mkdir(parents=True)
            effective={**config,'reasoning':'low' if arm=='baseline' else 'high'}
            row=evaluation.evaluate_sample(lookup[block['case_id']],block['repeat'],folder,effective,prompt,live=args.live,client_factory=client_factory)
            row['arm']=arm;record['samples'].append(row)
            evaluation.save(folder/'sample.json',row);evaluation.save(output/'run.json',record)
            print(json.dumps({'case':row['case_id'],'arm':arm,'status':row['status'],'quality':'unrated'}),flush=True)
    record['status']='finished';evaluation.save(output/'run.json',record);review(record,output,args.seed)
    return 1 if any(s['status']=='failed' for s in record['samples']) else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--families',default='referent_repair,metacommunication,evidence_calibration');parser.add_argument('--ids');parser.add_argument('--limit',type=int)
    parser.add_argument('--repeats',type=int,default=1);parser.add_argument('--seed',type=int,default=2409)
    parser.add_argument('--timeout',type=float,default=45);parser.add_argument('--max-output-tokens',type=int,default=4096)
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    if args.timeout<=0 or args.max_output_tokens<=0:parser.error('Positive timeout and completion budget required')
    return run(args)


if __name__=='__main__':raise SystemExit(main())
