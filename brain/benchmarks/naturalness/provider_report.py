"""Readable provider comparison with all observed timing and failed checks retained."""
import argparse
from collections import Counter
import html
import json
from pathlib import Path
import shutil

from metrics import distribution, score_sample
from runner import HERE, checked_suite, load, save, unsupported_reason

LABELS = {'baseline':'Luna / Codex', 'candidate':'GPT-OSS-120B / Cerebras'}
METRICS = [('model_ttft_ms','First text'), ('first_phrase_ms','First phrase'), ('first_tool_ms','First tool request')]


def stats(run):
    scores = [score_sample(s) for s in run['samples']]
    turns = [t for s in run['samples'] for t in s['turns']]
    return {'conversations':len(scores), 'turns':len(turns),
            'status_counts':dict(Counter(s['status'] for s in scores)),
            'failed_check_turns':sum(any(c['passed'] is False for c in t['checks']) for t in turns),
            'failed_checks':sum(c['passed'] is False for t in turns for c in t['checks']),
            'tool_calls':sum(len(t['tools']) for t in turns),
            'rejected_calls':sum(bool(c.get('is_error')) for t in turns for c in t['tools']),
            'all_observed':{name:distribution(v for s in scores for v in s['metric_observations'][name]) for name,_ in METRICS},
            'sampling':'All valid observed turn spans, including turns with failed checks. Missing spans are not zero. No claim of task success.'}


def annotation(case_id, arm, turn_id, check):
    if case_id.endswith('.terse') and turn_id=='2' and check=='contains_any':
        return 'Scorer false negative: a nonbreaking hyphen in fifty-six. The arithmetic answer is correct.'
    if case_id.endswith('.conditional_memory') and check=='required_tool:recall':
        return 'Overstrict contract: the user asked what they had requested in this conversation. Accurate conversation recall can answer without a storage read.'
    if case_id.endswith(('.exact_face','.face_default_control')) and check=='no_rejected_model_tool':
        return 'Inspect the receipt: the known plain-variation guard can reject a valid curious call. A rejected call alone does not identify a model error.'
    return ''


