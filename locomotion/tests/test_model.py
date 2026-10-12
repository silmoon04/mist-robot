"""Check CAD joint frames, mass accounting, IK and simulator FK."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from kinematics import LIMITS, NEUTRAL, forward, inverse, jacobian, foot_in_body
from model import LEGS, JOINT_NAMES, MOUNTS, REPO, export_models, load_config


class KinematicsTests(unittest.TestCase):
    def test_neutral_matches_cad_frames(self):
        np.testing.assert_allclose(forward(NEUTRAL), [.122313648, 0, -.143025947], atol=5e-8)

    def test_round_trip_over_all_limits(self):
        rng = np.random.default_rng(3215)
        samples = rng.uniform(LIMITS[:, 0], LIMITS[:, 1], (200, 3))
        samples = np.vstack([samples, LIMITS[:, 0], LIMITS[:, 1], NEUTRAL])
        for q in samples:
            np.testing.assert_allclose(inverse(forward(q)), q, atol=1e-9)

    def test_body_frame_round_trip(self):
        from kinematics import inverse_body
        for leg in LEGS:
            np.testing.assert_allclose(inverse_body(foot_in_body(NEUTRAL, MOUNTS[leg]), MOUNTS[leg]), NEUTRAL, atol=1e-10)

    def test_bad_targets_are_rejected(self):
        for point in ([1, 0, 0], [0, 0, -.1], [float("nan"), 0, 0], [0, 0]):
            with self.assertRaises(ValueError):
                inverse(point)
        with self.assertRaises(ValueError):
            inverse(forward([1.1, .5, 1.4]))
        with self.assertRaises(ValueError):
            inverse([.122, 0, -.143], elbow="unknown")

    def test_analytic_jacobian(self):
        eps = 1e-6
        for q in (NEUTRAL, [.25, .2, .5], [-.5, .7, 1.7]):
            numeric = np.column_stack([(forward(np.asarray(q) + eps*np.eye(3)[i]) - forward(np.asarray(q) - eps*np.eye(3)[i])) / (2*eps) for i in range(3)])
            np.testing.assert_allclose(jacobian(q), numeric, atol=1e-9)


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="mist-model-test-")
        cls.paths = export_models(Path(cls.temp.name))
        cls.root = ET.parse(cls.paths["quadruped"]).getroot()
        cls.single = ET.parse(cls.paths["single_leg"]).getroot()
        cls.report = json.loads(cls.paths["report"].read_text())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_twelve_actuated_source_axes_and_limits(self):
        joints = [j for j in self.root.findall("joint") if j.get("type") == "revolute"]
        self.assertEqual(tuple(j.get("name") for j in joints), JOINT_NAMES)
        for index, joint in enumerate(joints):
            axis = np.fromstring(joint.find("axis").get("xyz"), sep=" ")
            np.testing.assert_array_equal(axis, [0, 0, 1] if index % 3 == 0 else [0, 1, 0])
            np.testing.assert_allclose([float(joint.find("limit").get(k)) for k in ("lower", "upper")], LIMITS[index % 3])

    def test_bench_removed_only_from_free_robot(self):
        self.assertTrue(self.single.findall(".//visual[@name='bench_mounting_plate']"))
        self.assertFalse(self.root.findall(".//visual[@name='bench_mounting_plate']"))
        self.assertAlmostEqual(self.report["bench_removed"]["removed_mass_kg"], .06908948633599166)
        self.assertAlmostEqual(self.report["bench_removed"]["remaining_base_mass_kg"], .08745987637442381)

    def test_source_moving_inertials_preserved(self):
        source = ET.parse(REPO / load_config()["sources"]["leg_urdf"]).getroot()
        for leg in LEGS:
            for part in ("coxa", "femur", "tibia"):
                src = source.find(f"link[@name='{part}']/inertial")
                dst = self.root.find(f"link[@name='{leg}_{part}']/inertial")
                self.assertAlmostEqual(float(src.find("mass").get("value")), float(dst.find("mass").get("value")), places=14)
                np.testing.assert_allclose(np.fromstring(src.find("origin").get("xyz"), sep=" "), np.fromstring(dst.find("origin").get("xyz"), sep=" "), atol=1e-15)
                for key in src.find("inertia").attrib:
                    self.assertAlmostEqual(float(src.find("inertia").get(key)), float(dst.find("inertia").get(key)), places=14)

    def test_only_primitive_collisions_and_resolved_visuals(self):
        for robot in (self.root, self.single):
            for collision in robot.findall(".//collision"):
                self.assertIsNone(collision.find("geometry/mesh"))
            for mesh in robot.findall(".//visual/geometry/mesh"):
                self.assertTrue((Path(self.temp.name) / mesh.get("filename")).is_file())

    def test_payload_and_mass_shift_are_explicit(self):
        folder = Path(self.temp.name) / "variant"
        paths = export_models(folder, phone_mass_kg=0, body_mass_scale=1.2, body_com_shift=[.01, -.02, 0], link_mass_scale=.9)
        variant = ET.parse(paths["quadruped"]).getroot()
        self.assertIsNone(variant.find("link[@name='phone']"))
        nominal_body = self.root.find("link[@name='body']/inertial")
        shifted = variant.find("link[@name='body']/inertial")
        self.assertAlmostEqual(float(shifted.find("mass").get("value")), float(nominal_body.find("mass").get("value")) * 1.2)
        np.testing.assert_allclose(np.fromstring(shifted.find("origin").get("xyz"), sep=" "), np.fromstring(nominal_body.find("origin").get("xyz"), sep=" ") + [.01, -.02, 0])
        for kwargs in ({"phone_mass_kg": -.1}, {"body_mass_scale": 0}, {"body_com_shift": [0, 0]}):
            with self.assertRaises(ValueError):
                export_models(folder, **kwargs)

    def test_geometry_config_cannot_diverge_from_cad(self):
        config = load_config()
        config["geometry"]["coxa_m"] = .084
        with self.assertRaisesRegex(ValueError, "differ from the source CAD"):
            export_models(Path(self.temp.name), config=config)

    @unittest.skipUnless(importlib.util.find_spec("pybullet"), "PyBullet is not installed")
    def test_pybullet_fk_agrees_for_every_leg(self):
        import pybullet as p
        client = p.connect(p.DIRECT)
        try:
            robot = p.loadURDF(str(self.paths["quadruped"]), useFixedBase=True, flags=p.URDF_USE_INERTIA_FROM_FILE, physicsClientId=client)
            names = {p.getJointInfo(robot, i, physicsClientId=client)[1].decode(): i for i in range(p.getNumJoints(robot, physicsClientId=client))}
            links = {p.getJointInfo(robot, i, physicsClientId=client)[12].decode(): i for i in range(p.getNumJoints(robot, physicsClientId=client))}
            rng = np.random.default_rng(7)
            for trial in range(12):
                for leg in LEGS:
                    q = NEUTRAL if trial == 0 else rng.uniform(LIMITS[:, 0], LIMITS[:, 1])
                    for joint, angle in zip(("yaw", "hip", "knee"), q):
                        p.resetJointState(robot, names[leg + "_" + joint], float(angle), physicsClientId=client)
                    actual = p.getLinkState(robot, links[leg + "_toe"], computeForwardKinematics=True, physicsClientId=client)[4]
                    np.testing.assert_allclose(actual, foot_in_body(q, MOUNTS[leg]), atol=5e-8)
        finally:
            p.disconnect(client)


if __name__ == "__main__":
    unittest.main()
