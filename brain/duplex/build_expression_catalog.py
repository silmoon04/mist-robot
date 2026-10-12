"""Record the source face IDs and their intended use without changing their drawings."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'duplex/face_map.json'
mapping = json.loads(path.read_text(encoding='utf-8'))
source = (ROOT / 'face_assets/app/app_data.js').read_text(encoding='utf-8')
data = json.loads(source.removeprefix('window.MIST_DATA = ').rstrip().removesuffix(';'))
mapping['version'] = 2
mapping['expressions']['uncertain'] = {'primary': '18_misc_2_02_manual', 'alts': []}
uses = {
    'neutral': ('Calm, ordinary conversation or a direct correction.', 2800),
    'happy': ('A warm response to good news or an actual success.', 2800),
    'sad': ('A requested sad face. The tear variants are theatrical; avoid them for a routine apology.', 2200),
    'alert': ('A brief attention cue or a stop acknowledgement.', 1400),
    'bored': ('A requested bored face or an invited dry joke.', 2200),
    'dead_inside': ('A deliberately flat reaction, only when requested or clearly invited.', 1600),
    'error': ('A recoverable problem. Explain the actual problem calmly.', 1800),
    'smug': ('A playful, self-satisfied reaction when that tone is welcome.', 1800),
    'curious': ('Interest in a question or a new detail.', 2600),
    'sleepy': ('A requested sleepy expression or a rest cue.', 3000),
    'angry': ('A requested angry expression or roleplay. Do not use toward someone correcting you.', 1400),
    'love': ('Affection when invited by the person.', 2200),
    'suspicious': ('Playful doubt, not a claim about the person.', 1800),
    'surprised': ('A short reaction to something unexpected.', 1500),
    'panic': ('A requested exaggerated reaction. Do not use for ordinary delays or tool errors.', 1200),
    'listening': ('Compatibility preset. The interface normally owns the listening state.', 2200),
    'thinking': ('Compatibility preset. The interface normally owns thinking and gaze.', 2200),
    'mischief': ('An invited mischievous joke.', 1700),
    'proud': ('Quiet satisfaction after a real achievement.', 2400),
    'embarrassed': ('A brief, light awkward reaction when it fits.', 1800),
    'uncertain': ('A mild uncertain reaction. Say what is uncertain.', 1800),
}
for name, preset in mapping['expressions'].items():
    preset['use'], preset['duration_ms'] = uses[name]
mapping['faces'] = {}
for face in data['faces']:
    references = []
    for name, preset in mapping['expressions'].items():
        for index, face_id in enumerate([preset['primary'], *preset.get('alts', [])]):
            if face_id == face['id']:
                references.append({'expression': name, 'variant': index})
    if not references:
        raise ValueError('Face is not available through a named preset: ' + face['id'])
    mapping['faces'][face['id']] = {
        'name': face['name'], 'group': face['group'], 'talk_safe': face['talkSafe'],
        'calls': references,
        'parts': {slot: record['part'] for slot, record in face['slots'].items() if slot != 'tears'},
    }
mapping['control'] = {
    'min_duration_ms': 400, 'max_duration_ms': 6000, 'cooldown_ms': 450,
    'max_queued_age_ms': 1200,
    'speech_driver': 'audible_audio_only',
    'state_rule': 'Listening, thinking and speaking preserve a current expression. Barge-in clears it.',
    'variant_rule': 'Variant 0 is the primary face. Omit variant for ordinary conversation.',
}
path.write_text(json.dumps(mapping, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'faces': len(mapping['faces']), 'presets': len(mapping['expressions']),
                  'not_talk_safe': [key for key, value in mapping['faces'].items() if not value['talk_safe']]}))
