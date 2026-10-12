"""Select reviewed replacement sheets without changing original image bytes."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parent
EYE_POSES = ['rest', 'anticipation', 'closing', 'near_closed', 'closed', 'opening_low', 'opening', 'settled']
MOUTH_POSES = ['rest', 'MBP', 'release', 'small_AA', 'AA', 'EH', 'EE', 'OH', 'OO', 'FV', 'LNT', 'S', 'TH', 'wide_close', 'round_close', 'SMILE']


def save_baseline():
    for name in ['atlas.json', 'validation.json', 'sources.json', 'visual_quality_checks.json']:
        backup = ROOT / ('v1_' + name)
        if not backup.exists() and (ROOT / name).exists():
            shutil.copyfile(ROOT / name, backup)


def main():
    save_baseline()
    sources = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8-sig'))
    # Existing sheets are already project assets. Do not depend on external generated-image paths.
    for key in sources:
        if isinstance(sources[key], str):
            sources[key] = {'source': f'sheets/{key}.png'}
    accepted = []
    mouths = 'sheets/mouth_combined_v2.png'
    if (ROOT / mouths).exists():
        for key, offset in [('mouth_neutral', 0), ('mouth_smile', 16)]:
            sources[key] = {'source': mouths, 'output': mouths, 'columns': 4, 'rows': 8,
                            'frameOffset': offset, 'poses': MOUTH_POSES}
            accepted.append(key)
    reviewed_mouths = ROOT / 'reviewed_mouth_sources_v3.json'
    if reviewed_mouths.exists():
        for key, override in json.loads(reviewed_mouths.read_text(encoding='utf-8-sig')).items():
            assert key in ('mouth_neutral', 'mouth_smile'), key
            assert (ROOT / override['source']).exists(), key
            sources[key]['frameOverrides'] = override
    reviewed_emotions = ROOT / 'reviewed_mouth_sources_v4.json'
    if reviewed_emotions.exists():
        for key, entry in json.loads(reviewed_emotions.read_text(encoding='utf-8-sig')).items():
            assert (ROOT / entry['source']).exists(), key
            sources[key] = entry
            accepted.append(key)
    # Eye replacements are selected explicitly once their visual review is complete.
    reviewed = ROOT / 'reviewed_eye_sources.json'
    if reviewed.exists():
        for key, entry in json.loads(reviewed.read_text(encoding='utf-8-sig')).items():
            assert (ROOT / entry['source']).exists(), key
            sources[key] = {**entry, 'poses': EYE_POSES}
            accepted.append(key)
    (ROOT / 'sources.json').write_text(json.dumps(sources, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'selected': accepted}))


if __name__ == '__main__':
    main()
