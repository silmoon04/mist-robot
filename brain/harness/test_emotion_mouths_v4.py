"""Verify emotional speech artwork, mapping and shared source integrity."""
import hashlib
import json
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import label, binary_fill_holes

ROOT = Path(__file__).resolve().parents[1] / 'art_direction/artist_studio_20260916/reuse/drawn'
POSES = ('rest', 'release', 'small_AA', 'AA', 'EH', 'EE', 'LNT', 'wide_close')
NEW = ('mouth_angry', 'mouth_sad', 'mouth_flat', 'mouth_worried', 'mouth_skeptical')


class EmotionMouthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atlas = json.loads((ROOT / 'atlas.json').read_text())
        cls.before = json.loads((ROOT / 'v3_atlas.json').read_text())

    def test_complete_explicit_family_mapping(self):
        mapping = json.loads((ROOT / 'mouth_family_map_v4.json').read_text())
        faces = json.loads((ROOT.parents[3] / 'duplex/face_map.json').read_text())['faces']
        self.assertEqual(set(self.atlas['mouthFamilies']), set(faces))
        self.assertEqual(len(faces), 40)
        self.assertEqual(self.atlas['mouthFamilies'], mapping['faces'])
        self.assertEqual(set(mapping['faces'].values()), set(NEW) | {'mouth_smile'})
        self.assertEqual(self.atlas['fps'], 15)

    def test_existing_happy_and_eye_artwork_remain_exact(self):
        for name, asset in self.before['assets'].items():
            self.assertEqual(self.atlas['assets'][name]['frames'], asset['frames'], name)
            self.assertEqual(self.atlas['assets'][name]['sha256'], asset['sha256'])

    def test_emotional_poses_use_their_own_source(self):
        for name in NEW:
            asset = self.atlas['assets'][name]
            by_pose = {f['pose']: f for f in asset['frames']}
            self.assertEqual(len(by_pose), 16)
            self.assertFalse(asset['allowSmileCue'])
            scales = set()
            for pose in POSES:
                frame = by_pose[pose]
                self.assertEqual(frame['file'], f'sheets/{name}_v4.png')
                self.assertEqual(hashlib.sha256((ROOT / frame['file']).read_bytes()).hexdigest(), frame['sha256'])
                scales.add(frame['sourceScale'])
            self.assertEqual(len(scales), 1, 'One consistent scale per family')
            self.assertEqual(by_pose['SMILE']['aliasOf'], 'rest')
            for key in ('x', 'y', 'w', 'h', 'file', 'sourceScale'):
                self.assertEqual(by_pose['SMILE'][key], by_pose['rest'][key])
            for pose in ('MBP', 'OH', 'OO', 'FV', 'S', 'TH', 'round_close'):
                inherited = next(f for f in self.atlas['assets']['mouth_neutral']['frames'] if f['pose'] == pose)
                self.assertEqual(by_pose[pose], inherited)

    def test_new_shapes_are_populated_clean_and_unclipped(self):
        for name in NEW:
            asset = self.atlas['assets'][name]
            for frame in asset['frames']:
                if frame['pose'] not in POSES:
                    continue
                with Image.open(ROOT / frame['file']) as image:
                    pixels = np.asarray(image.convert('RGBA')).astype(np.int16)
                x, y, w, h = (frame[k] for k in ('x', 'y', 'w', 'h'))
                cell = pixels[y:y+h, x:x+w]
                r, g, b, a = cell.transpose(2, 0, 1)
                ink = (a >= 96) & (g-r > 20) & (b-r > 15) & (g > 100) & (b > 100)
                components, count = label(ink)
                sizes = np.bincount(components.ravel())[1:]
                self.assertEqual(int((sizes >= 12).sum()), 1, (name, frame['pose']))
                self.assertLessEqual(int(sizes[sizes < 12].sum()), 8)
                self.assertFalse(ink[0].any() or ink[-1].any() or ink[:, 0].any() or ink[:, -1].any())
                self.assertLessEqual(int((binary_fill_holes(ink) & ~ink).sum()), 4)


if __name__ == '__main__':
    unittest.main()
