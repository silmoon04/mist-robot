"""Estimate list-price cost from retained provider usage, never from word counts."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / 'brain/results/architecture-cost-20260928'


def token_cost(usage, rate):
    """Completion usage already includes reasoning; never add it a second time."""
    if not rate or any(usage.get(k) is None for k in ('prompt_tokens', 'completion_tokens')):
        return None
    prompt, completion = usage['prompt_tokens'], usage['completion_tokens']
    if any(type(n) is not int or n < 0 for n in (prompt, completion)):
        raise ValueError('Expected nonnegative token counts')
    cached = (usage.get('prompt_tokens_details') or {}).get('cached_tokens', 0)
    if type(cached) is not int or not 0 <= cached <= prompt:
        raise ValueError('Cached tokens must be a subset of prompt tokens')
    input_rate, output_rate = rate.get('input_usd_per_million'), rate.get('output_usd_per_million')
    if input_rate is None or output_rate is None:
        return None
    # Unknown discounts get the ordinary input price, not a speculative saving.
    cached_rate = rate.get('cached_input_usd_per_million')
    if cached_rate is None:
        cached_rate = input_rate
    return ((prompt-cached)*input_rate + cached*cached_rate + completion*output_rate)/1_000_000


def trace_usage(path, prices):
    rows = [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
    roles = defaultdict(lambda: {'input_tokens': 0, 'output_tokens': 0, 'known_cost_usd': 0., 'records': 0,
                                 'unknown_usage_records': 0})
    outcomes, durations = Counter(), []
    completed_ids, started_ids = set(), set()
    tts_chars = 0
    reader_started = reader_finished = 0
    config = next((r['event']['architecture'] for r in rows if r.get('event', {}).get('type') == 'studio_session'), {})
    speaker_model = config.get('model')
    reader_model = config.get('affect_model')

    def account(role, model, usage):
        entry = roles[role]
        entry['model'] = model
        entry['records'] += 1
        amount = token_cost(usage or {}, prices.get(model))
        if amount is None:
            entry['unknown_usage_records'] += 1
            return
        entry['input_tokens'] += usage['prompt_tokens']
        entry['output_tokens'] += usage['completion_tokens']
        entry['known_cost_usd'] += amount

    for row in rows:
        event = row.get('event', {})
        if row.get('source') == 'server':
            if event.get('type') == 'debug_model':
                turn = event.get('turn_id')
                if event.get('phase') == 'thinking_started':
                    started_ids.add(turn)
                if event.get('phase') == 'thinking_finished' and turn not in completed_ids:
                    completed_ids.add(turn)
                    rounds = (event.get('timings') or {}).get('http_requests') or []
                    for request in rounds:
                        account('speaker', event.get('model', speaker_model), request.get('usage'))
                    if not rounds:
                        account('speaker', speaker_model, None)
            if event.get('type') == 'affect_decision':
                if event.get('phase') == 'started':
                    reader_started += 1
                if event.get('phase') == 'finished':
                    reader_finished += 1
                    trace = event.get('trace') or {}
                    outcome = event.get('outcome', 'unknown')
                    outcomes[outcome] += 1
                    account('reader', reader_model, {'prompt_tokens': trace.get('input_tokens'),
                                                    'completion_tokens': trace.get('output_tokens')})
                    durations.append(event.get('elapsed_ms'))
                    if outcome == 'applied_before_speech' and (event.get('decision') or {}).get('change'):
                        outcomes['applied_face_change'] += 1
        if row.get('source') == 'provider' and event.get('event') == 'tts_phrase':
            tts_chars += event.get('characters', 0)
    return {'trace_id': Path(path).parent.name, 'architecture': config.get('id'),
            'span_minutes': (max((r.get('elapsed_ms', 0) for r in rows), default=0) / 60000),
            'roles': dict(roles), 'speaker_started_turns': len(started_ids),
            'speaker_turns_with_completed_diagnostics': len(completed_ids),
            'speaker_turns_missing_complete_usage': len(started_ids-completed_ids),
            'reader_started': reader_started, 'reader_finished': reader_finished,
            'reader_outcomes': dict(outcomes), 'tts_submitted_characters': tts_chars,
            'cost_status': 'recorded-usage lower bound; interrupted or unfinished calls may be billed',
            'scope': 'Historical trace, not a controlled architecture comparison or provider invoice'}


def model_usage(path, prices):
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    manifest = json.loads(Path(path).with_name('manifest.json').read_text(encoding='utf-8'))
    architectures = manifest['architectures']
    samples = raw if isinstance(raw, list) else raw.get('results', raw.get('samples', []))
    groups = defaultdict(lambda: {'known_cost_usd': 0., 'input_tokens': 0, 'output_tokens': 0,
                                 'reader_cost_usd': 0., 'unknown_rounds': 0, 'attempted_turns': 0})
    for sample in samples:
        arm = sample['arm']
        model = architectures[arm]['model']
        group = groups[arm]
        for turn in sample.get('turns', []):
            group['attempted_turns'] += 1
            rounds = turn.get('rounds', [])
            if not rounds:
                group['unknown_rounds'] += 1
            for request in rounds:
                usage = request.get('usage') or {}
                cost = token_cost(usage, prices.get(model))
                if cost is None:
                    group['unknown_rounds'] += 1
                else:
                    group['known_cost_usd'] += cost
                    group['input_tokens'] += usage['prompt_tokens']
                    group['output_tokens'] += usage['completion_tokens']
            for reader in turn.get('reader', []):
                if reader.get('phase') != 'finished':
                    continue
                trace = reader.get('trace') or {}
                usage = {'prompt_tokens': trace.get('input_tokens'), 'completion_tokens': trace.get('output_tokens')}
                cost = token_cost(usage, prices.get(architectures[arm].get('affect_model')))
                if cost is None:
                    group['unknown_rounds'] += 1
                else:
                    group['known_cost_usd'] += cost
                    group['reader_cost_usd'] += cost
                    group['input_tokens'] += usage['prompt_tokens']
                    group['output_tokens'] += usage['completion_tokens']
    for group in groups.values():
        group['cost_per_1000_attempted_turns_usd'] = group['known_cost_usd']/group['attempted_turns']*1000 if group['attempted_turns'] else None
    return dict(groups)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pricing', type=Path, default=OUTPUT/'pricing.json')
    parser.add_argument('--trace', type=Path, action='append', default=[])
    parser.add_argument('--model-results', type=Path)
    parser.add_argument('--output', type=Path, default=OUTPUT/'costs.json')
    args = parser.parse_args()
    pricing = json.loads(args.pricing.read_text(encoding='utf-8-sig'))
    prices = pricing['cerebras']['models']
    report = {'currency': 'USD', 'pricing_date': pricing['retrieved_on'],
              'assumptions': 'Public list-price estimates before credits, subscriptions, tax or negotiated rates. Completion counts include reasoning.',
              'traces': [trace_usage(path, prices) for path in args.trace]}
    if args.model_results:
        report['model_benchmark'] = model_usage(args.model_results, prices)
    for trace in report['traces']:
        trace['tts_list_price_estimate_usd'] = trace['tts_submitted_characters']/1000*pricing['speech']['elevenlabs']['usd_per_1000_characters']
    # Explicit scenario, not an extrapolation from a short benchmark sample.
    report['illustrative_hour'] = {'assumptions': {'turns': 120, 'input_tokens_per_turn': 3000,
              'completion_tokens_per_turn': 250, 'tts_characters': 18000, 'stt_streamed_minutes': 60},
              'speaker_usd': {model: 120*token_cost({'prompt_tokens': 3000, 'completion_tokens': 250}, rate) for model, rate in prices.items()},
              'tts_usd': 18*pricing['speech']['elevenlabs']['usd_per_1000_characters'],
              'stt_regular_usd': 60*pricing['speech']['deepgram']['pay_as_you_go_regular_usd_per_minute']['monolingual']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
