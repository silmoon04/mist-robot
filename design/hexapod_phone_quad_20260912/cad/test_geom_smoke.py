"""Numerical and export smoke checks for the direct-OCP helper."""

import math
import struct
import tempfile
import unittest
from pathlib import Path

import trimesh

import geom as g


class GeometrySmoke(unittest.TestCase):
    def assertVectorAlmostEqual(self, actual, expected, places=7):
        for a, e in zip(actual, expected):
            self.assertAlmostEqual(a, e, places=places)

    def test_geometry_and_exports(self):
        block = g.box(20, 30, 10)
        hole = g.cylinder(3, 14, base=(0, 0, -7))
        part = g.cut(block, hole)
        self.assertTrue(g.valid(part))
        self.assertAlmostEqual(g.volume(part), 6000 - math.pi * 9 * 10, places=6)
        self.assertVectorAlmostEqual(g.centroid(part), (0, 0, 0))
        rotated = g.rotate(part, (0, 0, 1), 90)
        low, high = g.bounds(rotated)
        self.assertVectorAlmostEqual(low, (-15, -10, -5))
        self.assertVectorAlmostEqual(high, (15, 10, 5))

        mass_block = g.box(2, 4, 6, center=(20, 30, 40))
        matrix = g.inertia(mass_block)
        self.assertVectorAlmostEqual([matrix[i][i] for i in range(3)], (208, 160, 80))
        self.assertVectorAlmostEqual([matrix[0][1], matrix[0][2], matrix[1][2]], (0, 0, 0))
        moved = g.transform(g.box(2, 4, 6, center=(1, 2, 3)), (10, 20, 30), (90, 90, 90))
        self.assertVectorAlmostEqual(g.centroid(moved), (13, 22, 29))
        self.assertAlmostEqual(g.volume(moved), 48)

        a, b = g.box(2, 2, 2), g.box(2, 2, 2, center=(1, 0, 0))
        self.assertAlmostEqual(g.volume(g.fuse(a, b)), 12)
        self.assertAlmostEqual(g.common_volume(a, b), 4)
        self.assertAlmostEqual(g.common_volume(a, g.translate(a, (2, 0, 0))), 0)
        self.assertAlmostEqual(g.common_volume(a, g.translate(a, (3, 0, 0))), 0)

        xy = g.prism_xy([(0, 0), (5, 0), (5, 7), (0, 7)], -2, 4)
        xz = g.prism_xz([(0, 0), (5, 0), (5, 7), (0, 7)], -2, 4)
        self.assertAlmostEqual(g.volume(xy), 140)
        self.assertAlmostEqual(g.volume(xz), 140)
        self.assertVectorAlmostEqual(g.bounds(xz)[0], (0, -2, 0))
        self.assertVectorAlmostEqual(g.bounds(xz)[1], (5, 2, 7))

        with tempfile.TemporaryDirectory(prefix="hexapod_quad_geom_smoke_") as temp:
            out = Path(temp)
            step = g.export_step(rotated, out / "part.step")
            roundtrip = g.import_step(step)
            self.assertAlmostEqual(g.volume(roundtrip), g.volume(rotated), places=6)
            for actual, expected in zip(g.bounds(roundtrip), g.bounds(rotated)):
                self.assertVectorAlmostEqual(actual, expected)
            g.export_step([a, g.translate(a, (5, 0, 0))], out / "pair.step")
            self.assertAlmostEqual(g.volume(g.import_step(out / "pair.step")), 16)
            stl = g.export_stl(rotated, out / "part.stl")
            payload = stl.read_bytes()
            triangle_count = struct.unpack_from("<I", payload, 80)[0]
            self.assertEqual(len(payload), 84 + 50 * triangle_count)
            mesh = trimesh.load_mesh(stl, process=True)
            self.assertTrue(mesh.is_watertight)
            self.assertTrue(mesh.is_winding_consistent)
            adjacent = [set() for _ in mesh.faces]
            for i, j in mesh.face_adjacency:
                adjacent[i].add(j)
                adjacent[j].add(i)
            visited, pending = set(), [0]
            while pending:
                face = pending.pop()
                if face not in visited:
                    visited.add(face)
                    pending.extend(adjacent[face] - visited)
            self.assertEqual(len(visited), len(mesh.faces))
            self.assertGreater(mesh.volume, 0)
            self.assertLess(abs(mesh.volume / g.volume(rotated) - 1), 0.001)


if __name__ == "__main__":
    unittest.main(verbosity=2)
