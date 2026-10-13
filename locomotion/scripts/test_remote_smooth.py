"""Pose-stream and motion-boundary regressions; no hardware or training."""
from copy import deepcopy
import hashlib
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
from locomotion import sim_remote_interactive_v2 as smooth
from locomotion.scripts import remote_session_smooth
from locomotion.model import load_config


def dormant():
    sim = smooth.SmoothSimulation.__new__(smooth.SmoothSimulation)
    sim.lock = threading.RLock()
    sim.instance_id, sim.clock_generation = 'test-instance', 0
    sim.clock_start, sim.clock_steps = 0., 0
    sim.env = SimpleNamespace(command=np.zeros(3), close=Mock())
    sim.mode, sim.epoch = 'fast', 'test-instance:0'
    sim.latest_pose = {'version': 1, 'epoch': sim.epoch, 'sequence': 0, 'time_s': 0.,
                       'links': [], 'stopped': False, 'error': None}
    return sim


class Candidate:
    instances = []

    def __init__(self, **arguments):
        self.arguments = arguments
        self.cfg = deepcopy(arguments['config'] if 'config' in arguments else load_config())
        self.command = np.zeros(3)
        self.gait = SimpleNamespace(cycle_s=3.2)
        self.close = Mock()
        self.instances.append(self)

    def reset(self, seed):
        return np.zeros(47), {'time_s': 0., 'seed': seed}


