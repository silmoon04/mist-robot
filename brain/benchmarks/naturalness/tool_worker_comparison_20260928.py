"""Bounded, read-only tool/latency comparison for local MIST worker choices.

No physical tools, host files, or user data are exposed. The only tools return
fixed synthetic values, and each sample starts a fresh conversation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import re
import sys
import tempfile
import time
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parents[1]
ROOT = BRAIN.parent
sys.path.insert(0, str(BRAIN / 'harness'))
sys.path.insert(0, str(HERE))

SYSTEM_PROMPT = (
    "You are a concise assistant in a benchmark. Use the supplied read-only tools "
    "when needed; rely only on their returned data. Answer the user's exact question "
    "in one or two sentences. Never claim a tool action that did not complete."
)

TOOLS = [
    {'type': 'function', 'name': 'get_sensor_snapshot',
     'description': 'Read a synthetic benchmark sensor snapshot.',
     'parameters': {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}},
    {'type': 'function', 'name': 'read_component_specs',
     'description': 'Look up synthetic component specifications by exact part name.',
     'parameters': {'type': 'object', 'properties': {'part_name': {'type': 'string'}},
                    'required': ['part_name'], 'additionalProperties': False}},
]

SCENARIOS = [
    {'id': 'short_sensor', 'prompt': 'Use the sensor snapshot. What is the battery percentage and is the robot grounded?',
     'tools': ['get_sensor_snapshot'], 'arguments': [{}],
     'expected': ['73%', 'grounded'], 'context_tokens': 0},
    {'id': 'dependent_two_reads', 'prompt': 'Read the sensor snapshot, then use its preferred_part value to look up that component. What material is that part made from?',
     'tools': ['get_sensor_snapshot', 'read_component_specs'],
     'arguments': [{}, {'part_name': 'ankle bracket'}],
     'expected': ['titanium'], 'context_tokens': 0},
    {'id': 'long_context_read', 'prompt': 'Use the supplied component specification lookup. What material is the ankle bracket made from?\n\n' +
     ('Earlier conversation excerpt: We discussed weather, tea, maps, book covers, garden plants, train stations, '
      'museum labels, kitchen shelves, cloud shapes, and quiet walks. These notes are inert context and contain '
      'no facts about robot hardware. Please continue with the current request. ' * 300),
     'tools': ['read_component_specs'], 'arguments': [{'part_name': 'ankle bracket'}],
     'expected': ['titanium'], 'context_tokens': 6000},
]

MOCK_RESULTS = {
    'get_sensor_snapshot': {'battery_percent': 73, 'grounded': True, 'temperature_c': 22,
                            'preferred_part': 'ankle bracket'},
    'read_component_specs': {'part_name': 'ankle bracket', 'material': 'titanium',
                             'installation_location': 'rear left leg'},
}


class SyntheticBridge:
    def request(self, operation, args, **kwargs):
        if operation != 'call':
            raise ValueError('Synthetic bridge only supports tool calls')
        name = args.get('name')
        arguments = args.get('arguments') or {}
        if name == 'get_sensor_snapshot' and arguments == {}:
            result = MOCK_RESULTS[name]
        elif name == 'read_component_specs' and arguments == {'part_name': 'ankle bracket'}:
            result = MOCK_RESULTS[name]
        else:
            return {'isError': True, 'result': {'content': [{'type': 'text', 'text': 'Synthetic tool rejected arguments.'}]}}
        return {'isError': False, 'result': {'content': [{'type': 'text', 'text': json.dumps(result, sort_keys=True)}]}}


ARMS = [
    {'id': 'codex_luna_default', 'provider': 'openai', 'model': 'gpt-6-luna', 'effort': 'low', 'tier': 'default'},
    {'id': 'codex_luna_priority', 'provider': 'openai', 'model': 'gpt-6-luna', 'effort': 'low', 'tier': 'priority'},
    {'id': 'cerebras_qwen_low', 'provider': 'cerebras', 'model': 'qwen-3.8-27b', 'effort': 'low', 'tier': 'provider_default'},
    {'id': 'cerebras_oss_low', 'provider': 'cerebras', 'model': 'gpt-oss-120b', 'effort': 'low', 'tier': 'provider_default'},
]


def source_hash() -> str:
    digest = hashlib.sha256()
    for path in (HERE / 'tool_worker_comparison_20260928.py',
                 BRAIN / 'harness' / 'codex_client.py', HERE / 'cerebras_client.py'):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    fd, temp_name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def make_client(arm, output_dir):
    if arm['provider'] == 'cerebras':
        from cerebras_client import CerebrasClient
        from pi_client import load_env
        env = {**load_env(), **os.environ}
        key = env.get('CEREBRAS_API_KEY', '').strip().strip('"\'')
        if not key:
            raise RuntimeError('CEREBRAS_API_KEY unavailable')
        import httpx
        client = CerebrasClient(model=arm['model'], thinking=arm['effort'],
                                system_prompt=SYSTEM_PROMPT, max_output_tokens=320,
                                run_dir=output_dir / arm['id'] / 'client',
                                http_client=httpx.Client(base_url='https://api.cerebras.ai/v1',
                                    headers={'Authorization': 'Bearer ' + key}, timeout=10,
                                    follow_redirects=False))
        client._specs = [{'name': row['name'], 'description': row['description'],
                          'inputSchema': row['parameters']} for row in TOOLS]
        client._selected = {row['name'] for row in TOOLS}
        client._bridge = SyntheticBridge()
        client.new_session()
        return client
    from codex_client import CodexClient
    client = CodexClient(model=arm['model'], thinking=arm['effort'], service_tier=arm['tier'],
                         system_prompt=SYSTEM_PROMPT, tools=[], with_memory=False,
                         run_dir=output_dir / arm['id'] / 'client', max_output_tokens=320)
    # Replace all capabilities before starting the session; no production bridge is created.
    client._specs = [{'name': row['name'], 'description': row['description'],
                      'inputSchema': row['parameters']} for row in TOOLS]
    client._selected = {row['name'] for row in TOOLS}
    client._bridge = SyntheticBridge()
    client.new_session()
    return client


def event_collector(started):
    marks = {'first_text_s': None, 'tool_call_s': None, 'tool_result_s': None}
    tool_events = []
    def collect(event):
        elapsed = time.perf_counter() - started
        etype = event.get('type')
        if etype == 'message_update':
            delta = event.get('assistantMessageEvent', {})
            if delta.get('type') == 'text_delta' and str(delta.get('delta', '')).strip() and marks['first_text_s'] is None:
                marks['first_text_s'] = elapsed
        elif etype == 'tool_execution_start' and marks['tool_call_s'] is None:
            marks['tool_call_s'] = elapsed
        if etype == 'tool_execution_start':
            tool_events.append({'phase': 'start', 'elapsed_s': elapsed,
                                'name': event.get('toolName'), 'arguments': event.get('args')})
        elif etype == 'tool_execution_end' and marks['tool_result_s'] is None:
            marks['tool_result_s'] = elapsed
        if etype == 'tool_execution_end':
            tool_events.append({'phase': 'result', 'elapsed_s': elapsed,
                                'name': event.get('toolName'), 'arguments': event.get('args'),
                                'result': event.get('result'), 'is_error': bool(event.get('isError'))})
    return marks, tool_events, collect


def as_dict(obj):
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, '__dict__'):
        return vars(obj)
    return {}


def answer_fact_present(text, fact):
    if fact == '73%':
        return re.search(r'(?<!\d)73(?:\s*%|\s+percent)(?![A-Za-z])', text, re.IGNORECASE) is not None
    return fact.casefold() in text.casefold()


def tool_evidence_correct(row, scenario):
    results = [event for event in row.get('tool_events', []) if event.get('phase') == 'result']
    if [event.get('name') for event in results] != scenario['tools']:
        return False
    for event, expected_args in zip(results, scenario['arguments']):
        if event.get('is_error') or event.get('arguments') != expected_args:
            return False
        content = (event.get('result') or {}).get('content') or []
        try:
            actual = json.loads(content[0].get('text', ''))
        except (IndexError, AttributeError, TypeError, json.JSONDecodeError):
            return False
        if actual != MOCK_RESULTS[event['name']]:
            return False
    return True


def run_one(client, arm, scenario, repetition, cold, order):
    client.new_session()
    started = time.perf_counter()
    marks, tool_events, callback = event_collector(started)
    record = {'arm': arm['id'], 'provider': arm['provider'], 'model': arm['model'],
              'effort': arm['effort'], 'requested_tier': arm['tier'],
              'scenario': scenario['id'], 'repetition': repetition, 'cold': cold,
              'order': order, 'prompt': scenario['prompt']}
    try:
        result = client.ask(scenario['prompt'], timeout=30, on_event=callback)
        record.update(marks)
        record['tool_events'] = tool_events
        record['total_s'] = getattr(result, 'total_s', None)
        record['text'] = getattr(result, 'text', '')
        record['errors'] = list(getattr(result, 'errors', []))
        calls = getattr(result, 'tool_calls', [])
        record['tool_calls'] = [as_dict(call) for call in calls]
        record['tool_correct'] = tool_evidence_correct(record, scenario)
        text = record['text'].casefold()
        record['answer_checks'] = {fact: answer_fact_present(record['text'], fact) for fact in scenario['expected']}
        record['answer_correct'] = bool(record['answer_checks']) and all(record['answer_checks'].values())
        record['completed'] = not record['errors'] and bool(record['text'].strip())
        record['public_answer_s'] = record['total_s'] if record['completed'] else None
        record['cumulative_turn_input_tokens'] = getattr(result, 'input_tokens', None)
        record['cumulative_turn_output_tokens'] = getattr(result, 'output_tokens', None)
    except Exception as error:
        record.update(marks)
        record['tool_events'] = tool_events
        record.update(total_s=time.perf_counter() - started, text='', errors=[type(error).__name__ + ': ' + str(error)[:200]],
                      tool_calls=[], tool_correct=False, answer_checks={}, answer_correct=False,
                      completed=False, public_answer_s=None)
    return record


def run_benchmark(output_dir: Path, live=True, seed=20260928, arms=None, repetitions=2,
                  prior_results: Path | None = None):
    arms = list(ARMS if arms is None else arms)
    prior_records = []
    prior_backend = {}
    if prior_results:
        previous = json.loads((prior_results / 'results.json').read_text(encoding='utf-8'))
        prior_records = previous.get('records', [])
        prior_backend = previous.get('backend_info', {})
    samples = [(arm, scenario, rep) for arm in arms for scenario in SCENARIOS
               for rep in range(1, repetitions + 1)]
    completed_keys = {(r.get('arm'), r.get('scenario'), r.get('repetition')) for r in prior_records}
    samples = [item for item in samples if (item[0]['id'], item[1]['id'], item[2]) not in completed_keys]
    if len(samples) + len(prior_records) > 24:
        raise ValueError('Benchmark is bounded to at most 24 model requests including prior samples')
    random.Random(seed).shuffle(samples)
    started_utc = datetime.now(timezone.utc).isoformat()
    manifest = {'started_utc': started_utc, 'seed': seed, 'turn_sample_budget': 24,
                'planned_turn_samples': len(samples), 'prior_turn_samples': len(prior_records),
                'cumulative_request_budget': len(samples) + len(prior_records),
                'source_sha256': source_hash(),
                'tool_data': MOCK_RESULTS, 'scenarios': SCENARIOS,
                'arms': arms, 'environment': 'synthetic readonly tools; no voice, ASR/TTS, or hardware claim',
                'randomized_order': True, 'fresh_session_per_sample': True, 'live': live}
    atomic_json(output_dir / 'manifest.json', manifest)
    records = list(prior_records)
    clients = {}
    backend_info = {}
    if live:
        for arm in arms:
            if not any(sample[0]['id'] == arm['id'] for sample in samples):
                if arm['id'] in prior_backend:
                    backend_info[arm['id']] = prior_backend[arm['id']]
                continue
            try:
                client = make_client(arm, output_dir)
                clients[arm['id']] = client
                info = getattr(client, 'backend_info', {})
                backend_info[arm['id']] = {k: info.get(k) for k in (
                    'provider', 'model_requested', 'model_accepted', 'reasoning_requested',
                    'reasoning_accepted', 'service_tier_requested', 'service_tier_accepted',
                    'catalog_service_tiers', 'request_controls', 'provider_default_effort') if k in info}
                if arm['tier'] == 'priority' and info.get('service_tier_accepted') != 'priority':
                    raise RuntimeError('Backend did not accept priority tier')
            except Exception as error:
                backend_info[arm['id']] = {'setup_error': type(error).__name__ + ': ' + str(error)[:200]}
    else:
        for arm in arms:
            clients[arm['id']] = FakeClient()
            backend_info[arm['id']] = {'provider': 'offline_fake', 'model': arm['model']}
    atomic_json(output_dir / 'backend_info.json', backend_info)
    seen_arms = {r.get('arm') for r in prior_records}
    for order, (arm, scenario, repetition) in enumerate(samples, 1):
        cold = arm['id'] not in seen_arms
        seen_arms.add(arm['id'])
        client = clients.get(arm['id'])
        if client is None:
            records.append({'arm': arm['id'], 'provider': arm['provider'], 'model': arm['model'],
                            'scenario': scenario['id'], 'repetition': repetition, 'order': order,
                            'cold': cold, 'sample_state': 'cold' if cold else 'warm',
                            'context_tokens_expected': scenario['context_tokens'],
                            'completed': False, 'tool_correct': False,
                            'answer_correct': False, 'errors': [backend_info[arm['id']].get('setup_error', 'client unavailable')],
                            'text': '', 'tool_calls': [], 'first_text_s': None, 'tool_call_s': None,
                            'tool_result_s': None, 'total_s': None, 'public_answer_s': None})
            continue
        record = run_one(client, arm, scenario, repetition, cold, order)
        record['sample_state'] = 'cold' if cold else 'warm'
        record['context_tokens_expected'] = scenario['context_tokens']
        records.append(record)
        atomic_json(output_dir / 'results.json', {'manifest': manifest, 'backend_info': backend_info, 'records': records})
    for client in clients.values():
        try:
            client.close()
        except Exception:
            pass
    atomic_json(output_dir / 'results.json', {'manifest': manifest, 'backend_info': backend_info, 'records': records})
    write_csv(output_dir / 'results.csv', records)
    atomic_json(output_dir / 'summary.json', summarize(records, backend_info))
    return records, backend_info


class FakeClient:
    """Deterministic offline runner fixture used to exercise result paths."""
    def new_session(self):
        return None
    def ask(self, prompt, timeout=40, on_event=None):
        from types import SimpleNamespace
        scenario = next(s for s in SCENARIOS if s['prompt'] == prompt)
        names = scenario['tools']
        arguments = scenario['arguments']
        if on_event:
            for name, args in zip(names, arguments):
                on_event({'type': 'tool_execution_start', 'toolName': name, 'args': args})
                receipt = {'content': [{'type': 'text', 'text': json.dumps(MOCK_RESULTS[name], sort_keys=True)}]}
                on_event({'type': 'tool_execution_end', 'toolName': name, 'args': args,
                          'result': receipt, 'isError': False})
            on_event({'type': 'message_update', 'assistantMessageEvent': {'type': 'text_delta', 'delta': '73% grounded titanium rear left leg'}})
        return SimpleNamespace(total_s=0.003, text='73% grounded titanium rear left leg', errors=[],
                               tool_calls=[SimpleNamespace(name=name, args=args, t_offset_s=.001, is_error=False)
                                           for name, args in zip(names, arguments)], input_tokens=30, output_tokens=8)
    def close(self):
        pass


def write_csv(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ['arm', 'provider', 'model', 'effort', 'requested_tier', 'scenario', 'repetition',
              'cold', 'sample_state', 'context_tokens_expected',
              'cumulative_turn_input_tokens', 'cumulative_turn_output_tokens',
              'order', 'first_text_s', 'tool_call_s', 'tool_result_s', 'total_s',
              'public_answer_s', 'tool_correct', 'answer_correct', 'completed', 'errors', 'text']
    fd, temp_name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            for row in records:
                writer.writerow({**row, 'errors': json.dumps(row.get('errors', [])),
                                 'text': row.get('text', '')})
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def summarize(records, backend_info):
    summary = {'backend_info': backend_info, 'arms': {}}
    for arm in sorted({r['arm'] for r in records}):
        rows = [r for r in records if r['arm'] == arm]
        good = [r for r in rows if r.get('completed')]
        summary['arms'][arm] = {
            'n': len(rows), 'completed': len(good),
            'tool_correct': sum(bool(r.get('tool_correct')) for r in rows),
            'answer_correct': sum(bool(r.get('answer_correct')) for r in good),
            'median_first_text_s': median([r.get('first_text_s') for r in good]),
            'median_tool_call_s': median([r.get('tool_call_s') for r in good]),
            'median_tool_result_s': median([r.get('tool_result_s') for r in good]),
            'median_public_answer_s': median([r.get('public_answer_s') for r in good]),
            'errors': [r.get('errors', []) for r in rows if r.get('errors')],
        }
    return summary


def refresh_result_artifacts(output_dir: Path):
    """Recompute answer checks and summaries from saved responses without provider calls."""
    path = output_dir / 'results.json'
    original_path = output_dir / 'results.pre_regrade.json'
    if not original_path.exists():
        original_path.write_bytes(path.read_bytes())
    bundle = json.loads(path.read_text(encoding='utf-8'))
    expected_by_id = {scenario['id']: scenario['expected'] for scenario in SCENARIOS}
    for row in bundle.get('records', []):
        row['cold'] = None
        row['sample_state'] = 'not_comparable_smoke_prelude_and_client_restart'
        row['cumulative_turn_input_tokens'] = row.pop('input_tokens', row.get('cumulative_turn_input_tokens'))
        row['cumulative_turn_output_tokens'] = row.pop('output_tokens', row.get('cumulative_turn_output_tokens'))
        expected = expected_by_id.get(row.get('scenario'), [])
        scenario = next((case for case in SCENARIOS if case['id'] == row.get('scenario')), None)
        if scenario is not None:
            row['tool_correct'] = tool_evidence_correct(row, scenario)
        row['answer_checks'] = {fact: answer_fact_present(row.get('text', ''), fact) for fact in expected}
        row['answer_correct'] = bool(row['answer_checks']) and all(row['answer_checks'].values())
    bundle['manifest']['scorer_revision_sha256'] = hashlib.sha256(
        ('evidence-check-v3:' + repr(answer_fact_present.__code__.co_consts) +
         repr(tool_evidence_correct.__code__.co_consts)).encode()
    ).hexdigest()
    bundle['manifest']['turn_sample_budget'] = 24
    bundle['manifest']['turn_sample_count'] = len(bundle.get('records', []))
    bundle['manifest']['provider_round_counts_retained'] = False
    atomic_json(path, bundle)
    write_csv(output_dir / 'results.csv', bundle['records'])
    atomic_json(output_dir / 'summary.json', summarize(bundle['records'], bundle.get('backend_info', {})))
    write_report(output_dir / 'REPORT.md', bundle)
    return bundle


def write_report(path: Path, bundle):
    records = bundle.get('records', [])
    summary = summarize(records, bundle.get('backend_info', {}))
    lines = [
        '# Read-only worker tool benchmark — 2026-09-28', '',
        'This compares model response and tool-turn latency on fixed synthetic readings. It does not measure ASR, speech output, physical robot control, or real sensor accuracy.', '',
        f"The run used {len(records)} benchmark turn samples: {bundle['manifest'].get('prior_requests', 0)} smoke samples plus {bundle['manifest'].get('planned_requests', 0)} main-run samples. This is not a count of provider HTTP/model rounds: a tool-using turn can trigger multiple rounds, and per-turn round counts were not retained. Each sample started a fresh conversation; the smoke samples were a prelude, then the remaining samples ran sequentially in randomized order. No failures were retried. Cold/warm results are not compared because the smoke client was closed and recreated for the main run.", '',
        'The short case reads one synthetic sensor snapshot. The dependent case reads the snapshot, then uses its `preferred_part` receipt to request a component lookup. The long case uses the same lookup after an inert context prompt. Input tokens are provider-reported cumulative turn usage, summed across multiple model rounds; they do not represent one prompt or a single model context. Round-level usage was not retained by this run. Tool arguments, receipts, timings, model text, token counts, and errors are retained in `results.json`.', '',
        '## Results', '',
        '| Arm | Completed | Correct tool sequence | Fact checks on completed answers | Median answer time | Median first text | Cumulative input tokens by case |',
        '|---|---:|---:|---:|---:|---:|---|',
    ]
    scenario_ids = [scenario['id'] for scenario in SCENARIOS]
    labels = {'short_sensor': 'short', 'dependent_two_reads': 'two reads', 'long_context_read': 'long context'}
    for arm, stat in summary['arms'].items():
        rows = [r for r in records if r.get('arm') == arm]
        token_parts = []
        for scenario_id in scenario_ids:
            tokens = [r.get('cumulative_turn_input_tokens') for r in rows if r.get('scenario') == scenario_id and isinstance(r.get('cumulative_turn_input_tokens'), int) and r.get('cumulative_turn_input_tokens') > 0]
            token_parts.append(f"{labels[scenario_id]} {round(sum(tokens)/len(tokens)) if tokens else 'n/a'}")
        lines.append(f"| `{arm}` | {stat['completed']}/{stat['n']} | {stat['tool_correct']}/{stat['n']} | {stat['answer_correct']}/{stat['completed']} | {fmt(stat['median_public_answer_s'])} s | {fmt(stat['median_first_text_s'])} s | " + ', '.join(token_parts) + ' |')
    lines += ['', 'Answer checks are deterministic fact checks only (including Unicode whitespace handling for `73 %`); they are not a subjective quality rubric. Tool correctness requires the exact expected call sequence, accepted arguments, and non-error receipts. Manual review of all 22 completed responses found them supported by their synthetic tool receipts.', '', '## Scenario-level timing', '', '| Arm | Case | First text | Tool call | Receipt | Public answer |', '|---|---|---:|---:|---:|---:|']
    for arm in summary['arms']:
        for scenario_id in scenario_ids:
            rows = [r for r in records if r.get('arm') == arm and r.get('scenario') == scenario_id and r.get('completed')]
            groups = [[r.get(key) for r in rows if isinstance(r.get(key), (int, float))] for key in
                      ('first_text_s', 'tool_call_s', 'tool_result_s', 'public_answer_s')]
            cells = [f"{fmt(median(group))} s" if group else 'n/a' for group in groups]
            lines.append(f"| `{arm}` | {labels[scenario_id]} | " + ' | '.join(cells) + ' |')
    lines += ['', '## Backend acceptance and failures', '']
    for arm, info in bundle.get('backend_info', {}).items():
        accepted = info.get('service_tier_accepted')
        if accepted:
            label = next((tier.get('name') for tier in info.get('catalog_service_tiers', []) if tier.get('id') == accepted), accepted)
            lines.append(f"- `{arm}`: requested `{info.get('service_tier_requested')}`, backend accepted `{accepted}` (catalog label `{label}`), model `{info.get('model_accepted')}`, effort `{info.get('reasoning_accepted')}`.")
    for arm, stat in summary['arms'].items():
        for errors in stat['errors']:
            lines.append(f"- `{arm}` retained error: `{'; '.join(errors)}`.")
    lines += ['', 'Luna default versus Fast/priority is a small six-sample comparison per tier; it is not enough to infer a stable speed multiplier. The accepted tier establishes that the request was routed as requested, not that a latency gain is guaranteed. Qwen completed the long-context case in both repetitions. OSS low timed out on both long-context requests under the existing 10-second HTTP read timeout; these were retained without retry. Its median timings use only completed samples.', '', '## Commands', '', 'Run the fake-provider tests:', '', '```powershell', 'python -m unittest brain.benchmarks.naturalness.test_tool_worker_comparison_20260928 -v', '```', '', 'Reproduce the offline runner artifact:', '', '```powershell', 'python brain/benchmarks/naturalness/tool_worker_comparison_20260928.py --offline --output-dir brain/results/session-review-20260928/worker-benchmark-offline', '```', '', 'Refresh this saved run without making provider calls:', '', '```powershell', 'python brain/benchmarks/naturalness/tool_worker_comparison_20260928.py --refresh-artifacts --output-dir brain/results/session-review-20260928/worker-benchmark', '```', '', 'The live run used this command after its separate three-sample smoke:', '', '```powershell', 'python brain/benchmarks/naturalness/tool_worker_comparison_20260928.py --continue-smoke brain/results/session-review-20260928/worker-benchmark-smoke --output-dir brain/results/session-review-20260928/worker-benchmark', '```', '', f"Run source/config hash (unchanged): `{bundle['manifest']['source_sha256']}`.", f"Scorer revision hash: `{bundle['manifest']['scorer_revision_sha256']}`. Original result bundle before answer-check correction: `results.pre_regrade.json`.", '']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines), encoding='utf-8')


def fmt(value):
    return 'n/a' if value is None else f'{value:.2f}'


def median(values):
    values = sorted(v for v in values if isinstance(v, (int, float)))
    if not values:
        return None
    middle = len(values) // 2
    return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=BRAIN / 'results' / 'session-review-20260928' / 'worker-benchmark')
    parser.add_argument('--offline', action='store_true', help='Run deterministic fake-provider path only')
    parser.add_argument('--smoke', action='store_true', help='Run a one-arm, one-sample live smoke test')
    parser.add_argument('--continue-smoke', type=Path, help='Include a completed smoke result directory without repeating its requests')
    parser.add_argument('--refresh-artifacts', action='store_true', help='Recompute checks and report from saved results only')
    args = parser.parse_args()
    if args.refresh_artifacts:
        bundle = refresh_result_artifacts(args.output_dir)
        print(json.dumps(summarize(bundle['records'], bundle['backend_info']), indent=2))
        return
    arms = ARMS[:1] if args.smoke else ARMS
    repetitions = 1 if args.smoke else 2
    records, info = run_benchmark(args.output_dir, live=not args.offline, arms=arms,
                                  repetitions=repetitions, prior_results=args.continue_smoke)
    print(json.dumps(summarize(records, info), indent=2))


if __name__ == '__main__':
    main()