def build(root):
    dest = root/'providers'
    dest.mkdir(exist_ok=True)
    parts, failures, aggregate = [], [], {}
    for folder, title in [('cerebras_comparison','Repeated baseline cases'), ('cerebras_expansion','New scenario pilot')]:
        exp = root/folder
        experiment = load(exp/'run.json')
        if experiment['status'] != 'finished':
            raise ValueError('Cannot publish unfinished experiment: '+folder)
        runs = {arm:load(exp/arm/'run.json') for arm in LABELS}
        summary = {arm:stats(r) for arm,r in runs.items()}
        for arm in LABELS:
            revised=exp/arm/'checks.regraded.json'
            if revised.exists():
                summary[arm]['regraded_failed_checks']=stats(load(revised))['failed_checks']
        aggregate[folder] = summary
        parts.append(f'<section><h2>{title}</h2><p>{len(runs["baseline"]["manifest"]["selected_case_ids"])} cases, {runs["baseline"]["manifest"]["repeats"]} repetitions per backend. Alternating order; fresh history for each conversation.</p><div class="scroll"><table><thead><tr><th>Observed median</th><th>Luna</th><th>Cerebras</th></tr></thead><tbody>')
        for key,label in METRICS:
            parts.append('<tr><td>'+label+'</td>')
            for arm in LABELS:
                d=summary[arm]['all_observed'][key]
                value=f'{d["median"]/1000:.3f} s' if d['median'] is not None else 'Unmeasured'
                parts.append(f'<td>{value}<small>{d["count"]} observed turns</small></td>')
            parts.append('</tr>')
        for field,label in [('turns','Completed turn records'),('failed_check_turns','Turns with a failed raw check'),('failed_checks','Failed raw checks'),('tool_calls','Tool calls'),('rejected_calls','Rejected calls')]:
            parts.append('<tr><td>'+label+'</td>'+''.join(f'<td>{summary[a][field]}</td>' for a in LABELS)+'</tr>')
        if all('regraded_failed_checks' in summary[a] for a in LABELS):
            parts.append('<tr><td>Failed checks after hyphen correction</td>'+''.join(f'<td><a href="../{folder}/{a}/checks.regraded.json">{summary[a]["regraded_failed_checks"]}</a></td>' for a in LABELS)+'</tr>')
        parts.append(f'</tbody></table></div><p class="note">These timings include incorrect replies. Tool timing covers only turns that called a tool; the two tool denominators differ. This is a small local sample, not a reliable tail-latency estimate.</p><nav><a href="../{folder}/review/review.html">Blind transcript review</a><a href="../{folder}/baseline/report.html">Luna transcripts</a><a href="../{folder}/candidate/report.html">Cerebras transcripts</a><a href="../{folder}/comparison.json">Paired case statistics</a></nav></section>')
        for arm,run in runs.items():
            for sample in run['samples']:
                for turn in sample['turns']:
                    bad=[c for c in turn['checks'] if c['passed'] is False]
                    if not bad:
                        continue
                    item={'experiment':folder,'arm':arm,'case_id':sample['case_id'],'repeat':sample['repeat'],'turn_id':turn['turn_id'],
                          'failed_checks':[{**c,'review_note':annotation(sample['case_id'],arm,turn['turn_id'],c['name'])} for c in bad],
                          'review_status':'Agent triage; raw records unchanged, not a human naturalness rating'}
                    failures.append(item)
                    parts.append('<details class="failure"><summary>'+html.escape(f'{LABELS[arm]} · {sample["case_id"].split(".")[-1]} · repeat {sample["repeat"]}, turn {turn["turn_id"]}')+'</summary><p><b>You</b> '+html.escape(turn['user'])+'</p><p><b>MIST</b> '+html.escape(turn['text'])+'</p><ul>'+''.join('<li>'+html.escape(c['name'])+(' <span class="note">'+html.escape(c['review_note'])+'</span>' if c['review_note'] else '')+'</li>' for c in item['failed_checks'])+'</ul><details><summary>Tools and receipts</summary><pre>'+html.escape(json.dumps({'tools':turn['tools'],'receipts':turn['receipts']},indent=2,ensure_ascii=False))+'</pre></details></details>')
    suite,digest=checked_suite(HERE/'cases_v2.json')
    supported=sum(unsupported_reason(c) is None for c in suite['cases'])
    save(dest/'observations.json',aggregate)
    save(dest/'failure_triage.json',failures)
    shutil.copyfile(HERE/'cases_v2.json',dest/'cases_v2.json')
    shutil.copyfile(HERE/'EXPANSION.md',dest/'EXPANSION.md')
    workers=load(root.parent/'cerebras_20260923/research/reviews.json')
    # Model outputs are evidence, including their original punctuation.
    save(dest/'research_reviews.json',workers)
    evidence={'suite_sha256':digest,'workers':[{'worker':r['worker'],'model':r['requested_model'],'status':r['status'],'elapsed_s':r['elapsed_s']} for r in workers]}
    save(dest/'research_provenance.json',evidence)
    audit_path=root.parent/'cerebras_20260923/audit/reviews.json'
    if audit_path.exists():
        shutil.copyfile(audit_path,dest/'audit_reviews.json')
    cases=''
    for c in suite['cases']:
        reason=unsupported_reason(c)
        new='.v2.' in c['id']
        query=(c['id']+' '+c['title']+' '+c['category']+' '+c['mode']+' '+('new' if new else 'original')).lower()
        cases+='<details class="case" data-search="'+html.escape(query,quote=True)+'"><summary>'+html.escape(c['title'])+(' <small>New</small>' if new else '')+'</summary><p class="note">'+html.escape(c['id']+' · '+c['mode']+' · '+c['split'])+'</p><p>'+html.escape(reason or 'Runnable text case. Human judgments remain separate.')+'</p><ol>'+''.join('<li>'+html.escape(t['user'])+'</li>' for t in c.get('turns',[]))+'</ol><ul>'+''.join('<li>'+html.escape(v)+'</li>' for v in c['rubric'])+'</ul>'
        if c.get('paired_control'):
            cases+='<p><b>Matched control</b> '+html.escape(c['paired_control'])+'</p>'
        if c.get('measurement_plan'):
            cases+='<pre>'+html.escape(json.dumps(c['measurement_plan'],indent=2))+'</pre>'
        cases+='</details>'
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>MIST provider tests</title><style>
    *{box-sizing:border-box}body{max-width:1000px;margin:24px auto;padding:20px 24px 60px;background:#f6f5f0;color:#27362f;font:16px/1.55 system-ui}h1{font-size:26px;font-weight:650}h2{font-size:20px;margin-top:34px}a{color:#156350}nav{display:flex;gap:10px 24px;flex-wrap:wrap;margin:16px 0}.note,small{color:#626d67;font-size:14px}td small{display:block}table{border-collapse:collapse;width:100%;max-width:780px}th,td{text-align:left;padding:12px;border-bottom:1px solid #d7ddd5}th{font-weight:600}.scroll{overflow-x:auto}details{border-bottom:1px solid #d7ddd5;padding:13px 0}summary{cursor:pointer}pre{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere;background:#efeee7;padding:12px}input{width:100%;font:inherit;padding:12px;border-radius:6px;border:1px solid #aebeb1;background:white}.notice{padding:18px 22px;background:#fff;border-left:4px solid #407566;margin:24px 0}li{margin:6px 0}.failure{font-size:14px}section{margin-bottom:20px}button{font:inherit;padding:7px 12px;background:#edf0e7;border:1px solid #b4c1b5;border-radius:5px;cursor:pointer}</style>
    <header><nav><a href="../">Calibration</a><a href="#cases">Scenarios</a><a href="cases_v2.json" download>Download cases</a><a href="EXPANSION.md" download>Test plan</a><a href="research_reviews.json" download>Research reviews</a></nav><h1>Luna and Cerebras</h1><p>Same MIST persona and application tools. Low reasoning, 1024-token completion cap, one live trial at a time. Live voice settings are unchanged.</p></header>
    <div class="notice"><b>Text is faster on Cerebras in this pilot.</b><p>It also missed both blue-colour corrections and both fresh battery reads in the repeated cases. Luna attempted an unwanted memory write and sometimes started background analysis unnecessarily. Both hit the same application guard when requesting a plain curious face.</p><details><summary>Scoring corrections and limits</summary><p>Two correct arithmetic answers were marked wrong because of a nonbreaking hyphen. The scorer is fixed; separate derived files show the correction and preserve the original checks. An accurate answer from conversation history failed the recall-tool requirement; that tool-use check remains visible, with a note.</p><p>No audio was synthesized here. Speech latency, interruption quality, rendered expressions and human preferences remain unmeasured. Prompt wrappers and reasoning/token-limit semantics differ between providers; this compares the complete text backends.</p></details></div>
    <details><summary>What the new scenarios exposed</summary><p>When pressed for a body-battery number, Cerebras repeated a stale phone reading without retaining its source and age limits. Luna refused that substitution. Both guessed degrees for an ambiguous phone-pan request. Luna also attempted a pan during a design-only discussion; the guard rejected it. These are agent-reviewed observations, not human ratings.</p><p>The valid half-degree-left clarification was rejected by the request guard on both backends. No physical movement occurred. Read receipts alongside tool calls: a successful call can still return a refused or preview-only result.</p></details>
    <details><summary>Independent audit and adapter recovery</summary><p>A further Luna transcript audit and Sol adapter audit are retained below. Their proposals need checking: the Luna audit initially treated the curious preset as unavailable, while the paired control shows that the wording guard causes the rejection.</p><p>After the measured runs, recovery tests found and closed a path that could submit incomplete tool history on a follow-up. Failed sessions now require an explicit reset, and provisional streamed text is retained in the error record. Turn deadlines are cooperative; an in-flight local tool is not forcibly cancelled. Frozen source copies show the implementation actually measured.</p><a href="audit_reviews.json">Audit records</a></details>'''
    page+=''.join(parts)
    page+=f'<section id="cases"><h2>{len(suite["cases"])} scenarios</h2><p>{supported} runnable text cases; {len(suite["cases"])-supported} require missing fixtures, timed audio or session resets. Eighteen additions came from four Luna and two Sol reviews, then were edited for observable criteria. The original 72 cases are preserved.</p><nav><a href="research_provenance.json">Worker records</a><a href="failure_triage.json">Failure notes</a><a href="observations.json">Observed timing data</a></nav><p class="note">Matched controls describe planned variations; they have not all been executed. All additions are visible development cases. The older holdout labels do not make those cases secret.</p><label for="filter">Find a scenario</label><input id="filter" placeholder="Try new, memory, correction or timed_audio"><p id="count">90 cases</p>'+cases+'</section>'
    page+='''<script>const field=document.getElementById('filter'),rows=[...document.querySelectorAll('.case')];field.oninput=()=>{let count=0;for(const row of rows){row.hidden=!row.dataset.search.includes(field.value.toLowerCase());if(!row.hidden)count++}document.getElementById('count').textContent=count+' cases'};</script></html>'''
    (dest/'index.html').write_text(page,encoding='utf-8')
    # Keep the older calibration intact and add a route to this separate experiment.
    index=root/'index.html'
    old=index.read_text(encoding='utf-8')
    link='<a href="providers/">Luna / Cerebras comparison</a>'
    if link not in old:
        index.write_text(old.replace('<nav>','<nav>'+link,1),encoding='utf-8')
    return aggregate


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(build(a.root),indent=2))