class SmoothRemoteTests(unittest.TestCase):
    def test_supervisor_starts_on_a_free_port_without_mistaking_connection_failure_for_an_occupant(self):
        from urllib.error import URLError
        with patch('urllib.request.urlopen', side_effect=URLError('Connection refused')):
            health = remote_session_smooth.health('simulation')
        self.assertFalse(health['ready'])
        self.assertIsNone(health.get('mode'))
        self.assertIn('Connection refused', health['error'])

    def test_supervisor_rejects_old_image_servers_and_accepts_version_2(self):
        import io
        for version in (None, 1, 2):
            state = {'controller': 'fast', 'interactive': {'version': version},
                     'info': {}, 'sensor': {}, 'pose': {'version': 1, 'links': []}}
            with self.subTest(version=version), \
                    patch.object(remote_session_smooth, 'base_health', return_value={'ready': True, 'mode': 'simulation'}), \
                    patch('urllib.request.urlopen', return_value=io.StringIO(json.dumps(state))):
                self.assertEqual(remote_session_smooth.health('simulation')['ready'], version == 2)

    def test_real_reset_publishes_matching_immutable_epoch_pose_and_meshes_without_rasterization(self):
        with patch.object(legacy.threading.Thread, 'start'), \
                patch.object(smooth.MistEnv, 'render', side_effect=AssertionError('Reset rasterized a frame')):
            sim = smooth.SmoothSimulation()
        try:
            state, pose = sim.state(), sim.pose()
            self.assertNotIn('image', state)
            self.assertEqual(state['interactive']['version'], 2)
            self.assertEqual(sim.model['epoch'], pose['epoch'])
            self.assertEqual({link['index'] for link in sim.model['links']},
                             {link['index'] for link in pose['links']})
            self.assertEqual(pose['sequence'], 0)
            self.assertEqual(pose['time_s'], 0.)
            self.assertGreater(len(sim.meshes), 0)
            for key, content in sim.meshes.items():
                self.assertEqual(hashlib.sha256(content).hexdigest(), key)
                self.assertEqual(sim.asset(f'/viewer/mesh/{key}.stl')[0], content)
            self.assertEqual(sim.env.cfg, smooth.preview_config(1.8))
            import io
            with patch('urllib.request.urlopen', return_value=io.StringIO(json.dumps(state))):
                self.assertTrue(remote_session_smooth.health('simulation')['ready'],
                                'Health must accept the actual image-free producer state')
            json.dumps(state, allow_nan=False)
            old_env, old_epoch, old_pose = sim.env, sim.epoch, sim.pose()
            with patch.object(smooth.MistEnv, 'render', side_effect=AssertionError('Reset rasterized a frame')):
                sim.reset({'controller': 'ik', 'seed': 51, 'payload': 0., 'sensor_mode': 'none'})
            self.assertNotEqual(sim.epoch, old_epoch)
            self.assertEqual(old_pose['epoch'], old_epoch)
            self.assertIsNot(sim.env, old_env)
            self.assertEqual(sim.state()['interactive']['max_translation_m_s'], .012)
            self.assertEqual(sim.state()['setup']['payload'], 0.)
            self.assertEqual(sim.model['epoch'], sim.pose()['epoch'])
            self.assertEqual(sim.env.cfg, smooth.preview_config(1.8))
        finally:
            sim.running = False
            sim.env.close()

    def test_failed_candidate_keeps_the_published_episode_and_closes_the_candidate(self):
        sim = dormant()
        previous, pose, generation = sim.env, sim.latest_pose, sim.clock_generation
        Candidate.instances = []
        with patch.object(smooth, 'ViewerEnv', Candidate), \
                patch.object(smooth, 'model_metadata', side_effect=ValueError('Bad visual metadata')):
            with self.assertRaisesRegex(ValueError, 'Bad visual metadata'):
                sim.reset({'controller': 'fast'})
        Candidate.instances[-1].close.assert_called_once()
        self.assertIs(sim.env, previous)
        self.assertIs(sim.latest_pose, pose)
        self.assertEqual(sim.clock_generation, generation)
        previous.close.assert_not_called()
        with patch.object(smooth, 'ViewerEnv', side_effect=AssertionError('Checkpoint reached fast construction')):
            with self.assertRaisesRegex(ValueError, 'checkpoint'):
                sim.reset({'controller': 'fast', 'checkpoint': 'old-policy.zip'})

    def test_worker_publishes_50_hz_fixed_steps_and_expires_commands_without_rendering(self):
        sim = dormant()
        sim.running, sim.stopped, sim.policy, sim.last_command = True, False, None, 0.
        sim.env.dt, sim.env.substeps, sim.env.step_count = .001, 20, 0
        sim.env.command = np.array([.02, 0., 0.])
        sim._render = Mock(side_effect=AssertionError('Worker attempted rasterization'))
        clock, commands = [0.], []

        def step(action):
            commands.append(sim.env.command.copy())
            sim.env.step_count += 1
            return np.zeros(47), 0., False, False, {'time_s': sim.env.step_count*.02}

        def snapshot(env, epoch, stopped=False):
            return {'version': 1, 'epoch': epoch, 'sequence': env.step_count,
                    'time_s': env.step_count*.02, 'links': [], 'stopped': stopped, 'error': None}

        def sleep(seconds):
            clock[0] += seconds
            if sim.env.step_count == 23:
                sim.running = False

        sim.env.step = Mock(side_effect=step)
        first_pose = sim.pose()
        with patch.object(smooth.time, 'monotonic', side_effect=lambda: clock[0]), \
                patch.object(smooth.time, 'sleep', side_effect=sleep), \
                patch.object(smooth, 'pose_snapshot', side_effect=snapshot):
            sim.worker()
        sim._render.assert_not_called()
        self.assertEqual(sim.clock_steps, 23)
        self.assertEqual((sim.env.dt, sim.env.substeps), (.001, 20))
        self.assertGreater(commands[0][0], 0.)
        np.testing.assert_array_equal(commands[-1], np.zeros(3))
        self.assertEqual(first_pose['sequence'], 0)
        self.assertEqual(sim.pose()['sequence'], 23)
        self.assertAlmostEqual(sim.pose()['time_s'], .46)

    def test_worker_failure_publishes_error_and_zero_command_in_the_same_epoch(self):
        sim = dormant()
        sim.running, sim.stopped, sim.policy, sim.last_command = True, False, None, 0.
        sim.env.dt, sim.env.substeps = .001, 20
        sim.env.command = np.array([.02, 0., 0.])
        sim.env.step = Mock(side_effect=RuntimeError('step failed'))
        old_pose = sim.pose()
        with patch.object(smooth.time, 'monotonic', return_value=0.), \
                patch.object(smooth.time, 'sleep', side_effect=lambda _: setattr(sim, 'running', False)):
            sim.worker()
        self.assertTrue(sim.stopped)
        self.assertEqual(sim.pose()['error'], 'step failed')
        self.assertEqual(sim.pose()['epoch'], old_pose['epoch'])
        self.assertIsNone(old_pose['error'])
        np.testing.assert_array_equal(sim.env.command, np.zeros(3))

    def test_legacy_policy_construction_preserves_frozen_config_and_verification(self):
        policy = SimpleNamespace(predict=Mock())
        loader = SimpleNamespace(load=Mock(return_value=policy))
        checkpoint = REPO/'locomotion/runs/ppo_51200/checkpoint_51200.zip'
        for mode in ('ik', 'ppo', 'sac'):
            with self.subTest(mode=mode):
                sim, Candidate.instances = dormant(), []
                with patch.object(smooth, 'ViewerEnv', Candidate), \
                        patch.object(smooth, 'preview_config', side_effect=AssertionError('Legacy config changed')), \
                        patch.object(smooth, 'model_metadata', return_value=({'version': 1}, {})), \
                        patch.object(smooth, 'pose_snapshot', return_value={'version': 1}), \
                        patch.object(smooth, 'verify_checkpoint', return_value={'status': 'verified'}) as verify, \
                        patch.dict(sys.modules, {'stable_baselines3': SimpleNamespace(PPO=loader, SAC=loader)}):
                    sim.reset({'controller': mode, 'seed': 42, 'sensor_mode': 'mpu6050',
                               'checkpoint': str(checkpoint), 'terrain': 'flat', 'payload': .155})
                self.assertNotIn('config', Candidate.instances[-1].arguments)
                if mode == 'ik':
                    verify.assert_not_called()
                    self.assertEqual(sim.active_checkpoint, '')
                else:
                    self.assertEqual(verify.call_args.args[1], mode)
                    self.assertEqual(verify.call_args.kwargs['sensor_mode'], 'mpu6050')
                    self.assertIs(sim.policy, policy)

    def test_command_and_asset_boundaries_remain_separate_from_preview_settings(self):
        sim = dormant()
        for mode in ('fast', 'fast_plus', 'ik', 'ppo', 'sac'):
            sim.mode = mode
            sim.command({'command': [99., -99., 99.]})
            profile = smooth.PROFILES[mode][0] if mode in smooth.PROFILES else None
            linear = profile['max_translation_m_s'] if profile else .012
            yaw = profile['max_yaw_rad_s'] if profile else .06
            np.testing.assert_array_equal(sim.env.command, [linear, -linear, yaw])
            sim.command({'command': [0., 0., 0.]})
            np.testing.assert_array_equal(sim.env.command, np.zeros(3))
        for command in ([float('nan'), 0., 0.], [0., 0.], [0., 0., float('inf')]):
            with self.assertRaises(ValueError):
                sim.command({'command': command})
        sim.meshes = {}
        for path in ('/viewer/../sim_remote.py', '/viewer/%2e%2e/sim_remote.py',
                     '/viewer/mesh/not-a-mesh.stl', '/viewer/'):
            with self.assertRaises(FileNotFoundError):
                sim.asset(path)

    def test_visual_terrain_capture_preserves_frozen_random_stream_and_physics(self):
        arguments = dict(command=(0, 0, 0), terrain='rough', payload=.155, randomize=True)
        original, visual = smooth.MistEnv(**arguments), smooth.ViewerEnv(**arguments)
        try:
            old_obs, old_info = original.reset(seed=91243)
            new_obs, new_info = visual.reset(seed=91243)
            np.testing.assert_array_equal(new_obs, old_obs)
            self.assertEqual(new_info, old_info)
            self.assertEqual(visual.np_random.bit_generator.state, original.np_random.bit_generator.state)
            self.assertEqual(len(visual.viewer_heights), 4096)
            for _ in range(5):
                old = original.step(np.zeros(12))
                new = visual.step(np.zeros(12))
                np.testing.assert_array_equal(new[0], old[0])
                self.assertEqual(new[1:], old[1:])
        finally:
            original.close()
            visual.close()

    def test_higher_profile_uses_independent_1_second_controller_with_frozen_actuators(self):
        sim = dormant()
        with patch.object(smooth, 'ViewerEnv', Candidate), \
                patch.object(smooth, 'model_metadata', return_value=({'version': 1}, {})), \
                patch.object(smooth, 'pose_snapshot', return_value={'version': 1}):
            sim.reset({'controller': 'fast_plus'})
        self.assertIsInstance(sim.env.gait, smooth.SpeedCeilingCrawl)
        self.assertEqual(sim.env.gait.cycle_s, 1.)
        self.assertEqual(sim.env.gait.shift_m, .005/3.2)
        self.assertEqual(sim.env.cfg, smooth.preview_config(1.8))
        self.assertEqual(sim.policy_status, 'preview_unqualified')
        with self.assertRaisesRegex(ValueError, 'checkpoint'):
            sim.reset({'controller': 'fast_plus', 'checkpoint': 'any.zip'})


if __name__ == '__main__':
    unittest.main()
