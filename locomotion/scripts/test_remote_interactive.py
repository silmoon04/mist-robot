"""Bounded interactive-remote checks; no HTTP server, policy job or hardware.

One real fast episode reset checks construction and cleanup. Other paths use
isolated environments while exercising the actual reset/command methods.
"""
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from locomotion import sim_remote as legacy
from locomotion import sim_remote_interactive as interactive
from locomotion.scripts import remote_session_fast


def dormant_simulation(mode="fast"):
    simulation = interactive.InteractiveSimulation.__new__(interactive.InteractiveSimulation)
    simulation.lock = threading.RLock()
    simulation.mode = mode
    simulation.clock_generation = 0
    simulation.env = SimpleNamespace(command=np.zeros(3), close=Mock())
    return simulation


class StandInEnv:
    instances = []

    def __init__(self, **kwargs):
        self.arguments = kwargs
        self.cfg = deepcopy(kwargs.get("config", interactive.load_config()))
        self.gait = SimpleNamespace(cycle_s=3.2)
        self.closed = False
        self.instances.append(self)

    def reset(self, seed):
        return np.zeros(47), {"time_s": 0., "seed": seed}

    def render(self):
        return np.zeros((4, 4, 3), dtype=np.uint8)

    def close(self):
        self.closed = True


class InteractiveRemoteTests(unittest.TestCase):
    def test_fast_supervisor_rejects_a_legacy_simulator_on_the_same_port(self):
        for state, ready in (({"controller": "ik"}, False),
                             ({"controller": "fast", "interactive": {"version": 1}}, True)):
            with self.subTest(state=state), \
                    patch.object(remote_session_fast, "base_health", return_value={"ready": True, "mode": "simulation"}), \
                    patch("urllib.request.urlopen", return_value=io.StringIO(json.dumps(state))):
                status = remote_session_fast.health("simulation")
                self.assertEqual(status["ready"], ready)
                if not ready:
                    self.assertEqual(status["mode"], "legacy-simulation")

    def test_selected_fast_config_is_an_independent_copy_of_frozen_values(self):
        original = interactive.load_config()
        candidate = interactive.fast_config()
        self.assertEqual(candidate["actuator"]["command_speed_rad_s"], 1.8)
        self.assertEqual(candidate, original)
        self.assertIsNot(candidate, original)
        self.assertIsNot(candidate["actuator"], original["actuator"])
        self.assertEqual(interactive.load_config(), original)

    def test_actual_command_preserves_fast_speed_and_caps_legacy_modes(self):
        for mode, limit in (("fast", .025), ("ik", .012), ("ppo", .012), ("sac", .012)):
            with self.subTest(mode=mode):
                simulation = dormant_simulation(mode)
                simulation.command({"command": [.025, -.025, 0.]})
                expected = min(.025, limit)
                np.testing.assert_array_equal(simulation.env.command, [expected, -expected, 0.])
                simulation.command({"command": [1., -1., 1.]})
                yaw_limit = interactive.PROFILE["max_yaw_rad_s"] if mode == "fast" else .06
                np.testing.assert_array_equal(simulation.env.command, [limit, -limit, yaw_limit])
                simulation.command({"command": [0., 0., 0.]})
                np.testing.assert_array_equal(simulation.env.command, np.zeros(3))
                with self.assertRaises(ValueError):
                    simulation.command({"command": [float("nan"), 0., 0.]})

    def test_legacy_and_policy_reset_use_original_environment_without_fast_config(self):
        policy = SimpleNamespace(predict=Mock())
        loader = SimpleNamespace(load=Mock(return_value=policy))
        modules = {"stable_baselines3": SimpleNamespace(PPO=loader, SAC=loader)}
        checkpoint = REPO / "locomotion/runs/ppo_51200/checkpoint_51200.zip"
        for mode in ("ik", "ppo", "sac"):
            with self.subTest(mode=mode):
                simulation = dormant_simulation()
                old = simulation.env
                StandInEnv.instances = []
                data = {"controller": mode, "seed": 42, "sensor_mode": "mpu6050",
                        "checkpoint": str(checkpoint), "terrain": "flat", "payload": .155}
                with patch.object(legacy, "MistEnv", StandInEnv), \
                        patch.object(interactive, "fast_config", side_effect=AssertionError("Legacy mode entered fast config")), \
                        patch.object(legacy, "verify_checkpoint", return_value={"status": "training_candidate_hardware_unvalidated"}) as verify, \
                        patch.dict(sys.modules, modules):
                    simulation.reset(data)
                self.assertEqual(simulation.env.cfg, interactive.load_config())
                self.assertNotIn("config", StandInEnv.instances[-1].arguments)
                self.assertEqual(simulation.mode, mode)
                self.assertEqual(simulation.clock_generation, 1)
                old.close.assert_called_once()
                if mode == "ik":
                    verify.assert_not_called()
                    self.assertIsNone(simulation.policy)
                else:
                    self.assertEqual(verify.call_args.args[1], mode)
                    self.assertEqual(verify.call_args.kwargs["sensor_mode"], "mpu6050")
                    self.assertIs(simulation.policy, policy)

    def test_single_real_fast_reset_and_failed_candidate_preserve_existing_episode(self):
        # Suppress the background loop: construct exactly one real episode.
        with patch.object(legacy.threading.Thread, "start"):
            simulation = interactive.InteractiveSimulation()
        try:
            self.assertEqual(simulation.mode, "fast")
            self.assertIsInstance(simulation.env.gait, interactive.WideRecoveryFastCrawl)
            self.assertEqual(simulation.env.gait.cycle_s, 1.2)
            self.assertEqual(simulation.env.gait.cycle_s, interactive.PROFILE["cycle_s"])
            self.assertEqual(simulation.env.gait.shift_m, .001875)
            self.assertEqual(simulation.env.gait.shift_m, interactive.PROFILE["shift_m"])
            self.assertEqual(simulation.env.gait.recovery_start, .82)
            self.assertEqual(simulation.env.gait.recovery_start, interactive.PROFILE["recovery_start"])
            self.assertEqual(simulation.env.servos.speed, 1.8)
            self.assertEqual(simulation.env.servos.cap, interactive.load_config()["actuator"]["torque_limit_nm"])
            bullet = interactive.p
            bodies = [simulation.env._call(bullet.getBodyUniqueId, index)
                      for index in range(simulation.env._call(bullet.getNumBodies))]
            visual_grid = set(bodies) - {simulation.env.robot, simulation.env.floor}
            self.assertTrue(visual_grid, "Flat fast preview should contain visible world landmarks")
            for body in visual_grid:
                self.assertFalse(simulation.env._call(bullet.getCollisionShapeData, body, -1))
                self.assertEqual(simulation.env._call(bullet.getDynamicsInfo, body, -1)[0], 0.)
            state = simulation.state()
            self.assertEqual(state["interactive"]["max_translation_m_s"], .025)
            self.assertEqual(state["interactive"]["default_translation_m_s"], .025)
            self.assertEqual(state["setup"]["randomize"], False)
            self.assertEqual(state["interactive"]["real_time_factor"], 0.)
            json.dumps(state, allow_nan=False)
            with patch.object(Path, "read_bytes", return_value=b'changed after profile was loaded'):
                self.assertEqual(simulation.state()["interactive"]["profile_sha256"],
                                 state["interactive"]["profile_sha256"],
                                 "Reported profile identity must describe the loaded settings")
            existing, old_info, generation = simulation.env, simulation.info, simulation.clock_generation
            candidate = StandInEnv(config=interactive.fast_config())
            candidate.reset = Mock(side_effect=ValueError("retained failed reset"))
            with patch.object(interactive, "MistEnv", return_value=candidate):
                with self.assertRaisesRegex(ValueError, "retained failed reset"):
                    simulation.reset({"controller": "fast"})
            self.assertTrue(candidate.closed)
            self.assertIs(simulation.env, existing)
            self.assertIs(simulation.info, old_info)
            self.assertEqual(simulation.clock_generation, generation)
            with self.assertRaisesRegex(ValueError, "checkpoint"):
                simulation.reset({"controller": "fast", "checkpoint": "any-policy.zip"})
            self.assertIs(simulation.env, existing)
            simulation.command({"command": [.025, 0., 0.]})
            np.testing.assert_array_equal(simulation.env.command, [.025, 0., 0.])
        finally:
            simulation.running = False
            simulation.env.close()

    def test_worker_uses_fixed_steps_and_bounds_catchup_after_a_render_stall(self):
        simulation = dormant_simulation()
        simulation.running, simulation.stopped, simulation.policy = True, False, None
        simulation.clock_steps, simulation.last_command = 0, -1.
        simulation.env.dt, simulation.env.substeps = .001, 20
        simulation.env.command = np.array([.025, 0., 0.])
        simulation.env.step = Mock(return_value=(np.zeros(47), 0., False, False, {"time_s": .02}))
        clock, sleeps = [0.], []
        def render():
            clock[0] += .8
        simulation._render = Mock(side_effect=render)
        def sleep(seconds):
            sleeps.append(seconds)
            clock[0] += seconds
            if len(sleeps) == 3:
                simulation.running = False
        with patch.object(interactive.time, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(interactive.time, "sleep", side_effect=sleep):
            simulation.worker()
        self.assertEqual(simulation.clock_steps, 3)
        self.assertEqual(simulation.env.step.call_count, 3)
        self.assertEqual((simulation.env.dt, simulation.env.substeps), (.001, 20))
        np.testing.assert_array_equal(simulation.env.command, np.zeros(3))
        self.assertGreater(sleeps[1], .01, "Long render stalls must not create an unbounded catch-up burst")


if __name__ == "__main__":
    unittest.main()
