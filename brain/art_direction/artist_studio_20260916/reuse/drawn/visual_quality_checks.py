"""Read-only raster measurements. These are review clues, not a quality score."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent


def registered_ink(image, frame):
    rgb = np.asarray(image.convert('RGB')).astype(np.int16)
    x, y, w, h = (frame[k] for k in ('x', 'y', 'w', 'h'))
    tile = rgb[y:y+h, x:x+w]
    mask = (tile.max(axis=2)-tile.min(axis=2) >= 22) & (tile[:, :, 1] > tile[:, :, 0]+10)
    yy, xx = np.nonzero(mask)
    scale = frame.get('sourceScale', 1)
    px = np.floor((xx+x-frame['cx'])*scale+.5).astype(int)
    py = np.floor((yy+y-frame['cy'])*scale+.5).astype(int)
    points = set(zip(px.tolist(), py.tolist()))
    return points, mask


def iou(a, b):
    return len(a & b)/max(1, len(a | b))


def main():
    atlas_path = ROOT/'atlas.json'
    atlas = json.loads(atlas_path.read_text(encoding='utf-8'))
    assets = {}
    for name, asset in atlas['assets'].items():
        source_paths = {asset['file'], *(frame['file'] for frame in asset['frames'] if frame.get('file'))}
        images = {file: Image.open(ROOT/file) for file in source_paths}
        masks, measurements = [], []
        for frame in asset['frames']:
            image = images[frame.get('file', asset['file'])]
            points, mask = registered_ink(image, frame)
            masks.append(points)
            coords = np.array(list(points), dtype=float)
            measurements.append({
                'index': frame['index'], 'pose': frame['pose'],
                'file': frame.get('file', asset['file']), 'sourceScale': frame.get('sourceScale', 1),
                'ink_pixels': len(points),
                'width': round(float(mask.any(axis=0).sum()) * frame.get('sourceScale', 1), 3),
                'height': round(float(mask.any(axis=1).sum()) * frame.get('sourceScale', 1), 3),
                'centroid_from_pivot': np.mean(coords, axis=0).round(2).tolist() if len(coords) else None,
                'components_reported_by_atlas': frame.get('components'),
            })
        pairs = []
        for n in range(len(masks)):
            previous = (n-1) % len(masks)
            pairs.append({'from': previous, 'to': n, 'registered_ink_iou': round(iou(masks[previous], masks[n]), 4),
                          'width_change_fraction_of_rest': round((measurements[n]['width']-measurements[previous]['width'])/max(1, measurements[0]['width']), 4)})
        seam = max(iou(masks[0], {(x+dx, y+dy) for x, y in masks[-1]}) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        assets[name] = {'sheet_sha256': hashlib.sha256((ROOT/asset['file']).read_bytes()).hexdigest(),
                        'selected_sheet_sha256': {file: hashlib.sha256((ROOT/file).read_bytes()).hexdigest() for file in sorted(source_paths)},
                        'frames': measurements, 'adjacent_changes': pairs,
                        'rest_to_last_iou_with_one_pixel_tolerance': round(seam, 4),
                        'note': 'Last cel is only a loop seam for eye sheets. Mouth last cels are separate poses.'}
        for image in images.values():
            image.close()
    report = {'checked_at': datetime.now(timezone.utc).isoformat(),
              'atlas_sha256': hashlib.sha256(atlas_path.read_bytes()).hexdigest(),
              'assets': assets,
              'measurements_only': True,
              'review_notes_for_v4_sources': [
                  {'asset': 'mouth_angry', 'finding': 'Tense downturned rest with blunt, level vowel apertures. Angry eyes carry much of the emotion during the open vowels.'},
                  {'asset': 'mouth_sad', 'finding': 'Downturned corners continue through AA, EH, EE and closing shapes. Original silent resting faces remain unchanged.'},
                  {'asset': 'mouth_flat', 'finding': 'Level capsules and apertures avoid a smile curve. Wide close is shallow but not thinner than the generated rest capsule.'},
                  {'asset': 'mouth_worried', 'finding': 'Tense rest and tall rounded vowels. Wide consonants rely on the worried eyes for emotional context.'},
                  {'asset': 'mouth_skeptical', 'finding': 'Consistent right-end-higher asymmetry across eight new poses. One family scale preserves relative dimensions.'},
                  {'asset': 'runtime_v4', 'finding': 'All 40 faces have explicit reviewed mouth-family assignments. Seven requested poses plus release were newly drawn for each of five families; the happy set and shared rounded vowels and closures are retained. Source PNG bytes are unchanged.'},
              ],
              'review_notes_for_v3_sources': [
                  {'asset': 'mouth_neutral', 'finding': 'FV is a compressed capsule, LNT a shallow bowl, and TH a small oval. The previous upper notches and lower tongue-like tab are absent.'},
                  {'asset': 'mouth_smile', 'finding': 'All three replacement consonants use continuous broad curves without localized notches, tabs, holes or teeth. One scale from the sheet cell dimensions preserves their relative proportions.'},
                  {'asset': 'runtime_v3', 'finding': 'The current renderer samples animation geometry at 15 fps while speech uses the current output clock. Six new source cels replace only FV, LNT and TH; other poses and exact original resting identities are retained.'},
              ],
              'review_notes_for_v2_sources': [
                  {'asset': 'round', 'finding': 'The new near-closed gap and low reopening pose improve the progression. Adjacent width changes are smaller. Rest and settled contours differ more than v1; use rest again to close the loop if the seam is noticeable.'},
                  {'asset': 'loop', 'finding': 'The reopening pose is connected instead of splitting into two arcs. The crossbar disappears through closure and returns as the eye opens. Rest and settled contours have the largest loop seam difference among the new eye sets.'},
                  {'asset': 'arc', 'finding': 'The closure now flattens the arch without reversing its curvature. Width stays nearly constant, making this a clearer squeeze.'},
                  {'asset': 'hook', 'finding': 'Closing and reopening now have narrow-gap intermediate poses. Width remains stable.'},
                  {'asset': 'chevron', 'finding': 'The angle narrows through closing instead of shrinking the whole glyph. This better preserves the eye identity.'},
                  {'asset': 'mouth_neutral', 'finding': 'Release, small AA, wide close, and round close provide useful intermediate silhouettes. FV and LNT are still visually similar symbolic notches; do not describe them as anatomically accurate lip shapes.'},
                  {'asset': 'mouth_smile', 'finding': 'The smile set keeps slightly raised corners in some poses, but much of its speech still resembles the neutral set. This is a reusable symbolic mouth library rather than detailed human lip sync.'},
              ],
              'review_notes_for_v1_sources': [
                  {'asset': 'round', 'finding': 'Opening cel 4 is much narrower than the settled eye. Closing cel 2 is already a closed arc, leaving no near-closed gap breakdown.'},
                  {'asset': 'loop', 'finding': 'Opening cel 4 splits into two arcs and drops the crossbar. This changes the loop identity before the settled cel restores it.'},
                  {'asset': 'hook', 'finding': 'The gradual closing sequence is clearer than round and loop. Reopening jumps from the closed stroke to a large gap in one cel.'},
                  {'asset': 'arc', 'finding': 'The closure changes curvature and is visible. Lowering and reopening cels remain broad arches, so the final curvature flip is abrupt.'},
                  {'asset': 'slot', 'finding': 'Closing and opening preserve the narrow slot. The closed arc is a deliberate shape change; the generated settled slot is slightly skewed versus the horizontal rest.'},
                  {'asset': 'chevron', 'finding': 'Lowering mostly shrinks the chevron before an abrupt switch to an arc. A bent narrow-chevron breakdown would make the action read better.'},
                  {'asset': 'bar', 'finding': 'The pinch bends an already closed bar and becomes narrower. It is visible motion, not an eyelid covering an aperture.'},
                  {'asset': 'mouth_neutral', 'finding': 'Core silhouettes are usable, but AA, EH, EE and rounded lips need transitional drawings to avoid popping. FV and LNT are symbolic poses, not anatomically differentiated lips.'},
                  {'asset': 'mouth_smile', 'finding': 'Rest and SMILE are visibly cheerful, but most speaking silhouettes closely match the neutral set. Expression-specific mouth character is weak during speech.'},
                  {'asset': 'runtime_v1', 'finding': 'At 8 fps, 30 ms anticipation and 50 ms lowering can both be skipped. Holding closure alone prevents a missed blink but does not prevent a rest-to-closed jump.'},
                  {'asset': 'runtime_v1', 'finding': 'Speech phase ends by switching generated mouths at fixed position 50,46.5 back to each original expression mouth without a transition. This can visibly pop for unlike source mouths.'},
              ],
              'limits': ['No source pixels are changed.', 'Silhouette IoU measures shape difference, not perceived quality. Large changes can be intentional.',
                         'Visual notes are versioned. Earlier notes describe earlier sheets, including consonant shapes that are no longer selected.',
                         'These measurements do not establish voice timing or perceived animation quality.']}
    (ROOT/'visual_quality_checks.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({name: {'rest_to_last_iou': a['rest_to_last_iou_with_one_pixel_tolerance'],
                              'max_width_jump_fraction': max(abs(p['width_change_fraction_of_rest']) for p in a['adjacent_changes'])}
                      for name, a in assets.items()}, indent=2))


if __name__ == '__main__':
    main()
