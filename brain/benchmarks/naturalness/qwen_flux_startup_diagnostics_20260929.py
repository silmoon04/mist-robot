"""Summarize redacted server trace failure classes for the finished pilot."""
import argparse
import json
from pathlib import Path


def classify(events):
    emitted = [row.get('event', {}) for row in events]
    tts = next((e for e in emitted if e.get('event') == 'tts_connect_failed'), None)
    if tts:
        return 'elevenlabs_tts_connect', tts.get('error_type')
    if any(e.get('type') == 'error' and e.get('message') == 'Deepgram streaming connection failed'
           for e in emitted):
        return 'deepgram_asr_connect', 'streaming_connection_failed'
    model = next((e for e in emitted if e.get('type') == 'debug_model'
                  and e.get('phase') == 'model_failed'), None)
    if model:
        errors = model.get('errors', [])
        if any('ConnectTimeout' in str(error) for error in errors):
            return 'cerebras_model_connect', 'ConnectTimeout'
        return 'model_request', 'redacted_model_failure'
    return 'unknown', 'see_private_trace'


def main(run: Path, trace_root: Path, output: Path):
    if output.exists():
        raise FileExistsError(output)
    attempts = json.loads((run / 'attempts.json').read_text(encoding='utf-8'))
    diagnostics = []
    for row in attempts:
        if row['status'] == 'complete':
            continue
        identity = next((e.get('trace_id') for e in row['events']
                         if e.get('type') == 'studio_session'), None)
        trace_path = trace_root / str(identity) / 'events.jsonl'
        events = [json.loads(line) for line in trace_path.read_text(encoding='utf-8').splitlines()]
        component, error_type = classify(events)
        diagnostics.append(dict(order=row['order'], case_id=row['case_id'], arm=row['arm'],
            status=row['status'], ready_observed=bool(row.get('ready_ms')),
            input_started=bool(row.get('input_start_ms')), duration_ms=row['duration_ms'],
            component=component, error_type=error_type,
            trace_events_path=str(trace_path.relative_to(run.parent))))
    output.write_text(json.dumps(dict(noncomplete_attempts=diagnostics,
        note='Classified from redacted local server trace events; no retries or substitutions.'),
        indent=2), encoding='utf-8')
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--trace-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    main(args.run, args.trace_root, args.output)
