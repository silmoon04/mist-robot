"""Create a versioned fixture copy with two explicit supplemental controls."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import wave

from synthesize_inputs import load_env, read_pcm, synthesize, wav


ANNOTATIONS = {
    'audio_backchannel_mhm': 'The second acknowledgement starts after playback becomes idle, not during the same explanation. Repeated overlapping backchannels are not tested by this fixture.',
    'audio_soft_voice': 'One normal synthesized voice is attenuated to gain 0.12. Quiet-speaker delivery, multiple speakers and calibrated microphone sound levels are not tested.',
    'audio_background_late': 'No background job is requested and no late result is injected. Reading the seed is not a background-task receipt. This fixture tests a topic-change interruption only.',
    'adaptive_backchannel_pair': 'The original fixture contains only the acknowledgement branch, with no quiet/echo delivery sweep. Its trigger is 150 ms after first playback, not 400 ms after an identified audible clause. A separate supplemental correction control is present in this version.',
    'queue_depth_correction': 'The correction starts 150 ms after first playback, not after a completed audible clause. Meaningful delivered words and a playful starting face must be confirmed from the capture.',
    'audio_emotion_switch': 'The seed asks for a line to be read; it does not request a playful starting face. A transition away from a playful face is only exercised if that starting expression is observed.',
    'audio_silence': 'The resume step waits for a playback-idle event. A correctly silent acknowledgement with no playback can cause a fixture trigger timeout; that timeout alone is not a conversation failure.',
    'audio_offer_reversal': 'The clauses are synthesized independently and joined with an exact silent gap. Continuous-speaker prosody through an unfinished thought is not established.',
    'audio_long_pause': 'The three fragments are synthesized independently and joined with exact silent gaps. Slow-speaker prosody and multiple speakers are not established. A supplemental control removes the inserted gaps while preserving the speech bytes.',
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def duration_ms(path: Path) -> float:
    with wave.open(str(path), 'rb') as handle:
        return 1000 * handle.getnframes() / handle.getframerate()


def extend(source: Path, destination: Path) -> dict:
    source = source.resolve()
    destination = destination.resolve()
    if source == destination or source in destination.parents:
        raise ValueError('Destination must be a separate new directory, outside the source directory.')
    if destination.exists():
        raise FileExistsError(f'Refusing to overwrite existing output: {destination}')
    manifest_path = source / 'manifest.json'
    source_hash = sha(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    originals = {f['id'].split('.')[-1]: f for f in manifest['fixtures']}
    acknowledgement = originals['adaptive_backchannel_pair']
    paused = originals['audio_long_pause']
    if len(acknowledgement['steps']) != 2 or len(paused['steps']) != 1:
        raise ValueError('Unexpected original control structure')
    segments = paused['steps'][0]['segments']
    if len(segments) != 3:
        raise ValueError('Expected exactly three original slow-speech segments')
    shutil.copytree(source, destination)
    audio = destination / 'audio'
    for fixture in manifest['fixtures']:
        slug = fixture['id'].split('.')[-1]
        if slug == 'audio_background_late':
            fixture['conditions_uncontrolled'] = [value for value in fixture.get('conditions_uncontrolled', [])
                if value != 'Actual background jobs may run; prescribed delayed-result timing is not injected in this audio run.']
        if slug in ANNOTATIONS:
            fixture.setdefault('conditions_uncontrolled', []).append(ANNOTATIONS[slug])

    text = 'Actually, explain the knee instead.'
    key = load_env()['DEEPGRAM_API_KEY']
    cache_name = synthesize(text, audio, key)
    correction_name = 'supplemental-adaptive-correction.wav'
    shutil.copyfile(audio / cache_name, audio / correction_name)
    correction = copy.deepcopy(acknowledgement)
    correction['id'] = 'mist.fixture_control.v1.adaptive_correction'
    correction['title'] = 'Early-playback correction control for the acknowledgement fixture'
    correction['source_case_id'] = acknowledgement['id']
    correction['coverage_role'] = 'supplemental_control_not_a_new_suite_case'
    correction['pair_kind'] = 'same first user audio and same playback-relative trigger; generated assistant content can vary'
    correction['steps'][1].update(file=correction_name, duration_ms=duration_ms(audio / correction_name),
        segments=[{'text': text, 'start_ms': 0.0, 'end_ms': duration_ms(audio / correction_name)}])
    correction['conditions_uncontrolled'] = [
        'Only the normal-gain near-end branch is present; quiet/echo delivery conditions are not swept.',
        'Both branches use 150 ms after first playback, not an identified clause boundary. Assistant wording can vary between runs.',
        'Synthetic input does not establish human backchannel prosody or physical microphone behavior.',
    ]
    correction['rubric'] = [
        'The direct correction takes the floor when it overlaps active playback.',
        'The next answer discusses the knee rather than continuing the obsolete phone-pan explanation.',
        'Compare false yield on the acknowledgement with missed correction here; retain failed or absent overlap as unavailable.',
    ]

    original_audio = read_pcm(source / 'audio' / paused['steps'][0]['file'])
    continuous_pcm = bytearray()
    continuous_segments = []
    for segment in segments:
        first = round(segment['start_ms'] * 32)
        last = round(segment['end_ms'] * 32)
        if first % 2 or last % 2 or not 0 <= first < last <= len(original_audio):
            raise ValueError('Invalid original segment PCM boundaries')
        start = len(continuous_pcm) / 32
        continuous_pcm.extend(original_audio[first:last])
        continuous_segments.append({'text': segment['text'], 'start_ms': start, 'end_ms': len(continuous_pcm) / 32})
    continuous_name = 'supplemental-long-pause-continuous.wav'
    wav(audio / continuous_name, continuous_pcm)
    continuous = copy.deepcopy(paused)
    continuous['id'] = 'mist.fixture_control.v1.long_pause_continuous'
    continuous['title'] = 'The same three speech fragments without inserted silence'
    continuous['source_case_id'] = paused['id']
    continuous['coverage_role'] = 'supplemental_control_not_a_new_suite_case'
    continuous['pair_kind'] = 'same speech PCM bytes, with only the two inserted silent gaps removed'
    continuous['steps'][0].update(file=continuous_name, segments=continuous_segments,
        duration_ms=len(continuous_pcm) / 32)
    continuous['conditions_uncontrolled'] = [
        'Fragments retain their independently synthesized prosody and any internal leading/trailing silence; only inserted gaps are removed.',
        'This control does not add a second speaker or natural continuous human speech.',
    ]
    continuous['rubric'] = [
        'Recognize the same complete request as the paused fixture.',
        'Do not begin an answer before the final fragment finishes.',
        'Compare early responses and response latency against the paused version using actual segment offsets.',
    ]
    manifest['fixtures'].extend([correction, continuous])
    manifest['version'] = '2026-09-24.2'
    manifest['source_manifest'] = {'path': str(manifest_path), 'sha256': source_hash,
        'version': json.loads(manifest_path.read_text(encoding='utf-8'))['version']}
    manifest['extension'] = {'original_suite_audio_fixtures': len(originals), 'supplemental_controls': 2,
        'new_suite_cases': 0, 'annotations_added': len(ANNOTATIONS),
        'new_synthesis_requests_max': 1,
        'note': 'Original fixture WAVs remain byte-identical. Controls do not increase the 90-case suite coverage.'}
    manifest['assets'] = [{'file': p.name, 'sha256': sha(p), 'duration_ms': duration_ms(p)}
        for p in sorted(audio.glob('*.wav'))]
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    if sha(manifest_path) != source_hash:
        raise RuntimeError('Original manifest changed during extension')
    for original in (source / 'audio').glob('*.wav'):
        if sha(original) != sha(audio / original.name):
            raise RuntimeError(f'Copied WAV differs: {original.name}')
    return {'output': str(destination), 'version': manifest['version'], 'fixtures': len(manifest['fixtures']),
        'supplemental_ids': [correction['id'], continuous['id']], 'original_manifest_sha256': source_hash,
        'manifest_sha256': sha(destination / 'manifest.json'), 'continuous_duration_ms': len(continuous_pcm) / 32}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(extend(args.source, args.output), indent=2))
