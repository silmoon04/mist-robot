"""Measure Luna text/tool latency separately from speech and provider audio."""
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time

BRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN))
sys.path.insert(0, str(BRAIN / 'harness'))
from codex_client import CodexClient
from duplex.native import choose_binary
from duplex.runtime import RobotRuntime, specs
from duplex.phrasing import next_phrase

OUTPUT = BRAIN / 'results/luna_latency_20260922'
BASELINE = [
    ('greeting', 'Hey MIST, how are you?'),
    ('tired', 'I am exhausted today. No advice, just keep me company.'),
    ('success', 'The printed leg fits perfectly now.'),
    ('correction', 'Just to be clear, printed and fitted, not walking yet.'),
    ('playful', 'Give me one very dry robot joke.'),
    ('casual', 'What colour would you choose for your feet?'),
    ('explain', 'Why do printed parts tend to break between layers? Explain in two short sentences.'),
    ('sensor', 'What is the robot battery reading right now?'),
    ('face', 'Show your happy expression, variation 1, briefly.'),
    ('calm', 'Thanks. Can we just sit quietly for a bit?'),
    ('memory', 'Remember this: no jokes when I am tired.'),
    ('recall', 'What did I ask you to remember?'),
]
PAIRS = [
    ('greeting', 'Hey MIST, how are you?'),
    ('gentle', 'Rough day. I want a little company, no advice.'),
    ('playful', 'Give me one short, dry joke about your robot feet.'),
    ('explain', 'Why do printed parts tend to break between layers? Explain in two short sentences.'),
    ('sensor', 'What is the robot battery reading right now?'),
    ('face', 'Show your curious expression, variation 0, briefly.'),
    ('stop', 'Freeze. Stop the robot now.'),
    ('memory', 'Remember this exact preference: no jokes when I am tired.'),
]


class Bridge:
    def __init__(self, runtime):
        self.runtime = runtime

    def request(self, method, params, **kwargs):
        if method != 'call':
            raise ValueError('Only local application calls are available')
        try:
            result = self.runtime.call(params['name'], params['arguments'])
            return {'isError': result.get('status') == 'refused', 'result': {
                'content': [{'type': 'text', 'text': json.dumps(result)}]}}
        except (ValueError, TypeError, KeyError) as error:
            return {'isError': True, 'result': {'content': [{'type': 'text', 'text': str(error)}]}}

    def close(self):
        pass


def rounded(value):
    return None if value is None else round(value, 4)


