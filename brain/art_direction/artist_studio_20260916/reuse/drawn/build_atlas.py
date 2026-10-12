"""Index unmodified ImageGen model sheets for the raster preview."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import shutil
import zipfile
from collections import deque

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
EYES = ['round', 'hook', 'arc', 'loop', 'slot', 'chevron', 'bar']
MOUTHS = ['mouth_neutral', 'mouth_smile', 'mouth_angry', 'mouth_sad', 'mouth_flat', 'mouth_worried', 'mouth_skeptical']
EXPECTED = EYES + MOUTHS
EYE_POSES = ['rest', 'anticipation', 'closing', 'closed', 'opening', 'settled']
MOUTH_POSES = ['rest', 'MBP', 'small_AA', 'AA', 'EH', 'EE', 'OH', 'OO', 'FV', 'LNT', 'S', 'SMILE']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_sources():
    obj = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8-sig'))
    obj = obj.get('assets', obj.get('sources', obj)) if isinstance(obj, dict) else obj
    if isinstance(obj, list):
        obj = {entry['id']: entry for entry in obj}
    result = {}
    for key, value in obj.items():
        if key not in EXPECTED:
            continue
        entry = {'source': value} if isinstance(value, str) else dict(value)
        source = entry.get('source') or entry.get('path') or entry.get('file') or entry.get('local_path')
        if source:
            path = Path(source)
            entry['source'] = path if path.is_absolute() else ROOT / path
            result[key] = entry
    return result


def significant_mask(mask):
    """Keep meaningful cyan components; ignore detached single-pixel noise."""
    try:
        from scipy.ndimage import label
        labels, count = label(mask)
        sizes = np.bincount(labels.ravel())
        sizes[0] = 0
        threshold = max(12, int(sizes.max(initial=0) * .003))
        kept = sizes >= threshold
        kept[0] = False
        return kept[labels], int(count), int(np.count_nonzero(kept))
    except ImportError:
        visited = np.zeros(mask.shape, dtype=bool)
        components = []
        for y, x in zip(*np.nonzero(mask)):
            if visited[y, x]:
                continue
            queue = deque([(y, x)])
            visited[y, x] = True
            component = []
            while queue:
                py, px = queue.popleft()
                component.append((py, px))
                for ny, nx in [(py-1, px), (py+1, px), (py, px-1), (py, px+1)]:
                    if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        queue.append((ny, nx))
            components.append(component)
        threshold = max(12, int(max(map(len, components), default=0) * .003))
        output = np.zeros(mask.shape, dtype=bool)
        kept = 0
        for component in components:
            if len(component) >= threshold:
                rows, cols = zip(*component)
                output[rows, cols] = True
                kept += 1
        return output, len(components), kept


def analyze(key, entry):
    source = entry['source']
    before = digest(source)
    with Image.open(source) as image:
        pixels = np.asarray(image.convert('RGBA')).astype(np.int16)
    height, width = pixels.shape[:2]
    kind = 'eye' if key in EYES else 'mouth'
    columns = entry.get('columns', 3 if kind == 'eye' else 4)
    rows = entry.get('rows', 2 if kind == 'eye' else 3)
    poses = entry.get('poses', EYE_POSES if kind == 'eye' else MOUTH_POSES)
    frame_offset = entry.get('frameOffset', 0)
    if frame_offset < 0 or frame_offset + len(poses) > columns * rows:
        raise ValueError(f'{key}: poses extend beyond sheet grid')
    frames = []
    checks = []
    column_edges = entry.get('columnEdges', [round(i * width / columns) for i in range(columns + 1)])
    row_edges = entry.get('rowEdges', [round(i * height / rows) for i in range(rows + 1)])
    if len(column_edges) != columns + 1 or len(row_edges) != rows + 1:
        raise ValueError(f'{key}: incorrect cell boundaries')
    if column_edges[0] != 0 or column_edges[-1] != width or row_edges[0] != 0 or row_edges[-1] != height:
        raise ValueError(f'{key}: cell boundaries must span the source image')
    for index in range(len(poses)):
        sheet_index = index + frame_offset
        col, row = sheet_index % columns, sheet_index // columns
        x0, x1 = column_edges[col:col+2]
        y0, y1 = row_edges[row:row+2]
        cell = pixels[y0:y1, x0:x1]
        r, g, b, a = cell.transpose(2, 0, 1)
        cyan = (a >= 96) & (g-r > 20) & (b-r > 15) & (g > 100) & (b > 100)
        ink, components, kept = significant_mask(cyan)
        yy, xx = np.nonzero(ink)
        if len(xx) < 12:
            raise ValueError(f'{key} frame {index}: no meaningful cyan artwork')
        left, right = int(xx.min()+x0), int(xx.max()+x0+1)
        top, bottom = int(yy.min()+y0), int(yy.max()+y0+1)
        bounds = {'x': left, 'y': top, 'w': right-left, 'h': bottom-top}
        # Fixed baseline and horizontal registration correct sheet placement drift.
        # Frame widths/heights remain unchanged; there is no per-frame rescaling.
        pivot_x = (left+right)/2
        pivot_y = bottom if kind == 'eye' else top
        padding = 3
        crop = {'x': max(x0, left-padding), 'y': max(y0, top-padding)}
        crop['w'] = min(x1, right+padding)-crop['x']
        crop['h'] = min(y1, bottom+padding)-crop['y']
        frames.append({
            'index': index, 'pose': poses[index],
            **crop, 'cx': pivot_x, 'cy': pivot_y,
            'cell': {'x': x0, 'y': y0, 'w': x1-x0, 'h': y1-y0},
            'cropBounds': crop, 'inkBounds': bounds,
            'geometricCenter': {'x': (left+right)/2, 'y': (top+bottom)/2},
            'registration': {'anchorX': pivot_x-x0, 'anchorY': pivot_y-y0,
                             'method': 'horizontal-center-lower-lid' if kind == 'eye' else 'horizontal-center-upper-mouth'},
            'inkPixels': int(ink.sum()), 'components': kept,
        })
        checks.append({'frame': index, 'inkPixels': int(ink.sum()), 'detectedComponents': components,
                       'retainedComponents': kept, 'touchesCellEdge': bool(left<=x0+2 or top<=y0+2 or right>=x1-2 or bottom>=y1-2)})
    output = ROOT / entry.get('output', f'sheets/{key}.png')
    output.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != output.resolve():
        shutil.copyfile(source, output)
    assert digest(source) == before == digest(output), f'Source bytes changed for {key}'
    first = frames[0]['inkBounds']
    extra_sources = []
    override = entry.get('frameOverrides')
    if override:
        if kind != 'mouth':
            raise ValueError('Frame overrides currently support mouth artwork only')
        override_entry = dict(override)
        override_source = Path(override_entry['source'])
        override_entry['source'] = override_source if override_source.is_absolute() else ROOT / override_source
        replacement, replacement_checks = analyze(key, override_entry)
        relative_width = float(override_entry.get('widthRelativeToRest', .72))
        if not 0 < relative_width <= 1.5:
            raise ValueError('Replacement width must be relative to the original resting mouth')
        # One scale for the complete replacement family keeps its drawn proportions.
        source_scale = float(override_entry.get('sourceScale', first['w'] * relative_width / replacement['masterWidth']))
        if not 0 < source_scale <= 4:
            raise ValueError('Replacement source scale must be finite and positive')
        by_pose = {frame['pose']: frame['index'] for frame in frames}
        if set(override_entry['poses']) != {'FV', 'LNT', 'TH'}:
            raise ValueError('The reviewed replacement must contain exactly FV, LNT and TH')
        for replacement_frame, check in zip(replacement['frames'], replacement_checks['frames']):
            index = by_pose[replacement_frame['pose']]
            frames[index] = {**replacement_frame, 'index': index, 'file': replacement['file'],
                             'sha256': replacement['sha256'], 'sourceScale': source_scale}
            checks[index] = {**check, 'frame': index, 'file': replacement['file']}
        extra_sources.append({key: replacement[key] for key in ('file', 'sha256', 'imageWidth', 'imageHeight')})
    asset = {'id': key, 'file': output.relative_to(ROOT).as_posix(), 'kind': kind,
             'imageWidth': width, 'imageHeight': height, 'columns': columns, 'rows': rows,
             'frameOffset': frame_offset,
             'masterWidth': first['w'], 'masterHeight': first['h'],
             'maxWidth': max(frame['inkBounds']['w'] * frame.get('sourceScale', 1) for frame in frames),
             'maxHeight': max(frame['inkBounds']['h'] * frame.get('sourceScale', 1) for frame in frames),
             'anchor': 'bottom' if kind == 'eye' else 'top',
             'frames': frames, 'sha256': before,
             'hasTransparentPixels': bool(np.any(pixels[:,:,3] < 250)),
             'registration': 'constant scale, horizontal center, lower eye baseline / upper mouth baseline',
             'provenance': 'ImageGen raster source copied without modification'}
    if extra_sources:
        asset['extraSources'] = extra_sources
    widths = [f['inkBounds']['w'] * f.get('sourceScale', 1) for f in frames]
    quality = {'widthRatioToRest': [round(w / first['w'], 3) for w in widths],
               'heightRatioToRest': [round(f['inkBounds']['h'] * f.get('sourceScale', 1) / first['h'], 3) for f in frames],
               'loopWidthChange': round(abs(widths[-1] - widths[0]) / widths[0], 3),
               'note': 'Ratios flag candidates for visual review; narrowing is expected for rounded speech shapes.'}
    return asset, {'sha256': before, 'copiedByteForByte': True, 'extraSources': extra_sources,
                   'frames': checks, 'shapeMetrics': quality}


def write_json(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def inherit_mouth(base, artwork, entry):
    """Share safe articulation cels while keeping each emotional aperture distinct."""
    asset = copy.deepcopy(base)
    asset.update(id=artwork['id'], label=entry.get('label', artwork['id'].removeprefix('mouth_')),
                 inherits=base['id'], allowSmileCue=False)
    scale = float(entry.get('sourceScale', 221.75 / (artwork['imageWidth'] / artwork['columns'])))
    if not 0 < scale <= 4:
        raise ValueError('Invalid emotion sheet scale')
    slots = {frame['pose']: frame['index'] for frame in asset['frames']}
    for frame in artwork['frames']:
        if frame['pose'] not in slots:
            raise ValueError(f"Unknown inherited mouth pose: {frame['pose']}")
        index = slots[frame['pose']]
        asset['frames'][index] = {**frame, 'index': index, 'file': artwork['file'],
                                  'sha256': artwork['sha256'], 'sourceScale': scale}
    # SMILE is an old speech-study label. Negative/flat families never borrow a grin.
    index = slots['SMILE']
    asset['frames'][index] = {**asset['frames'][slots['rest']], 'index': index,
                              'pose': 'SMILE', 'aliasOf': 'rest'}
    asset['maxWidth'] = max(f['inkBounds']['w'] * f.get('sourceScale', 1) for f in asset['frames'])
    asset['maxHeight'] = max(f['inkBounds']['h'] * f.get('sourceScale', 1) for f in asset['frames'])
    asset.setdefault('extraSources', []).append({key: artwork[key] for key in ('file', 'sha256', 'imageWidth', 'imageHeight')})
    return asset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-partial', action='store_true')
    parser.add_argument('--no-pack', action='store_true', help='Update metadata without replacing the downloadable archive')
    args = parser.parse_args()
    sources = read_sources()
    assets, checks = {}, {}
    for key in EXPECTED:
        if key in sources and sources[key]['source'].exists():
            assets[key], checks[key] = analyze(key, sources[key])
            parent = sources[key].get('inherits')
            if parent:
                if parent not in assets:
                    raise ValueError(f'Mouth family {key} requires earlier source {parent}')
                artwork = assets[key]
                assets[key] = inherit_mouth(assets[parent], artwork, sources[key])
                checks[key]['inherits'] = parent
                checks[key]['selectedFrameCount'] = len(assets[key]['frames'])
    missing = [key for key in EXPECTED if key not in assets]
    if missing and not args.allow_partial:
        raise ValueError('Missing ImageGen sheets: ' + ', '.join(missing))
    atlas = {'version': 4, 'fps': 15, 'assets': assets, 'expectedAssets': EXPECTED,
             'missingAssets': missing, 'sourceType': 'ImageGen raster sheets',
             'notes': ['Source images are copied byte for byte. Bounds and pivots are metadata.',
                       'Each sequence has a fixed scale. No sprite is stretched to fit its individual bounds.',
                       'A frame.file overrides the source sheet; sourceScale maps that replacement family into the original sheet coordinates.',
                       'The preview removes the white background at display time; downloaded sheets remain original.',
                       'Generated open and settled poses can differ. The preview may reuse the rest pose to close a loop.']}
    family_map = ROOT / 'mouth_family_map_v4.json'
    if family_map.exists():
        mapping = json.loads(family_map.read_text(encoding='utf-8'))
        atlas['mouthFamilies'] = mapping['faces']
        atlas['mouthFamilyLabels'] = mapping['labels']
        for family in atlas['mouthFamilies'].values():
            if family not in assets:
                raise ValueError('Face refers to missing mouth family: ' + family)
        for family, label in mapping['labels'].items():
            if family in assets:
                assets[family]['label'] = label
    write_json('atlas.json', atlas)
    (ROOT / 'atlas.js').write_text('window.MIST_DRAWN_ATLAS = ' + json.dumps(atlas, separators=(',', ':')) + ';\n', encoding='utf-8')
    validation = {'complete': not missing, 'assetCount': len(assets),
                  'frameCount': sum(len(a['frames']) for a in assets.values()),
                  'expectedAssetCount': len(EXPECTED), 'expectedFrameCount': sum(len(a['frames']) for a in assets.values()),
                  'missingAssets': missing, 'sourceBytesPreserved': True,
                  'checks': checks, 'limits': ['Frame detection validates populated cells and source integrity, not animation quality.',
                                               'Sprite pose labels are the prompt order; visual review is required.',
                                               'Asset integrity does not establish voice synchronisation; playback tests are separate.']}
    write_json('validation.json', validation)
    (ROOT / 'asset_notes.txt').write_text(
        'MIST drawn animation study\n\n'
        f"Seven eye families and {len(MOUTHS)} mouth assets contain {validation['frameCount']} selected pose entries.\n"
        'Emotion families share safe rounded sounds and closures; selected pose entries can reuse source cels.\n'
        'Artwork: ImageGen. Existing MIST contours supplied as references.\n'
        'Source PNGs are unchanged. White background removal happens in the browser.\n\n'
        'atlas.json contains full cell rectangles, ink bounds, padded crop bounds and pivots.\n'
        'cx/cy are absolute sheet coordinates. registration.anchorX/anchorY are relative to the cell.\n'
        'Eyes use the lower lid baseline; mouths use the upper mouth baseline.\n'
        'Use one constant scale per sequence. Do not resize each frame to the same bounds.\n'
        'The current renderer targets 15 fps. Blink poses have timed holds; the audio clock stays independent.\n'
        'FV, LNT and TH use separately reviewed replacement cels when frame.file is present.\n'
        'Multiply source offsets and dimensions by frame.sourceScale, default 1. Never draw the old sheet for those cels.\n'
        'atlas.mouthFamilies maps all source faces to an explicit speaking-mouth family.\n'
        'These are reusable family studies; they do not represent 40 independently drawn face animations.\n'
        'The silent study demonstrates poses. Voice tests follow scheduled audio playback.\n'
        'Energy-only samples show timing, not phoneme recognition.\n', encoding='utf-8')
    if args.no_pack:
        print(json.dumps({'assets': len(assets), 'frames': validation['frameCount'], 'fps': atlas['fps'], 'missing': missing,
                          'sourceBytesPreserved': True, 'packageUnchanged': True}))
        return
    package = ROOT / 'MIST_drawn_animation_pack.zip'
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
        include = ['atlas.json', 'atlas.js', 'validation.json', 'asset_notes.txt', 'prompts.json', 'revised_prompts.json', 'generated_blinks.json', 'generated_mouths.json', 'hook_prompt.txt']
        include += [asset['file'] for asset in assets.values()]
        include += [frame['file'] for asset in assets.values() for frame in asset['frames'] if frame.get('file')]
        for name in dict.fromkeys(include):
            path = ROOT / name
            if path.exists():
                archive.write(path, name)
    with zipfile.ZipFile(package) as archive:
        assert archive.testzip() is None
        for key, asset in assets.items():
            assert hashlib.sha256(archive.read(asset['file'])).hexdigest() == asset['sha256']
            for frame in asset['frames']:
                if frame.get('file'):
                    assert hashlib.sha256(archive.read(frame['file'])).hexdigest() == frame['sha256']
    print(json.dumps({'assets': len(assets), 'frames': validation['frameCount'], 'missing': missing,
                      'packBytes': package.stat().st_size, 'sourceBytesPreserved': True}))


if __name__ == '__main__':
    main()
