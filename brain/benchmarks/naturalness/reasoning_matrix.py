"""Interleaved multi-condition reasoning snapshots; --live explicitly enables calls.

Conditions JSON is an array, or {"conditions": [...]}, containing objects with
id, provider, model and reasoning. A shared completion cap defaults to 4096.
Each case/repetition block runs every condition once in a balanced order. No
retries are made. Meaning is left ungraded; blind review hides settings/timing.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import html
import json
import math
from pathlib import Path
import random
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reasoning_eval as evaluation
from reasoning_suite import digest, model_payload

VERSION = '2026-09-24.1'


def validate_conditions(value):
    if isinstance(value, dict):
        if set(value) != {'conditions'}:
            raise ValueError('Condition document accepts only a conditions array')
        value = value['conditions']
    if not isinstance(value, list) or not 2 <= len(value) <= 8:
        raise ValueError('Provide between two and eight conditions')
    conditions, seen = [], set()
    for row in value:
        if not isinstance(row, dict) or set(row) != {'id', 'provider', 'model', 'reasoning'}:
            raise ValueError('Each condition needs exactly id, provider, model and reasoning; budgets are shared')
        cid = row['id']
        if not isinstance(cid, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', cid) or cid in seen:
            raise ValueError('Condition IDs must be unique safe names')
        if row['provider'] not in ('cerebras', 'codex'):
            raise ValueError('Provider must be cerebras or codex')
        if any(not isinstance(row[key], str) or not row[key].strip() for key in ('model', 'reasoning')):
            raise ValueError('Specify the exact verified model and reasoning setting')
        seen.add(cid)
        conditions.append(dict(row))
    return conditions


def schedule_matrix(cases, conditions, repeats=3, seed=2409):
    """Balance every condition's position within each complete N-block cycle.

    Case order is independently shuffled per repeat. Each block includes all
    conditions. Reversing alternate cycles also balances adjacent ordering over
    complete 2N-block cycles for the three-condition comparison. Per-case order
    is randomized by scheduling, not guaranteed balanced with arbitrary sizes.
    """
    if type(repeats) is not int or repeats < 1 or type(seed) is not int:
        raise ValueError('Repeats must be positive and seed must be an integer')
    if not cases or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Cases must be nonempty and unique')
    ids = [c['id'] for c in validate_conditions(conditions)]
    rng = random.Random(seed)
    rng.shuffle(ids)
    blocks = []
    for repeat in range(1, repeats + 1):
        ordered = list(cases)
        rng.shuffle(ordered)
        for case in ordered:
            index = len(blocks)
            cycle, offset = divmod(index, len(ids))
            base = ids if cycle % 2 == 0 else list(reversed(ids))
            order = base[offset:] + base[:offset]
            blocks.append({'block_id': f'block-{index + 1:04d}', 'case_id': case['id'],
                           'repeat': repeat, 'order': order})
    return blocks


def order_counts(schedule, conditions):
    counts = {c['id']: [0] * len(conditions) for c in conditions}
    for block in schedule:
        for position, cid in enumerate(block['order']):
            counts[cid][position] += 1
    return counts


def finite_nonnegative(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def timing_stats(values):
    values = sorted(v for v in values if finite_nonnegative(v))
    if not values:
        return {'count': 0, 'median_s': None, 'p90_s': None}
    offset = (len(values) - 1) * .9
    lo, hi = math.floor(offset), math.ceil(offset)
    p90 = values[lo] + (values[hi] - values[lo]) * (offset - lo)
    return {'count': len(values), 'median_s': statistics.median(values), 'p90_s': p90}


def latency_summary(record):
    result = {'version': VERSION, 'timing_scope': 'successful fixed-prefix text calls only; no audio latency',
              'semantic_quality': 'unrated', 'conditions': {},
              'limits': ['Timing counts exclude planned, unsupported, failed and malformed-timing samples.',
                         'Completed calls are not semantically correct by definition.',
                         'p90 is descriptive and unstable with small counts; repetitions share case context.']}
    for condition in record['manifest']['conditions']:
        rows = [s for s in record['samples'] if s['condition_id'] == condition['id']]
        successful = [s for s in rows if s['status'] == 'completed' and not s.get('errors') and not s.get('tools')]
        inconsistent = [s for s in successful if finite_nonnegative(s.get('ttft_s'))
                        and finite_nonnegative(s.get('total_s')) and s['ttft_s'] > s['total_s']]
        eligible = [s for s in successful if s not in inconsistent]
        result['conditions'][condition['id']] = {
            'configuration': condition, 'samples': len(rows),
            'status_counts': dict(Counter(s['status'] for s in rows)),
            'completed_without_errors': len(successful),
            'error_samples': sum(bool(s.get('errors')) or s['status'] == 'failed' for s in rows),
            'error_entries': sum(len(s.get('errors', [])) for s in rows),
            'unexpected_tool_samples': sum(bool(s.get('tools')) for s in rows),
            'invalid_timing_order_samples': len(inconsistent),
            'ttft': timing_stats([s.get('ttft_s') for s in eligible]),
            'total': timing_stats([s.get('total_s') for s in eligible]),
            'missing_or_invalid_ttft_in_completed': sum(not finite_nonnegative(s.get('ttft_s')) for s in successful),
            'missing_or_invalid_total_in_completed': sum(not finite_nonnegative(s.get('total_s')) for s in successful),
            'semantic_pass': None,
        }
    return result


def blind_review(record, output, seed):
    """Keep the lookup private. Review data and HTML contain no settings/timings."""
    lookup = {(s['case_id'], s['repeat'], s['condition_id']): s for s in record['samples']}
    rng = random.Random(seed ^ 0x745A)
    blocks = list(record['schedule'])
    rng.shuffle(blocks)
    comparisons, key = [], {}
    for block in blocks:
        if not all((block['case_id'], block['repeat'], cid) in lookup for cid in block['order']):
            continue
        order = list(block['order'])
        rng.shuffle(order)
        rid = f'comparison-{len(comparisons) + 1:04d}'
        answers, private = [], {}
        for index, cid in enumerate(order):
            label = chr(ord('A') + index)
            row = lookup[(block['case_id'], block['repeat'], cid)]
            answers.append({'label': label, 'text': row.get('text'),
                            'complete': row['status'] == 'completed' and not row.get('errors')})
            private[label] = {'condition_id': cid, 'sample_id': row['sample_id']}
        row = lookup[(block['case_id'], block['repeat'], order[0])]
        comparisons.append({'review_id': rid, 'input': row['model_input'], 'answers': answers})
        key[rid] = {'case_id': block['case_id'], 'repeat': block['repeat'], 'answers': private}
    data = {'schema_version': 1, 'kind': 'blinded_unrated_text_comparison', 'comparisons': comparisons,
            'note': 'Condition identity and latency are omitted. Response wording may still reveal a model identity.'}
    evaluation.save(output / 'review_inputs.blind.json', data)
    evaluation.save(output / 'condition_key.private.json', {'schema_version': 1, 'comparisons': key})
    sections = []
    for comparison in comparisons:
        context = html.escape(json.dumps(comparison['input'], ensure_ascii=False, indent=2))
        cards, choices = [], []
        for answer in comparison['answers']:
            label = answer['label']
            text = html.escape(answer['text'] if answer['text'] is not None else '[No answer]')
            state = '' if answer['complete'] else '<p class="notice">Incomplete or unavailable answer.</p>'
            cards.append(f'<article><h3>{label}</h3><div class="response">{text}</div>{state}'
                         f'<label>Correctness and usefulness <select data-answer="{label}"><option value="">Unrated</option>'
                         '<option value="1">1 - misses the point</option><option value="2">2</option>'
                         '<option value="3">3 - partly useful</option><option value="4">4</option>'
                         '<option value="5">5 - correct and useful</option><option value="unclear">Unclear</option></select></label></article>')
            choices.append(f'<option>{label}</option>')
        rid = comparison['review_id']
        sections.append(f'<section data-review="{rid}"><h2>{rid}</h2><details open><summary>Conversation and evidence</summary><pre>{context}</pre></details>'
                        '<div class="answers">' + ''.join(cards) + '</div><label>Preferred answer <select data-choice><option value="">Unrated</option>' + ''.join(choices) +
                        '<option>Tie</option><option>All inadequate</option><option>Unclear</option></select></label>'
                        '<label>Evidence for your judgment<textarea data-note></textarea></label></section>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Response comparison</title>
<style>body{margin:30px auto;max-width:1200px;padding:0 20px;background:#f5f5f0;color:#25322e;font:15px/1.55 system-ui}h1{font-size:22px}h2{font-size:17px}h3{margin-top:0}section{padding:24px 0;border-bottom:1px solid #c8d1ca}.answers{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}article{background:white;border:1px solid #d6ded8;border-radius:6px;padding:16px}.response,pre{white-space:pre-wrap;overflow-wrap:anywhere}pre{font-size:12px}label{display:block;margin-top:16px}textarea{display:block;width:96%;min-height:65px}select,button,textarea{font:inherit;padding:7px}.notice{font-size:13px;color:#655a49}</style>
<h1>Response comparison</h1><p>Judge each answer against the full conversation and evidence. Settings are hidden. This reviews text reasoning, not voice quality. No correctness score has been assigned.</p>''' + ''.join(sections) + '''
<button id="download">Download ratings</button><script>
document.getElementById('download').onclick=()=>{const ratings=[...document.querySelectorAll('section[data-review]')].map(s=>({review_id:s.dataset.review,choice:s.querySelector('[data-choice]').value,ratings:Object.fromEntries([...s.querySelectorAll('[data-answer]')].map(e=>[e.dataset.answer,e.value])),evidence:s.querySelector('[data-note]').value}));const u=URL.createObjectURL(new Blob([JSON.stringify({schema_version:1,ratings},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download='response-ratings.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};
</script></html>'''
    (output / 'review.html').write_text(page, encoding='utf-8')


def freeze_sources(output):
    paths = [Path(__file__), HERE / 'test_reasoning_matrix.py', HERE / 'reasoning_eval.py',
             HERE / 'reasoning_suite.py', HERE / 'cerebras_client.py',
             evaluation.BRAIN / 'harness/codex_client.py', evaluation.BRAIN / 'harness/pi_client.py',
             evaluation.BRAIN / 'duplex/persona.txt']
    hashes = {}
    for path in paths:
        relative = path.relative_to(evaluation.ROOT)
        raw = path.read_bytes()
        target = output / 'sources' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        hashes[relative.as_posix()] = evaluation.sha(raw)
    return hashes


def run(args, *, client_factory=evaluation.make_client):
    if args.repeats < 1 or args.timeout <= 0 or args.max_output_tokens < 1:
        raise ValueError('Repeat count, timeout and shared token cap must be positive')
    conditions = validate_conditions(args.condition_values)
    public, manifest = evaluation.load_suite(args.suite)
    cases = evaluation.select_cases(public, args.ids, args.families, args.limit)
    schedule = schedule_matrix(cases, conditions, args.repeats, args.seed)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    persona = (evaluation.BRAIN / 'duplex/persona.txt').read_bytes()
    prompt = persona.decode('utf-8').replace("Your voice is being converted to the owner's MIST voice.",
        "Your words are spoken through the owner's MIST streaming TTS voice.") + evaluation.CASCADE_WRAPPER
    configs = {c['id']: {k: c[k] for k in ('provider', 'model', 'reasoning')} | {
        'timeout_s': args.timeout, 'max_output_tokens': args.max_output_tokens, 'concurrency': 1,
        'new_session_per_sample': True, 'tools': [], 'retry_policy': 'none'} for c in conditions}
    record = {'manifest': {'schema_version': 1, 'version': VERSION, 'adapter': 'reasoning-matrix-text',
        'created_utc': datetime.now(timezone.utc).isoformat(), 'live': args.live,
        'conditions': conditions, 'effective_configs': configs, 'suite_sha256': manifest['public_sha256'],
        'selected_case_ids': [c['id'] for c in cases], 'repeats': args.repeats, 'seed': args.seed,
        'planned_samples': len(schedule) * len(conditions), 'source_hashes': freeze_sources(output),
        'system_prompt_sha256': evaluation.sha(prompt.encode('utf-8')), 'persona_raw_sha256': evaluation.sha(persona),
        'input_hashes': {c['id']: digest(model_payload(c)) for c in cases},
        'submission_hashes': {c['id']: evaluation.sha(evaluation.prompt_for(c).encode('utf-8')) for c in cases},
        'condition_position_counts': order_counts(schedule, conditions), 'semantic_quality': 'unrated',
        'limits': ['Fixed-prefix decisions, not closed-loop conversations or audio.',
                   'Each sample constructs a fresh client and session. Calls are sequential, interleaved by paired block.',
                   'No matrix retries or replacement samples; provider failures and partial text are retained.',
                   'No private oracles are opened or submitted. Tool-bearing cases remain unsupported.',
                   'The common completion cap includes reasoning where the provider counts it that way.',
                   'Provider adapters may impose different host/output instructions; actual backend metadata is retained.',
                   'Model and tool execution status never implies semantic correctness.']},
        'status': 'running' if args.live else 'planning', 'schedule': schedule, 'samples': []}
    evaluation.save(output / 'model_cases.frozen.json', public)
    evaluation.save(output / 'suite_manifest.frozen.json', manifest)
    evaluation.save(output / 'conditions.frozen.json', conditions)
    (output / 'system_prompt.frozen.txt').write_text(prompt, encoding='utf-8')
    (output / 'persona.raw.txt').write_bytes(persona)
    evaluation.save(output / 'run.json', record)
    lookup = {c['id']: c for c in cases}
    try:
        for block in schedule:
            for position, cid in enumerate(block['order']):
                case = lookup[block['case_id']]
                sample_id = f'{block["block_id"]}-{cid}'
                folder = output / 'samples' / sample_id
                folder.mkdir(parents=True)
                evaluation.save(folder / 'config.json', configs[cid])
                try:
                    row = evaluation.evaluate_sample(case, block['repeat'], folder, configs[cid], prompt,
                        live=args.live, client_factory=client_factory)
                except Exception as error:
                    row = {'case_id': case['id'], 'repeat': block['repeat'], 'family': case['family'],
                        'model_input': model_payload(case), 'model_input_sha256': digest(model_payload(case)),
                        'status': 'failed', 'text': None, 'tools': [], 'quality': 'unrated', 'semantic_pass': None,
                        'errors': ['Sample adapter: ' + type(error).__name__ + ': ' + str(error)[:700]]}
                row.update(sample_id=sample_id, condition_id=cid, order_position=position, block_id=block['block_id'])
                row['execution'] = {'model_status': row['status'],
                    'tool_contract': 'unexpected_calls' if row.get('tools') else
                        'no_calls_observed' if row['status'] == 'completed' else 'unmeasured',
                    'semantic_quality': 'unrated'}
                record['samples'].append(row)
                evaluation.save(folder / 'sample.json', row)
                evaluation.save(output / 'run.json', record)
                print(json.dumps({'sample': sample_id, 'case': case['id'], 'condition': cid,
                                  'status': row['status'], 'semantic_quality': 'unrated'}), flush=True)
        record['status'] = 'finished' if args.live else 'planned'
    except BaseException:
        record['status'] = 'interrupted'
        raise
    finally:
        record['status_counts'] = dict(Counter(s['status'] for s in record['samples']))
        evaluation.save(output / 'run.json', record)
        evaluation.save(output / 'latency-summary.json', latency_summary(record))
        blind_review(record, output, args.seed)
    return 1 if any(s['status'] == 'failed' for s in record['samples']) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--conditions', type=Path, help='JSON file containing the condition array.')
    source.add_argument('--condition', action='append', help='Repeat a JSON object with id/provider/model/reasoning.')
    parser.add_argument('--families'); parser.add_argument('--ids'); parser.add_argument('--limit', type=int)
    parser.add_argument('--repeats', type=int, default=3); parser.add_argument('--seed', type=int, default=2409)
    parser.add_argument('--timeout', type=float, default=45)
    parser.add_argument('--max-output-tokens', type=int, default=4096)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args(argv)
    args.condition_values = json.loads(args.conditions.read_text(encoding='utf-8')) if args.conditions else [json.loads(c) for c in args.condition]
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
