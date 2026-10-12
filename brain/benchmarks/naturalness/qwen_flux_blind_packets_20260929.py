"""Create blinded semantic-review packets from a finished live pilot (offline)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import secrets
import shutil
import sys

BRAIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BRAIN))
from benchmarks.naturalness import speech_cases_20260930 as spec


def write(path: Path, obj: object):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def tool_evidence(receipts: list[dict]) -> list[dict]:
    answer = []
    for row in receipts:
        event = row.get('event', {})
        if not isinstance(event, dict) or event.get('type') not in ('tool', 'debug_tool', 'tool_call', 'tool_result'):
            continue
        reduced = {key: event[key] for key in ('type', 'phase', 'name', 'arguments', 'result',
                   'success', 'error_type', 'expression', 'variant') if key in event}
        if reduced and reduced not in answer:
            answer.append(reduced)
    return answer


def packet(row: dict, case: spec.Case) -> dict:
    events = row.get('scored_events', [])
    ids = set(row.get('stage', {}).get('input_user_turn_ids', []))
    final_id = row.get('stage', {}).get('active_user_turn_id')
    user_done = [e for e in events if e.get('type') == 'transcript_done' and e.get('role') == 'user']
    assistant_done = [e for e in events if e.get('type') == 'transcript_done' and
                      e.get('role') == 'assistant' and e.get('benchmark_parent_user_turn_id') in ids]
    assistant_deltas = [e for e in events if e.get('type') == 'transcript_delta' and
                        e.get('role') == 'assistant' and e.get('benchmark_parent_user_turn_id') in ids]
    face = [{key: e[key] for key in ('expression', 'variant', 'source', 'persistent') if key in e}
            for e in events if e.get('type') == 'face']
    return dict(case_id=case.id, input_oracle=list(case.expected_transcript),
        target_checklist=list(case.semantic_constraints),
        accepted_user_transcripts=[e.get('text', '') for e in user_done],
        accepted_final_user_transcript=next((e.get('text', '') for e in reversed(user_done)
            if e.get('benchmark_turn_id') == final_id), user_done[-1].get('text', '') if user_done else None),
        assistant_final_texts=[e.get('text', '') for e in assistant_done],
        assistant_streamed_text=''.join(str(e.get('text', '')) for e in assistant_deltas),
        tool_receipts=tool_evidence(row.get('runtime_receipts', [])),
        face_events=face,
        outcome_flags=dict(status=row.get('status'),
            complete_response_capture=row.get('status') == 'complete' and bool(assistant_done)
                and bool(row.get('stage', {}).get('tts_drain_receipts'))
                and row.get('stage', {}).get('software_queue_drain_ms') is not None,
            seed_active_at_input=row.get('seed_playing_at_input'),
            runtime_error_type=(row.get('error') or {}).get('type'),
            trace_export_failed=bool(row.get('trace_export_error'))),
        response_audio_files=[])


def build(run: Path, output: Path, private_key: Path):
    rows = json.loads((run / 'attempts.json').read_text(encoding='utf-8'))
    if len(rows) != 32 or not (run / 'report.json').exists():
        raise ValueError('Blind packets require a finished 32-attempt run')
    if output.exists() or private_key.exists():
        raise FileExistsError('Blind output or private key already exists')
    output.mkdir(parents=True)
    mapping = []
    names = []
    for row in rows:
        case = next(c for c in spec.CASES if c.id == row['case_id'])
        ident = 'P-' + secrets.token_hex(6).upper()
        data = packet(row, case)
        data['packet_id'] = ident
        target_turns = {e.get('benchmark_turn_id') for e in row.get('scored_events', [])
            if e.get('type') == 'audio' and e.get('benchmark_parent_user_turn_id') in
                set(row.get('stage', {}).get('input_user_turn_ids', []))}
        for index, audio in enumerate(row.get('output_audio', []), 1):
            if audio.get('file') and audio.get('turn_id') in target_turns:
                filename = f'{ident}-response-{index}.wav'
                shutil.copy2(run / audio['file'], output / filename)
                data['response_audio_files'].append(filename)
        write(output / f'{ident}.json', data)
        names.append(ident)
        mapping.append(dict(packet_id=ident, order=row['order'], repetition=row['repetition'],
                            case_id=row['case_id'], arm=row['arm'], status=row['status']))
    secrets.SystemRandom().shuffle(names)
    write(output / 'index.json', dict(packet_ids=names, count=len(names)))
    write(private_key, dict(run=str(run), packets=mapping))
    print(json.dumps(dict(packets=len(names), output=str(output), private_key=str(private_key))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--private-key', required=True, type=Path)
    args = parser.parse_args()
    build(args.run, args.output, args.private_key)
