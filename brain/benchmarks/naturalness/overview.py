"""Build a small local index of cases, evidence and the first calibration."""
import argparse
import html
import json
from pathlib import Path

from runner import checked_suite, unsupported_reason, HERE


def build(output, experiment, suite_path=HERE / 'cases.json'):
    suite, digest = checked_suite(suite_path)
    summaries = [json.loads((experiment / arm / 'summary.json').read_text(encoding='utf-8')) for arm in ('baseline', 'candidate')]
    runs = [json.loads((experiment / arm / 'run.json').read_text(encoding='utf-8')) for arm in ('baseline', 'candidate')]
    relative = experiment.relative_to(output.parent).as_posix()
    rows = ''
    for name, label in [('model_ttft_ms', 'First text'), ('first_phrase_ms', 'First phrase'), ('first_tool_ms', 'First tool request')]:
        values = [s['metrics'][name] for s in summaries]
        rows += '<tr><td>'+label+'</td>'+''.join('<td>'+f"{v['median']/1000:.2f} s"+'</td>' for v in values)+'</tr>'
    cases = ''
    for c in suite['cases']:
        reason = unsupported_reason(c)
        badge = 'Text runnable' if reason is None else c['mode'].replace('_', ' ') + ' / fixture needed'
        turns = ''.join('<p><b>You</b> '+html.escape(t['user'])+'</p>' for t in c['turns'])
        if not turns:
            turns = ''.join('<p>'+str(t['at_ms'])+' ms · '+html.escape(t['type'])+' '+html.escape(t.get('text',''))+'</p>' for t in c.get('timeline', []))
        rubric = ''.join('<li>'+html.escape(r)+'</li>' for r in c['rubric'])
        cases += '<details class="case" data-search="'+html.escape((c['title']+' '+c['category']+' '+c['split']+' '+c['mode']).casefold(), quote=True)+'"><summary>'+html.escape(c['title'])+'<small>'+html.escape(c['split']+' · '+c['category']+' · '+badge)+'</small></summary>'+turns+'<ul>'+rubric+'</ul>'+(('<p class="muted">'+html.escape(reason)+'</p>') if reason else '')+'</details>'
    turns = sum(len(s['turns']) for r in runs for s in r['samples'])
    failures = sum(sum(x.get('passed') is False for x in s['checks']) for r in runs for s in r['samples'])
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>MIST benchmark</title><style>body{max-width:980px;padding:24px;margin:20px auto;font:16px/1.6 system-ui;color:#20312f;background:#f5f4ef}h1{font-size:24px}h2{font-size:19px;margin-top:32px}a{color:#176653}nav{display:flex;gap:24px;flex-wrap:wrap}.muted,small{color:#627269;font-size:14px}small{display:block}table{border-collapse:collapse;width:100%;max-width:640px}td,th{text-align:left;border-bottom:1px solid #ccd4cc;padding:10px}details{border-bottom:1px solid #d2d9d1;padding:14px 0}summary{cursor:pointer}input{box-sizing:border-box;width:100%;padding:12px;border:1px solid #b8c7bd;border-radius:6px;font:inherit}code{font-size:13px}#count{font-size:14px}.box{background:white;border:1px solid #d2d9d1;border-radius:10px;padding:18px;margin:20px 0}</style><h1>MIST benchmark</h1>'''
    page += f'<nav><a href="{relative}/review/review.html">Blind comparison</a><a href="{relative}/baseline/report.html">Run A</a><a href="{relative}/candidate/report.html">Run B</a><a href="{relative}/comparison.json">Paired metrics</a><a href="cases.json" download>Download cases</a></nav>'
    page += '<div class="box"><b>72 scenarios</b><p>42 text cases run now. Four further text cases need special fixtures; 24 need timed audio and two need session resets. None of those missing conditions count as passed.</p></div>'
    page += f'<h2>First calibration</h2><p>{turns} real Luna turns, four scenarios, two repetitions per arm. Both arms used the same settings. This checks variation; it does not demonstrate an improvement.</p><table><tr><th>Median</th><th>Run A</th><th>Run B</th></tr>{rows}</table><p class="muted">Backend text timing only. Audio onset, interruption quality and human ratings are still unmeasured. This sample is too small for reliable tail estimates.</p>'
    page += f'<p>{failures} failed tool-delivery checks remain in the results. In each, Luna requested curious correctly but the application rejected “no special variation”. A failed application call is distinct from an incorrect model choice.</p>'
    page += '<h2>What counts as better</h2><p>Correct tasks and history; appropriate responses to emotion and context; fewer false interruptions; quicker useful responses; less effort for the person talking. Rate complete exchanges, allow ties, and keep voice and expression judgments separate from text.</p><h2>Cases</h2><input id="search" aria-label="Filter cases" placeholder="Filter by topic, category, mode or split"><p id="count">72 cases</p>'+cases
    page += '<p class="muted">Visible dev, validation and holdout labels are not a secret test set. Freeze cases before comparison; do not tune against the held-out results and keep calling them unseen.</p><small>Case SHA256: '+digest+'</small><script>const input=document.getElementById("search"),items=[...document.querySelectorAll(".case")];input.oninput=()=>{const q=input.value.toLowerCase();let n=0;for(const e of items){e.hidden=!e.dataset.search.includes(q);if(!e.hidden)n++}document.getElementById("count").textContent=n+" cases"};</script></html>'
    output.write_text(page, encoding='utf-8')
    (output.parent/'cases.json').write_bytes(suite_path.read_bytes())


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    build(a.output, a.experiment)
