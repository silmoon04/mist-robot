"""One-pass text-only comparison of a Qwen speaker with optional affect readers.

This is an isolated benchmark adapter. It makes provider requests but never starts
the live voice service, TTS, renderer, or physical robot path.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import escape
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import sys
import threading
import time
import uuid

BRAIN = Path(__file__).resolve().parents[2]
ROOT = BRAIN.parent
sys.path.insert(0, str(BRAIN))
sys.path.insert(0, str(BRAIN / 'harness'))
sys.path.insert(0, str(BRAIN / 'benchmarks' / 'naturalness'))

from duplex.affect_director import AffectDirector
from duplex.conversation_policy import POLICIES
from duplex.expression_policy import FACE_MAP
from duplex.runtime import RobotRuntime, specs as runtime_specs
from benchmarks.naturalness.cerebras_client import CerebrasClient
from duplex.background import specs as background_specs
from duplex.phrasing import next_phrase
from eval_luna_conversations import RuntimeBridge
from pi_client import load_env

RESULTS = BRAIN / 'results' / 'dual-model-harness-20260924' / 'comparison-rerun'
CASES_PATH = BRAIN / 'results' / 'dual-model-harness-20260924' / 'director-cases.json'
SPEAKER_MODEL = 'qwen-3.8-27b'
SPEAKER_EFFORT = 'low'
ARMS = ('qwen_single_speaker', 'qwen_director_qwen_speaker',
        'gpt_oss_director_qwen_speaker')
CASE_NAMES = (
    'steady_mood_after_disappointment',
    'explicit_face_with_scope',
    'direct_override_of_inferred_mood',
    'ambiguous_observation_and_correction',
    'ambiguous_negative_question',
    'speaker_phrase_conflicts_with_active_face',
)
MAX_TURN_S = 45


def sha256(value) -> str:
    if isinstance(value, str):
        value = value.encode('utf-8')
    return hashlib.sha256(value).hexdigest()


def ensure_api_key():
    env = load_env()
    if env.get('CEREBRAS_API_KEY'):
        os.environ.setdefault('CEREBRAS_API_KEY', env['CEREBRAS_API_KEY'].strip('"\''))
    if not os.environ.get('CEREBRAS_API_KEY'):
        raise RuntimeError('CEREBRAS_API_KEY unavailable; no benchmark call made')


def speaker_prompt(memory):
    prompt = (BRAIN / 'duplex' / 'persona.txt').read_text(encoding='utf-8')
    prompt = prompt.replace("Your voice is being converted to the owner's MIST voice.",
                            "Your words are spoken through the owner's MIST streaming TTS voice.")
    prompt += ('\nThis benchmark uses you directly for text and application tools. Use the supplied tools '
               'yourself where the persona mentions delegation. No native voice agent is present. '
               'Earlier assistant text describes generated words, not proof the person heard them. '
               'Follow the latest correction without resuming interrupted material.')
    # The experiment holds this policy fixed across all three arms.
    prompt += POLICIES['responsive']
    if memory:
        prompt += '\nSaved preference reports: ' + json.dumps(memory[-12:], ensure_ascii=False)
    return prompt


def first_phrase(text):
    """Return the first actual complete punctuation-delimited phrase, if present."""
    clean = text.strip()
    if not clean:
        return ''
    match = re.search(r'(?s)^.{8,}?[.!?](?:["\'”’)]*)?(?:\s|$)', clean)
    if match:
        return match.group(0).strip()
    if len(clean) >= 180:
        return clean[:180].rsplit(' ', 1)[0]
    return ''


def call_speaker(case, arm, case_dir, director_model=None, director_effort=None,
                 *, speaker_factory=None, director_factory=None):
    run_id = uuid.uuid4().hex[:12]
    run_path = case_dir / arm / run_id
    run_path.mkdir(parents=True, exist_ok=True)
    raw_path = run_path / 'raw.json'
    raw_lock = threading.Lock()
    raw = {'run_id': run_id, 'case_id': case['id'], 'arm': arm,
           'speaker_model': SPEAKER_MODEL, 'speaker_reasoning_effort': SPEAKER_EFFORT,
           'director_model': director_model, 'director_effort': director_effort,
           'status': 'started', 'speaker_deltas': [], 'speaker_result': None,
           'director_result': None, 'exception_type': None}

    def persist_raw():
        with raw_lock:
            temp_path = raw_path.with_suffix('.json.tmp')
            temp_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8')
            temp_path.replace(raw_path)

    persist_raw()
    runtime = RobotRuntime(run_path / 'runtime')
    prompt = speaker_prompt(runtime.memory)
    prompt_hash = sha256(prompt)
    factory = CerebrasClient if speaker_factory is None else speaker_factory
    client = factory(model=SPEAKER_MODEL, thinking=SPEAKER_EFFORT,
                     system_prompt=prompt, max_output_tokens=4096,
                     parallel_tool_calls=True, run_dir=run_path / 'speaker')
    client._specs = runtime_specs() + background_specs()
    background_names = {s['name'] for s in background_specs()}
    client._selected = {spec['name'] for spec in client._specs if spec['name'] not in background_names}
    bridge = RuntimeBridge(runtime)
    bridge.prepare('none', request_text=case['current_user'])
    client._bridge = bridge
    client.new_session()
    context, current = case['context'], case['current_user']
    for row in context:
        role = row['role']
        if role not in ('user', 'assistant'):
            continue
        client.messages.append({'role': role, 'content': row['text']})

    latest_assistant = ''
    first_nonblank_at = None
    first_phrase_at = None
    first_phrase_text = ''
    director_started_at = None
    director_future = None
    director_result = None
    director_started_event = threading.Event()
    wall_start = time.perf_counter()
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='affect-reader')

    def run_director():
        nonlocal director_started_at
        records = [{'id': f'fixture_{i}', 'role': row['role'], 'text': row['text']}
                   for i, row in enumerate(context)]
        snapshot = {'records': records, 'current_user': current,
                    'current_face': fixture_face(context),
                    'speaker_text': '',
                    'face_override': case.get('face_override') is True}
        reader_cls = AffectDirector if director_factory is None else director_factory
        reader = reader_cls(model=director_model, reasoning_effort=director_effort,
                            timeout_s=12)
        director_started_at = time.perf_counter()
        director_started_event.set()
        return reader.decide_with_trace(snapshot)

    def on_event(event):
        nonlocal latest_assistant, first_nonblank_at, first_phrase_at, first_phrase_text
        if event.get('type') != 'message_update':
            return
        inner = event.get('assistantMessageEvent') or {}
        if inner.get('type') != 'text_delta':
            return
        delta = inner.get('delta') or ''
        latest_assistant += delta
        raw['speaker_deltas'].append(delta)
        raw['status'] = 'speaker_streaming'
        persist_raw()
        now = time.perf_counter()
        if latest_assistant.strip() and first_nonblank_at is None:
            first_nonblank_at = now
        if first_phrase_at is None:
            boundary = next_phrase(latest_assistant)
            if boundary:
                first_phrase_at = now
                first_phrase_text = latest_assistant[:boundary[0]].strip()

    speaker_error = None
    director_error = None
    speaker_result = None
    try:
        if director_model:
            director_future = executor.submit(run_director)
            def save_reader(future):
                try:
                    decision, trace = future.result()
                    raw['director_result'] = {'decision': decision, 'trace': trace}
                    raw['status'] = 'reader_complete' if trace.get('status') != 'provider_failure' else 'reader_provider_failure'
                except Exception as error:
                    raw['director_result'] = {'exception_type': type(error).__name__,
                                              'exception_message': str(error)[:240]}
                    raw['status'] = 'reader_exception'
                persist_raw()
            director_future.add_done_callback(save_reader)
            # Establish that the reader starts before the speaker request is sent;
            # never wait for the reader's completion on the speech path.
            if not director_started_event.wait(timeout=2):
                raise TimeoutError('Affect reader did not start before speaker request')
        speaker_result = client.ask(current, timeout=MAX_TURN_S, on_event=on_event)
        speaker_done_at = time.perf_counter()
        raw['speaker_result'] = {
            'text': getattr(speaker_result, 'text', ''),
            'errors': list(getattr(speaker_result, 'errors', []) or []),
            'tool_calls': [{'name': t.name, 'arguments': t.args, 'is_error': t.is_error}
                           for t in (getattr(speaker_result, 'tool_calls', []) or [])],
            'timings': getattr(speaker_result, 'timings', {}),
            'first_nonblank_ms': (None if first_nonblank_at is None else
                                  round((first_nonblank_at - wall_start) * 1000, 1)),
            'speaker_total_ms': round((speaker_done_at - wall_start) * 1000, 1),
        }
        raw['status'] = 'speaker_complete'
        persist_raw()
        if director_future is not None:
            try:
                director_result = director_future.result(timeout=14)
            except Exception as error:
                director_error = type(error).__name__
                director_result = (None, {'status': 'harness_reader_failure',
                                          'exception_type': director_error,
                                          'elapsed_ms': None})
            if director_error is not None:
                raw['director_result'] = {'exception_type': director_error}
                raw['status'] = 'reader_error'
                persist_raw()
        else:
            director_error = None
    except Exception as error:
        speaker_error = type(error).__name__
        speaker_done_at = time.perf_counter()
        director_error = None
        raw['exception_type'] = speaker_error
        raw['exception_message'] = str(error)[:240]
        raw['status'] = 'speaker_exception'
        persist_raw()
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
        client.close()

    answer = getattr(speaker_result, 'text', '') if speaker_result else ''
    speaker_trace = {
        'provider': 'cerebras', 'model': SPEAKER_MODEL,
        'reasoning_effort': SPEAKER_EFFORT,
        'prompt_sha256': prompt_hash, 'prompt_version': 'cascade_voice_make_client-responsive-adapter',
        'history_source': 'authored frozen fixture; this arm’s generated answer is retained in result',
        'current_user': current, 'answer': answer,
        'errors': list(getattr(speaker_result, 'errors', []) or []),
        'tool_calls': [{'name': t.name, 'arguments': t.args, 'is_error': t.is_error}
                       for t in (getattr(speaker_result, 'tool_calls', []) or [])],
        'bridge_receipts': getattr(bridge, 'receipts', []),
        'timings': getattr(speaker_result, 'timings', {}),
        'first_nonblank_ms': (None if first_nonblank_at is None else
                              round((first_nonblank_at - wall_start) * 1000, 1)),
        'speaker_total_ms': round((speaker_done_at - wall_start) * 1000, 1),
        'first_phrase_ms': (None if first_phrase_at is None else
                            round((first_phrase_at-wall_start)*1000, 1)),
        'first_phrase': first_phrase_text,
        'exception_type': speaker_error,
    }
    reader = None
    if director_result:
        decision, trace = director_result
        # Do not treat the proposal as a tool receipt or a visible face action.
        reader_completed = (None if director_started_at is None or trace.get('elapsed_ms') is None
                            else round((director_started_at - wall_start) * 1000 + trace['elapsed_ms'], 1))
        reader = {'decision': decision, 'trace': trace,
                  'speaker_text_at_reader_start': '',
                  'reader_started_ms': (None if director_started_at is None else
                                        round((director_started_at-wall_start)*1000, 1)),
                  'reader_completed_ms': reader_completed,
                  'completed_before_first_phrase': (reader_completed is not None and first_phrase_at is not None
                                                    and reader_completed <= round((first_phrase_at-wall_start)*1000, 1)),
                  'proposal_applied': False,
                  'proposal_note': 'Reader output is validated advice only; this text-only harness has no renderer.'}
    raw['speaker_trace'] = speaker_trace
    raw['reader_trace'] = reader
    raw['director_exception_type'] = director_error
    speaker_provider_errors = list(getattr(speaker_result, 'errors', []) or [])
    raw['status'] = ('complete' if speaker_error is None and director_error is None
                     and not speaker_provider_errors else 'complete_with_error')
    persist_raw()
    try:
        raw_relpath = str(raw_path.relative_to(ROOT)).replace('\\', '/')
    except ValueError:
        raw_relpath = str(raw_path)
    return {'run_id': run_id, 'speaker': speaker_trace, 'director': reader,
            'director_exception_type': director_error,
            'raw_path': raw_relpath}


def model_catalog():
    path = ROOT / '.env.example'
    return {'source': '.env.example; secrets excluded', 'sha256': sha256(path.read_bytes()) if path.exists() else None}


def frozen_turn(source):
    """Only authored transcript rows are model input; criteria never pass through."""
    history = source.get('history')
    if not isinstance(history, list) or not history:
        raise ValueError('fixture history is required')
    last_user = next((i for i in range(len(history) - 1, -1, -1)
                      if history[i].get('role') == 'user'), None)
    if last_user is None:
        raise ValueError('fixture requires a user turn')
    rows = history[:last_user]
    considered = rows + [history[last_user]]
    if any(row.get('role') not in ('user', 'assistant') or not isinstance(row.get('text'), str)
           for row in considered):
        raise ValueError('fixture history has an unsupported record')
    return rows, history[last_user]['text']


def fixture_face(context):
    """Use explicit user display requests in transcript history as UI state."""
    names = sorted(FACE_MAP['expressions'], key=len, reverse=True)
    current = {'expression': 'neutral', 'variant': 0}
    for row in context:
        if row['role'] != 'user':
            continue
        text = row['text'].lower()
        for name in names:
            pattern = (rf"\b(?:show|use|make|switch to|change to|set|keep|put on)\b"
                       rf"[^.!?\n]{{0,60}}\b{re.escape(name)}\b[^.!?\n]{{0,25}}\b(?:face|expression)\b")
            if re.search(pattern, text):
                current = {'expression': name, 'variant': 0}
                break
    return current


def explicit_face_override(current_user):
    text = current_user.lower()
    if re.search(r"\bcan you not\b|\bnot talk with\b|\bwould .* fit\b", text):
        return False
    pattern = r"\b(?:show|use|make|switch to|change to|set|keep|put on)\b[^.!?\n]{0,80}\b(?:face|expression)\b"
    return bool(re.search(pattern, text))


def source_manifest():
    paths = [BRAIN / 'duplex' / 'affect_director.py',
             BRAIN / 'duplex' / 'persona.txt',
             BRAIN / 'duplex' / 'conversation_policy.py',
             BRAIN / 'duplex' / 'background.py',
             BRAIN / 'duplex' / 'runtime.py',
             BRAIN / 'duplex' / 'expression_policy.py',
             BRAIN / 'duplex' / 'phrasing.py',
             BRAIN / 'harness' / 'eval_luna_conversations.py',
             BRAIN / 'benchmarks' / 'naturalness' / 'cerebras_client.py',
             Path(__file__)]
    return {str(path.relative_to(ROOT)).replace('\\', '/'): sha256(path.read_bytes())
            for path in paths}


def render_html(report):
    rows = []
    for case in report['cases']:
        for arm in ARMS:
            result = case['arms'].get(arm)
            if not result:
                continue
            speaker = result['speaker']
            director = result.get('director')
            decision = director.get('decision') if director else None
            trace = director.get('trace') if director else None
            face = ('no reader' if decision is None else
                    f"{decision['expression']} v{decision['variant']} {'(change)' if decision['change'] else '(hold)'}")
            delivery = 'not applicable' if decision is None else decision['delivery']
            raw_decision = (trace or {}).get('raw_decision', '')
            speaker_errors = speaker.get('errors') or []
            speaker_error = '; '.join(speaker_errors) if speaker_errors else speaker.get('exception_type') or 'none'
            first = speaker.get('first_nonblank_ms')
            phrase_at = speaker.get('first_phrase_ms')
            end = speaker.get('speaker_total_ms')
            done = director.get('reader_completed_ms') if director else None
            eligible = 'not applicable' if done is None or phrase_at is None else ('reader first' if done < phrase_at else 'phrase first')
            rows.append(f"<tr><td>{escape(case['id'])}</td><td>{escape(arm)}</td><td>{escape(str(speaker.get('answer','')))}</td>"
                        f"<td>{escape(face)}</td><td>{escape(delivery)}</td><td>{escape(str((trace or {}).get('status','not applicable')))}</td>"
                        f"<td>{escape(raw_decision)}</td><td>{escape(str(speaker_error))}</td>"
                        f"<td>{escape(str(first))}</td><td>{escape(str(phrase_at))}</td><td>{escape(str(end))}</td><td>{escape(str(done))}</td><td>{escape(eligible)}</td></tr>")
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>Affect director comparison</title><style>body{font:15px/1.5 system-ui,sans-serif;max-width:1500px;margin:32px auto;padding:0 20px;color:#202b2b}h1{font-size:30px}p{max-width:1000px;color:#43514f}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border-bottom:1px solid #ccd4d0;padding:9px;text-align:left;vertical-align:top}th{position:sticky;top:0;background:#f2f5f1}td:nth-child(3){min-width:280px;max-width:540px;white-space:pre-wrap}code{background:#eef2ee;padding:2px 4px}</style><body>'
            '<h1>Qwen speaker with optional affect director</h1>'
            '<p>One pass, text only. The director starts at user-turn dispatch with an empty proposed phrase; it does not wait for speaker text. Its proposal is not a tool receipt, renderer action, audio tone, or proof of playback. Prior messages are authored frozen fixtures. Speaker phrase examples, rubrics, and criteria are excluded from model input. Reader and speaker times share one local monotonic clock. “Before first phrase” means reader completion preceded the production phrase boundary, not audible speech.</p>'
            '<table><thead><tr><th>Case</th><th>Arm</th><th>Speaker output</th><th>Validated face</th><th>Delivery</th><th>Reader status</th><th>Raw reader JSON</th><th>Speaker errors</th><th>First text ms</th><th>First phrase ms</th><th>Speaker done ms</th><th>Reader done ms</th><th>Phrase readiness</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></body></html>')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', default=','.join(CASE_NAMES),
                        help='Comma-separated frozen case IDs (default: selected six).')
    parser.add_argument('--output', default='comparison.json',
                        help='JSON filename inside comparison-rerun.')
    args = parser.parse_args(argv)
    selected_names = [name.strip() for name in args.cases.split(',') if name.strip()]
    if not selected_names or Path(args.output).name != args.output:
        raise ValueError('Select cases and a simple output filename')
    ensure_api_key()
    raw_cases = CASES_PATH.read_bytes()
    dataset = json.loads(raw_cases)
    source_cases = [c for c in dataset['cases'] if c['id'] in selected_names]
    missing = sorted(set(selected_names) - {c['id'] for c in source_cases})
    if missing:
        raise ValueError('Unknown case IDs: ' + ', '.join(missing))
    if not source_cases:
        raise ValueError('No benchmark cases selected')
    RESULTS.mkdir(parents=True, exist_ok=True)
    order_rng = random.Random(20260924)
    report = {'experiment': 'Qwen speaker with optional affect director',
              'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'mode': 'single_pass_no_tuning', 'text_only': True,
              'arms': list(ARMS), 'speaker_model': SPEAKER_MODEL,
              'speaker_reasoning_effort': SPEAKER_EFFORT,
              'director_models': {'qwen_director_qwen_speaker': ['qwen-3.8-27b', 'none'],
                                  'gpt_oss_director_qwen_speaker': ['gpt-oss-120b', 'low']},
              'source_case_path': str(CASES_PATH.relative_to(ROOT)).replace('\\', '/'),
              'source_case_sha256': sha256(raw_cases),
              'model_catalog': model_catalog(),
              'source_sha256': source_manifest(),
              'prompt_sha256': {'speaker': sha256(speaker_prompt([]))},
              'speaker_output_limit': 4096, 'parallel_tool_calls': True,
              'reader_launch': 'Started at user-turn dispatch before the speaker request, with speaker_text empty; reader never gates speaker text.',
              'disclosure': 'Speaker histories are authored frozen fixtures; each arm retains its own generated current reply. Reader inputs receive the same user transcript/history and empty proposed phrase, never speaker_phrase_for_alignment, discriminates, or review_questions. Reader proposals are not applied. This is not a voice or renderer rating.',
              'cases': []}
    (RESULTS / 'harness-source-frozen.py').write_bytes(Path(__file__).read_bytes())
    (RESULTS / 'prompt-frozen.txt').write_text(speaker_prompt([]), encoding='utf-8')
    for source in source_cases:
        context, current_user = frozen_turn(source)
        case = {'id': source['id'], 'history': source['history'], 'context': context,
                'current_user': current_user,
                'face_override': explicit_face_override(current_user)}
        # Explicit face instructions are intentionally excluded from reader calls by
        # the module's override contract only when the harness itself marks them.
        case_dir = RESULTS / case['id']
        case_dir.mkdir(parents=True, exist_ok=True)
        arms = {}
        order = list(ARMS)
        order_rng.shuffle(order)
        result_case = {'id': case['id'], 'arm_order': order,
                       'fixture_history_sha256': sha256(json.dumps(case['history'], ensure_ascii=False, sort_keys=True)),
                       'current_user': current_user,
                       'context_roles': [row['role'] for row in context], 'arms': arms}
        report['cases'].append(result_case)
        partial_path = RESULTS / (Path(args.output).stem + '.partial.json')
        partial_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        for arm in order:
            print(f"RUN {case['id']} {arm}", flush=True)
            director_model = director_effort = None
            if arm == 'qwen_director_qwen_speaker':
                director_model, director_effort = 'qwen-3.8-27b', 'none'
            elif arm == 'gpt_oss_director_qwen_speaker':
                director_model, director_effort = 'gpt-oss-120b', 'low'
            try:
                arms[arm] = call_speaker(case, arm, case_dir,
                                         director_model=director_model,
                                         director_effort=director_effort)
            except Exception as error:
                arms[arm] = {'speaker': {'answer': '', 'errors': [],
                                        'exception_type': type(error).__name__,
                                        'exception_message': str(error)[:240]},
                             'director': None}
            partial_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    report_path = RESULTS / args.output
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (RESULTS / 'index.html').write_text(render_html(report), encoding='utf-8')
    md = ['# Affect director comparison', '',
          'Single pass, text-only, with no tuning. Speaker wording is evaluated from actual model output. Reader outputs are validated proposals; they were not applied to a renderer. No audible tone or visible face result is measured.', '',
          f"- Cases: {len(report['cases'])}",
          '- Arms: Qwen speaker only; Qwen none director plus Qwen low speaker; GPT-OSS low director plus Qwen low speaker.',
          '- Speaker prompt: production persona adapter with responsive conversation policy, fixed across arms.',
          '- Prior context: authored fixtures. Speaker phrase examples, rubrics, and criteria were excluded from model inputs.',
          '- Reader starts before the speaker request with an empty proposed phrase, using the same committed user turn and frozen history. It never gates speaker output.',
          '- First nonblank text and the first phrase boundary from `duplex.phrasing.next_phrase` are measured against reader completion on one local monotonic clock.',
          '- Text-only limits: no acoustic onset, prosody, renderer visibility, persistence, or human naturalness score.', '',
          f"See `index.html` for the per-case table and `{args.output}` for the complete output, raw snapshots, reader traces, tool receipts, timings, and error records.", '']
    (RESULTS / 'COMPARISON.md').write_text('\n'.join(md), encoding='utf-8')
    partial_path.unlink(missing_ok=True)
    print(f"WROTE {report_path}", flush=True)


if __name__ == '__main__':
    main()
