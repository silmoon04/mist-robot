"""Measure simulation HTTP latency and visual updates without moving the robot."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import statistics
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def percentile(values, fraction):
    values = sorted(values)
    return values[min(len(values)-1, int((len(values)-1)*fraction+.5))]


def request(url, path, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    req = Request(url+path, data=body, headers={'Content-Type': 'application/json'})
    started = time.monotonic()
    with urlopen(req, timeout=10) as response:
        value = json.load(response)
    return value, (time.monotonic()-started)*1000


def summarize(samples):
    latency = [s['latency_ms'] for s in samples]
    return {'samples': len(samples), 'median_ms': statistics.median(latency),
            'p95_ms': percentile(latency, .95), 'max_ms': max(latency)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8131')
    parser.add_argument('--duration', type=float, default=4.)
    parser.add_argument('--state-path', default='/api/state')
    parser.add_argument('--output', required=True)
    parser.add_argument('--max-p95-ms', type=float, default=80.)
    parser.add_argument('--min-visual-hz', type=float, default=15.)
    args = parser.parse_args()
    parsed = urlparse(args.url)
    if parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.scheme != 'http':
        raise ValueError('Use the local simulation HTTP service')
    initial, _ = request(args.url, '/api/state')
    if 'interactive' not in initial or initial.get('controller') not in ('fast', 'ik', 'ppo', 'sac'):
        raise ValueError('Endpoint is not the interactive simulation remote')
    started = time.monotonic()
    deadline = started+args.duration

    def collect(path, interval, payload=None):
        samples = []
        next_sample = started
        while time.monotonic() < deadline:
            time.sleep(max(0., next_sample-time.monotonic()))
            if time.monotonic() >= deadline:
                break
            value, latency = request(args.url, path, payload)
            sample = {'received_s': time.monotonic()-started, 'latency_ms': latency}
            if payload is None:
                image = value.get('image')
                pose = value.get('pose')
                if isinstance(pose, dict):
                    sample['visual_sequence'] = pose.get('sequence', pose.get('time_s'))
                    sample['visual_source'] = 'pose'
                elif image is not None:
                    sample['visual_sequence'] = hashlib.sha256(image.encode()).hexdigest()
                    sample['visual_source'] = 'jpeg_change'
                sample['simulation_time_s'] = value.get('info', {}).get('time_s')
            samples.append(sample)
            next_sample = max(next_sample+interval, time.monotonic())
        return samples

    with ThreadPoolExecutor(max_workers=2) as executor:
        state = executor.submit(collect, args.state_path, .025)
        command = executor.submit(collect, '/api/command', .1, {'command': [0, 0, 0]})
        state_samples, command_samples = state.result(), command.result()
    # Zero commands also preserve the watchdog's normal UI heartbeat pattern.
    request(args.url, '/api/command', {'command': [0, 0, 0]})
    elapsed = time.monotonic()-started
    sequences = [s.get('visual_sequence') for s in state_samples]
    changes = sum(a is not None and a != b for a, b in zip(sequences[1:], sequences[:-1]))
    span = state_samples[-1]['received_s']-state_samples[0]['received_s']
    result = {'url': args.url, 'state_path': args.state_path, 'duration_s': elapsed,
              'controller': initial['controller'], 'interactive_version': initial['interactive']['version'],
              'state_latency': summarize(state_samples), 'command_latency': summarize(command_samples),
              'observed_visual_updates': changes, 'observed_visual_hz': changes/span,
              'visual_source': state_samples[0].get('visual_source'),
              'thresholds': {'max_p95_ms': args.max_p95_ms, 'min_visual_hz': args.min_visual_hz},
              'state_samples': state_samples, 'command_samples': command_samples}
    failures = []
    for name in ('state_latency', 'command_latency'):
        if result[name]['p95_ms'] >= args.max_p95_ms:
            failures.append(f"{name} p95 {result[name]['p95_ms']:.1f} ms exceeds {args.max_p95_ms:.1f} ms")
    if result['observed_visual_hz'] < args.min_visual_hz:
        failures.append(f"observed visual updates {result['observed_visual_hz']:.1f} Hz below {args.min_visual_hz:.1f} Hz")
    result['failures'], result['passed'] = failures, not failures
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if not k.endswith('_samples')}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
