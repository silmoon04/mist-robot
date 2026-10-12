"""Check the selected replacement artwork and preserve unrelated poses."""
import hashlib
import json
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1] / 'art_direction/artist_studio_20260916/reuse/drawn'


class AnimationAtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atlas = json.loads((ROOT / 'atlas.json').read_text(encoding='utf-8'))
        cls.before = json.loads((ROOT / 'v2_atlas.json').read_text(encoding='utf-8'))

    def test_only_six_mouth_drawings_change(self):
        replacements = []
        for name in self.before['assets']:
            asset = self.atlas['assets'][name]
            old = self.before['assets'][name]
            self.assertEqual(asset['masterWidth'], old['masterWidth'])
            self.assertEqual(asset['masterHeight'], old['masterHeight'])
            self.assertEqual(len(asset['frames']), len(old['frames']))
            for frame, previous in zip(asset['frames'], old['frames']):
                if name.startswith('mouth_') and frame['pose'] in ('FV', 'LNT', 'TH'):
                    replacements.append((name, frame['pose']))
                    self.assertEqual(frame['file'], 'sheets/mouth_consonants_v3.png')
                    self.assertAlmostEqual(frame['sourceScale'], 221.75 / 512)
                else:
                    self.assertEqual(frame, previous, (name, frame['pose']))
        self.assertEqual(len(replacements), 6)
        self.assertEqual(self.atlas['fps'], 15)

    def test_selected_sources_match_their_hashes(self):
        for asset in self.atlas['assets'].values():
            self.assertEqual(hashlib.sha256((ROOT / asset['file']).read_bytes()).hexdigest(), asset['sha256'])
            for frame in asset['frames']:
                if frame.get('file'):
                    self.assertEqual(hashlib.sha256((ROOT / frame['file']).read_bytes()).hexdigest(), frame['sha256'])

    def test_replacement_crops_contain_registered_single_shapes(self):
        audit = json.loads((ROOT / 'mouth_consonants_v3_validation.json').read_text(encoding='utf-8'))
        by_pose = {(f['family'], f['pose']): f for f in audit['frames']}
        for name in ('mouth_neutral', 'mouth_smile'):
            for frame in self.atlas['assets'][name]['frames']:
                if not frame.get('file'):
                    continue
                expected = by_pose[name, frame['pose']]
                # The independent audit uses a stricter cyan edge threshold.
                # Its antialiased outline can differ by one source pixel.
                for key in ('x', 'y', 'w', 'h'):
                    self.assertLessEqual(abs(frame['inkBounds'][key] - expected['inkBounds'][key]), 1)
                self.assertLessEqual(abs(frame['cx'] - expected['cx']), .5)
                self.assertLessEqual(abs(frame['cy'] - expected['cy']), 1)
                self.assertEqual(frame['components'], 1)
                with Image.open(ROOT / frame['file']) as image:
                    pixels = np.asarray(image.convert('RGB')).astype(np.int16)
                x, y, w, h = (frame[k] for k in ('x', 'y', 'w', 'h'))
                crop = pixels[y:y+h, x:x+w]
                ink = (crop[:, :, 1] - crop[:, :, 0] > 20) & (crop[:, :, 2] - crop[:, :, 0] > 15)
                self.assertGreater(int(ink.sum()), 1000)
                self.assertFalse(ink[0].any() or ink[-1].any() or ink[:, 0].any() or ink[:, -1].any())
                # A single interval per column rejects holes and split silhouettes.
                for column in ink.T:
                    indices = np.flatnonzero(column)
                    if len(indices):
                        self.assertEqual(len(indices), int(indices[-1] - indices[0] + 1))


if __name__ == '__main__':
    unittest.main()
