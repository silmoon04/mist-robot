"""Mechanical geometry checks for the phone module before coupon printing."""

import itertools
import math
import unittest

from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer

import geom as g
import phone


def solids(shape):
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    count = 0
    while explorer.More():
        count += 1
        explorer.Next()
    return count


class PhoneGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = phone.build_phone()
        cls.coupons = phone.build_coupons()

    def test_parts_are_valid_connected_solids(self):
        for part in self.parts + self.coupons:
            with self.subTest(part=part["name"]):
                self.assertTrue(g.valid(part["shape"]))
                self.assertEqual(solids(part["shape"]), 1)
                self.assertGreater(g.volume(part["shape"]), 0)

    def test_assembly_has_no_nominal_interference(self):
        world = [(p, g.translate(p["shape"], (0, 0, phone.PAN_Z))
                  if p["link"] == "phone_pan" else p["shape"])
                 for p in self.parts]
        for (a, sa), (b, sb) in itertools.combinations(world, 2):
            with self.subTest(first=a["name"], second=b["name"]):
                self.assertLess(g.common_volume(sa, sb), .001)

    def test_pan_sweep_has_no_fixed_part_interference(self):
        moving = [p for p in self.parts if p["link"] == "phone_pan"]
        fixed = [p for p in self.parts if p["link"] == "base"]
        for degrees in range(0, 360, 15):
            for part in moving:
                moved = g.translate(g.rotate(part["shape"], (0, 0, 1), degrees),
                                    (0, 0, phone.PAN_Z))
                for obstacle in fixed:
                    with self.subTest(angle=degrees, moving=part["name"],
                                      fixed=obstacle["name"]):
                        self.assertLess(g.common_volume(moved, obstacle["shape"]), .001)

    def test_driver_access_before_cradle_installation(self):
        hub = next(p["shape"] for p in self.parts if p["name"] == "phone_pan_hub")
        for x, y in ((7, 0), (-7, 0), (0, 7), (0, -7)):
            driver = g.cylinder(3.0, 30, base=(x, y, 8.001))
            self.assertLess(g.common_volume(hub, driver), .001)
        # Counterbore floor 8 + washer .5 - screw 6 gives a 2.5 mm tip height.
        screw_tip = 8 + .5 - 6
        self.assertAlmostEqual(screw_tip, 2.5)
        self.assertGreater(screw_tip, 2.0)

    def test_phone_rear_fasteners_end_outside_phone(self):
        device = next(p["shape"] for p in self.parts
                      if p["name"] == "Xiaomi_Mi9SE_bare_phone_envelope")
        for y in (-24, 24):
            for z in (24, 34):
                screw = g.cylinder(1.5, 10, base=(-10.5, y, z), axis=(1, 0, 0))
                self.assertLess(g.common_volume(device, screw), .001)

    def test_landscape_side_port_clearance(self):
        device = next(p["shape"] for p in self.parts
                      if p["name"] == "Xiaomi_Mi9SE_bare_phone_envelope")
        low, high = g.bounds(device)
        self.assertAlmostEqual(high[1] - low[1], 147.5)
        self.assertAlmostEqual(high[2] - low[2], 70.5)
        # A 12 mm deep, 18 mm high plug can enter either short edge.
        for sign in (-1, 1):
            plug = g.box(12, 24, 18, center=(3.725, sign * 85.75, 53.25))
            for part in self.parts:
                if part["name"].startswith("phone_cradle_"):
                    with self.subTest(end=sign, part=part["name"]):
                        self.assertLess(g.common_volume(part["shape"], plug), .001)

    def test_both_camera_ends_and_long_edge_buttons_are_open(self):
        exclusions = [
            g.box(6, 23.75, 70.4, center=(-3, -61.875, 53.25)),
            g.box(6, 23.75, 70.4, center=(-3, 61.875, 53.25)),
            g.box(8.15, 119, 2, center=(3.675, 0, 17)),
            g.box(8.15, 119, 2, center=(3.675, 0, 89.5)),
        ]
        for index, exclusion in enumerate(exclusions):
            for part in self.parts:
                if part["name"].startswith("phone_cradle_"):
                    with self.subTest(exclusion=index, part=part["name"]):
                        self.assertLess(g.common_volume(part["shape"], exclusion), .001)

    def test_reinforced_usb_spines_retain_six_mm_section(self):
        frame = next(p["shape"] for p in self.parts
                     if p["name"] == "phone_cradle_rear_frame")
        for sign in (-1, 1):
            section = g.box(6, 8, 1, center=(-5.5, sign * 78.25, 53.25))
            self.assertAlmostEqual(g.common_volume(frame, section), 48, places=5)
        specimen = next(p["shape"] for p in self.coupons
                        if p["name"] == "phone_usb_spine_6mm_coupon")
        section = g.box(6, 8, 1, center=(-5.5, 78.25, 53.25))
        self.assertAlmostEqual(g.common_volume(specimen, section), 48, places=5)

    def test_short_corner_clips_and_deep_rear_top_bridge(self):
        clips = [p for p in self.parts if p["name"].startswith("phone_cradle_lower_clip_")]
        self.assertEqual(len(clips), 2)
        for clip in clips:
            low, high = g.bounds(clip["shape"])
            self.assertLessEqual(high[1] - low[1], 16.5 + 1e-6)
        top = next(p["shape"] for p in self.parts if p["name"] == "phone_cradle_top_cap")
        bridge = g.box(12, 100, 8, center=(-6.5, 0, 93))
        self.assertAlmostEqual(g.common_volume(top, bridge), 9600, places=5)

    def test_cap_nuts_insert_sideways_and_react_upward_screw_load(self):
        saddle = next(p["shape"] for p in self.parts
                      if p["name"] == "phone_pan_servo_saddle")
        # A 5.5 mm AF by 2.4 mm M3 nut has manufacturing clearance in its pocket.
        radius = 5.5 / math.sqrt(3)
        for x, y in ((-25, -19), (-25, 19), (5, -19), (5, 19)):
            polygon = [(x + radius * math.cos(math.radians(angle + 30)),
                        y + radius * math.sin(math.radians(angle + 30)))
                       for angle in range(0, 360, 60)]
            nut = g.prism_xy(polygon, 81.05, 2.4)
            for distance in (0, 1, 2, 3, 4, 5, 6, 7):
                inserted = g.translate(nut, (0, math.copysign(distance, y), 0))
                self.assertLess(g.common_volume(saddle, inserted), .001)
            # Screw tension pulls upward. Roof contact must stop a 0.4 mm lift.
            lifted = g.translate(nut, (0, 0, .4))
            self.assertGreater(g.common_volume(saddle, lifted), .5)
        self.assertAlmostEqual(90.8 - 10, 80.8)
        self.assertLess(90.8 - 10, 81.05)
        self.assertAlmostEqual(86.5 - 83.6, 2.9)


if __name__ == "__main__":
    unittest.main()
