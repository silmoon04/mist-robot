"""Measure fallback mouth-family wait from saved speech, without network calls."""
import json
import math
from pathlib import Path
import struct
import wave

ROOT = Path(__file__).resolve().parents[2]
rows = []
for path in sorted((ROOT / 'brain/art_direction/artist_studio_20260916/reuse/drawn/audio').glob('*.wav')):
    with wave.open(str(path), 'rb') as sound:
        rate, channels, width = sound.getframerate(), sound.getnchannels(), sound.getsampwidth()
        if width != 2:
            rows.append({'file': path.name, 'skipped': 'not signed 16 bit PCM'})
            continue
        values = [value[0] / 32768 for value in struct.iter_unpack('<h', sound.readframes(sound.getnframes()))]
    samples = [sum(values[i:i + channels]) / channels for i in range(0, len(values), channels)]
    step = round(rate * .02)
    runs, start, count = [], None, 0
    for index in range(0, len(samples), step):
        chunk = samples[index:index + step]
        rms = math.sqrt(sum(value * value for value in chunk) / len(chunk))
        if rms >= .006:
            if start is None:
                start = index / rate
            count += 1
        elif start is not None:
            runs.append({'start_s': round(start, 3), 'duration_s': round(index / rate - start, 3)})
            start = None
    if start is not None:
        runs.append({'start_s': round(start, 3), 'duration_s': round(len(samples) / rate - start, 3)})
    rows.append({'file': path.name, 'duration_s': round(len(samples) / rate, 3),
                 'fallback_AA_runs': len(runs), 'longest_unchanged_AA_s': max((run['duration_s'] for run in runs), default=0),
                 'runs_over_600ms': [run for run in runs if run['duration_s'] > .6]})
report = {'method': 'Exact browser fallback rule: 20 ms RMS windows, rest below 0.006 and AA otherwise.',
          'scope': 'Saved six speech fixtures, analyzed without provider character alignment. This measures the audio-energy fallback, not aligned cue timing.',
          'clips': rows,
          'worst_case': 'An indefinitely sustained voiced sound has no cue boundary; the current family latch can therefore wait indefinitely.'}
target = ROOT / 'brain/harness/mouth_family_wait_analysis.json'
target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