def summary(rows):
    result = {'turns': len(rows), 'errors': sum(bool(x['errors']) for x in rows)}
    for key in ('first_text_s', 'first_tool_s', 'first_speakable_phrase_s', 'total_s'):
        values = sorted(x[key] for x in rows if x[key] is not None)
        result[key] = None if not values else {
            'n': len(values), 'median': rounded(statistics.median(values)),
            'min': min(values), 'max': max(values),
            'p90_nearest_rank': values[max(0, __import__('math').ceil(.9*len(values))-1)]}
    return result


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    choose_binary()
    persona = (BRAIN / 'duplex/persona.txt').read_text(encoding='utf-8')
    prompt = persona + '\n\nFor this text-only timing test you are the backing Codex agent. Use the supplied application tools directly instead of delegating to yourself. No microphone, audio playback or physical motors are connected. There is no background worker in this timing test. Answer ordinary social chat directly without a tool.'
    (OUTPUT / 'persona_snapshot.txt').write_text(prompt, encoding='utf-8')
    report = {
        'model': 'gpt-6-luna', 'reasoning': 'low', 'created_at': time.time(),
        'persona_sha256': hashlib.sha256(persona.encode()).hexdigest(),
        'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
        'production_files_modified': [], 'baseline': [], 'matched_tier_trials': [],
        'limits': ['Text-only Luna backing-agent timings, not front realtime voice or end-to-end speech latency.',
                   'First speakable phrase uses the production next_phrase splitter on actual streamed text deltas.',
                   'Baseline is one continuous conversation; tier comparisons use fresh ephemeral sessions and alternating order.',
                   'Tool calls use the production RobotRuntime with isolated local preview state. No physical movement or provider TTS.',
                   'Small sequential sample. Tier conclusions are descriptive and can vary with server load.',
                   'Other independent agents are running model tests concurrently; these are shared-load measurements.']}
    client = None
    def save():
        (OUTPUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    try:
        began = time.perf_counter()
        client = CodexClient(model='gpt-6-luna', thinking='low', service_tier='default',
            tools=[], with_memory=False, system_prompt=prompt, run_dir=OUTPUT/'client', max_output_tokens=180)
        report['cold_constructor_s'] = rounded(time.perf_counter()-began)
        report['backend_info'] = dict(client.backend_info)
        client._specs = specs()
        client._selected = {x['name'] for x in client._specs}
        client._bridge = Bridge(RobotRuntime(OUTPUT/'runtime'))
        began = time.perf_counter()
        client.new_session()
        report['configure_tool_session_s'] = rounded(time.perf_counter()-began)
        save()

        def ask(case, group, tier):
            name, text = case
            started = time.perf_counter()
            chunk_buffer = ''
            chunks = []
            deltas = []
            def event(value):
                nonlocal chunk_buffer
                if value.get('type') != 'message_update':
                    return
                item = value.get('assistantMessageEvent', {})
                if item.get('type') != 'text_delta':
                    return
                delta = item.get('delta', '')
                at = time.perf_counter()-started
                deltas.append({'at_s': rounded(at), 'text': delta})
                chunk_buffer += delta
                while (boundary := next_phrase(chunk_buffer)) is not None:
                    end, reason = boundary
                    chunks.append({'at_s': rounded(at), 'text': chunk_buffer[:end], 'reason': reason})
                    chunk_buffer = chunk_buffer[end:]
            value = client.ask(text, timeout=40, on_event=event)
            if chunk_buffer.strip():
                chunks.append({'at_s': rounded(time.perf_counter()-started), 'text': chunk_buffer, 'reason': 'reply_end'})
            row = {
                'id': name, 'group': group, 'tier': tier, 'prompt': text, 'text': value.text,
                'first_text_s': rounded(value.ttft_s), 'first_tool_s': rounded(value.ttf_tool_s),
                'first_speakable_phrase_s': chunks[0]['at_s'] if chunks else None,
                'total_s': rounded(value.total_s), 'errors': value.errors,
                'calls': [{'name': c.name, 'args': c.args, 'at_s': rounded(c.t_offset_s), 'is_error': c.is_error} for c in value.tool_calls],
                'timings': value.timings, 'phrases': chunks, 'deltas': deltas,
                'input_tokens': value.input_tokens, 'output_tokens': value.output_tokens,
                'cached_input_tokens': value.cache_read_tokens,
            }
            print(json.dumps({k: row[k] for k in ('id','group','tier','first_text_s','first_tool_s','first_speakable_phrase_s','total_s','errors')}), flush=True)
            if value.errors:
                raise RuntimeError('Timing turn failed: ' + str(value.errors))
            return row

        for case in BASELINE:
            report['baseline'].append(ask(case, 'continuous_baseline', 'default'))
            save()
        report['baseline_summary'] = summary(report['baseline'])
        advertised = client.backend_info.get('catalog_service_tiers', [])
        report['priority_advertised'] = any(x.get('id') == 'priority' for x in advertised)
        if report['priority_advertised']:
            for index, case in enumerate(PAIRS):
                for tier in (('default','priority') if index%2 == 0 else ('priority','default')):
                    client.service_tier = tier
                    started = time.perf_counter()
                    client.new_session()
                    reset_s = time.perf_counter()-started
                    client._bridge = Bridge(RobotRuntime(OUTPUT/'pairs'/case[0]/tier))
                    row = ask(case, 'matched_tier', tier)
                    row['fresh_session_s'] = rounded(reset_s)
                    row['tier_accepted'] = client.backend_info.get('service_tier_accepted')
                    report['matched_tier_trials'].append(row)
                    save()
            report['tier_summary'] = {tier: summary([r for r in report['matched_tier_trials'] if r['tier']==tier]) for tier in ('default','priority')}
            paired=[]
            for name, _ in PAIRS:
                rows={r['tier']:r for r in report['matched_tier_trials'] if r['id']==name}
                paired.append({'id':name, **{k:rounded(rows['default'][k]-rows['priority'][k])
                    if rows['default'][k] is not None and rows['priority'][k] is not None else None
                    for k in ('first_text_s','first_tool_s','first_speakable_phrase_s','total_s')}})
            report['paired_default_minus_priority_s']=paired
        save()
    finally:
        if client:
            client.close()
        save()


if __name__ == '__main__':
    main()
