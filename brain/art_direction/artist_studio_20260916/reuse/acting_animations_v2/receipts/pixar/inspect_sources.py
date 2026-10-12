from pathlib import Path
from PIL import Image
from scipy.ndimage import label, find_objects
import numpy as np
import hashlib
import json

root = Path(__file__).resolve().parents[2]
generated = Path('<LOCAL_HOME>/.codex/generated_images/01a0ed20-8602-7551-beeb-41c181be54bb')
files = {'recall': 'exec-e368d907-5fb4-46f4-9b6c-1856e60a3dce.png', 'checking': 'exec-c3a25637-3b03-4ca8-a4fb-8a2c8c8689a8.png', 'discovery': 'exec-0dcdbbf7-0be8-43d5-a228-7aed2439b940.png'}
for name, filename in files.items():
    p = root / 'source' / 'pixar' / (name + '.png')
    im = Image.open(p)
    a = np.array(im)[:, :, 3]
    frames = []
    for frame in range(12):
        col, row = frame % 4, frame // 4
        x0, x1 = round(col * im.width / 4), round((col + 1) * im.width / 4)
        y0, y1 = round(row * im.height / 3), round((row + 1) * im.height / 3)
        mask = a[y0:y1, x0:x1] > 128
        labs, _ = label(mask)
        pieces = []
        for component, region in enumerate(find_objects(labs), start=1):
            if region is None:
                continue
            area = int((labs[region] == component).sum())
            if area < 100:
                continue
            ys, xs = region
            pieces.append({'bbox': [xs.start, ys.start, xs.stop, ys.stop], 'area': area})
        pieces.sort(key=lambda part: (part['bbox'][1], part['bbox'][0]))
        frames.append({'frame': frame, 'rect': [x0, y0, x1 - x0, y1 - y0], 'significantComponents': pieces})
    receipt = {
        'group': 'pixar', 'example': name, 'tool': 'built-in image_gen.imagegen',
        'generationCount': 2, 'originalGeneratedPath': str(generated / filename),
        'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'mode': im.mode, 'size': list(im.size),
        'transparentBackgroundRequested': True, 'nonzeroAlphaFraction': float((a > 0).mean()),
        'opaqueAlphaFraction': float((a > 200).mean()),
        'prompts': ['prompts/pixar/' + name + '.txt', 'prompts/pixar/' + name + '-blink-fix.txt'],
        'referencePoses': ['acting_studies_v1/poses/pixar/' + name + '_' + str(i) + '.png' for i in range(3)],
        'visualInspection': 'Inspected all 12 drawings composited over dark. Actual alpha has clear background and pupil holes. Flat second generation improves blink silhouettes. Exactly 12 faces; independent left eye, right eye and mouth. Row placement drifts vertically and requires per-cell translation registration in compiler. Do not infer background from raw RGB preview: transparent pixels retain cyan fog RGB.',
        'frames': frames,
    }
    (root / 'receipts' / 'pixar' / (name + '.json')).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(name, receipt['sha256'], [len(frame['significantComponents']) for frame in frames])
