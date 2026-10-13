"""Pose-streamed CAD remote; browser rendering never holds the physics lock."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import sys
import time
from urllib.parse import unquote, urlsplit
import uuid
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'locomotion/scripts'))
import numpy as np
import pybullet as p
from locomotion.kinematics import inverse
from locomotion.mist_env import MistEnv
from locomotion.provenance import verify_checkpoint
from locomotion.sensor_sim import SimulatedIMU
from locomotion.sim_remote import Simulation
from locomotion.scripts.experimental_fast_crawl import preview_config
from locomotion.scripts.experimental_fast_crawl_v3 import WideRecoveryFastCrawl
from locomotion.scripts.experimental_fast_crawl_v4 import SpeedCeilingCrawl

PROFILE_PATH = Path(__file__).with_name('profiles') / 'interactive_fast_v2.json'
PROFILE_BYTES = PROFILE_PATH.read_bytes()
PROFILE = json.loads(PROFILE_BYTES)
PROFILE_SHA256 = hashlib.sha256(PROFILE_BYTES).hexdigest()
BRISK_BYTES = PROFILE_PATH.with_name('interactive_brisk.json').read_bytes()
BRISK = json.loads(BRISK_BYTES)
BRISK_SHA256 = hashlib.sha256(BRISK_BYTES).hexdigest()
PROFILES = {'fast': (PROFILE, PROFILE_SHA256), 'fast_plus': (BRISK, BRISK_SHA256)}
VIEWER_ROOT = Path(__file__).with_name('viewer').resolve()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class ViewerEnv(MistEnv):
    """Retain the frozen terrain calls; replay its random draws for visual data."""
    def _terrain(self):
        state = deepcopy(self.np_random.bit_generator.state)
        super()._terrain()
        self.viewer_heights = None
        if self.terrain == 'rough':
            generator = np.random.Generator(type(self.np_random.bit_generator)())
            generator.bit_generator.state = state
            if self.randomize:
                generator.uniform(*self.ranges['friction'])
            heights = generator.uniform(*self.ranges['roughness_height_m'], (64, 64))
            # Bullet centers the heightfield around the midpoint of its bounds.
            self.viewer_heights = (heights-(heights.min()+heights.max())/2).ravel().tolist()


def vector(element, key, default):
    return [float(v) for v in (element.get(key, default) if element is not None else default).split()]


def model_metadata(env, epoch):
    """Read CAD visual origins from the generated URDF, never inertia frames."""
    urdf = Path(env.temp.name) / 'quadruped.urdf'
    tree = ET.parse(urdf)
    meshes, links = {}, []
    permitted = {
        (REPO / 'design/main_hub_20260915/output/Main_Hub_4Leg.stl').resolve(),
        *[f.resolve() for f in (REPO / 'design/single_leg_r7_wide_joints_20260914/output/assembly_mesh').glob('*.stl')],
    }
    for link in tree.findall('link'):
        name = link.get('name')
        index = -1 if name == 'body' else env.links[name]
        visuals = []
        for visual in link.findall('visual'):
            origin, geometry = visual.find('origin'), visual.find('geometry')
            color = visual.find('material/color')
            item = {'position': vector(origin, 'xyz', '0 0 0'),
                    'quaternion': list(p.getQuaternionFromEuler(vector(origin, 'rpy', '0 0 0'))),
                    'color': vector(color, 'rgba', '.4 .6 .65 1')}
            mesh, box, sphere = geometry.find('mesh'), geometry.find('box'), geometry.find('sphere')
            if mesh is not None:
                path = (urdf.parent / mesh.get('filename')).resolve()
                if path not in permitted:
                    raise ValueError('CAD visual mesh is outside the model allowlist')
                content = path.read_bytes()
                key = hashlib.sha256(content).hexdigest()
                meshes[key] = content
                item.update(type='mesh', url=f'/viewer/mesh/{key}.stl',
                            scale=vector(mesh, 'scale', '1 1 1'))
            elif box is not None:
                item.update(type='box', size=vector(box, 'size', '1 1 1'))
            elif sphere is not None:
                item.update(type='sphere', radius=float(sphere.get('radius')))
            else:
                raise ValueError('Unsupported CAD visual primitive')
            visuals.append(item)
        links.append({'index': index, 'name': name, 'visuals': visuals})
    position, quaternion = env._call(p.getBasePositionAndOrientation, env.floor)
    terrain = {'type': env.terrain, 'position': list(position), 'quaternion': list(quaternion),
               'size': [6., 6., .02]}
    if env.viewer_heights is not None:
        terrain.update(rows=64, columns=64, spacing=.04, heights=env.viewer_heights)
    return {'version': 1, 'epoch': epoch, 'links': links, 'terrain': terrain}, meshes


def pose_snapshot(env, epoch, stopped=False, error=None):
    position, quaternion = env._call(p.getBasePositionAndOrientation, env.robot)
    position, quaternion = p.multiplyTransforms(position, quaternion, *env.inertial_to_body)
    links = [{'index': -1, 'position': list(position), 'quaternion': list(quaternion)}]
    indices = list(env.links.values())
    states = env._call(p.getLinkStates, env.robot, indices, computeForwardKinematics=True)
    links.extend({'index': index, 'position': list(state[4]), 'quaternion': list(state[5])}
                 for index, state in zip(indices, states))
    return {'version': 1, 'epoch': epoch, 'sequence': env.step_count,
            'time_s': env.step_count*env.dt*env.substeps, 'links': links,
            'stopped': stopped, 'error': error}


class SmoothSimulation(Simulation):
    def __init__(self):
        self.instance_id = uuid.uuid4().hex
        self.clock_generation = 0
        self.clock_start = time.monotonic()
        self.clock_steps = 0
        super().__init__()

    def reset(self, data):
        if not isinstance(data, dict):
            raise ValueError('request must be an object')
        mode = data.get('controller', 'fast')
        if mode not in (*PROFILES, 'ik', 'ppo', 'sac'):
            raise ValueError('unknown controller')
        with self.lock:
            seed = int(data.get('seed', 42))
            if seed < 0:
                raise ValueError('seed must be nonnegative')
            randomize = data.get('randomize', False)
            if not isinstance(randomize, bool):
                raise ValueError('randomize must be boolean')
            sensor_mode = data.get('sensor_mode', 'mpu6050')
            sensor = SimulatedIMU(sensor_mode, data.get('sensor_profile'))
            sensor_profile = sensor.profile if sensor_mode != 'none' else None
            policy, checkpoint, policy_status = None, '', 'baseline_unqualified'
            if mode in PROFILES and data.get('checkpoint'):
                raise ValueError('Faster crawl does not load checkpoints; choose PPO/SAC with its original settings or clear the path.')
            if mode in ('ppo', 'sac'):
                from stable_baselines3 import PPO, SAC
                checkpoint = str(Path(data.get('checkpoint', '')).expanduser().resolve())
                record = verify_checkpoint(Path(checkpoint), mode, sensor_mode=sensor_mode, sensor_profile=sensor_profile)
                policy_status = record['status']
                if not Path(checkpoint).exists():
                    raise ValueError('development checkpoint has not been produced')
                policy = (PPO if mode == 'ppo' else SAC).load(checkpoint, device='cpu')
            arguments = dict(command=(0, 0, 0), terrain=data.get('terrain', 'flat'),
                             payload=float(data.get('payload', .155)), randomize=randomize,
                             max_steps=100000, sensor_mode=sensor_mode, sensor_profile=sensor_profile)
            if mode in PROFILES:
                profile = PROFILES[mode][0]
                arguments['config'] = preview_config(profile['command_speed_rad_s'])
            candidate = ViewerEnv(**arguments)
            try:
                if mode in PROFILES:
                    controller = SpeedCeilingCrawl if mode == 'fast_plus' else WideRecoveryFastCrawl
                    candidate.gait = controller(config=candidate.cfg, cycle_s=profile['cycle_s'],
                                                shift_m=profile['shift_m'], recovery_start=profile['recovery_start'],
                                                translational_stride_gain=profile['translational_stride_gain'])
                    policy_status = 'preview_unqualified'
                obs, info = candidate.reset(seed=seed)
                generation = self.clock_generation+1
                epoch = f'{self.instance_id}:{generation}'
                model, meshes = model_metadata(candidate, epoch)
                pose = pose_snapshot(candidate, epoch)
            except Exception:
                candidate.close()
                raise
            previous = getattr(self, 'env', None)
            self.env, self.obs, self.info = candidate, obs, info
            self.model, self.meshes, self.latest_pose, self.epoch = model, meshes, pose, epoch
            self.stopped, self.last_command, self.policy, self.error = False, 0., policy, None
            self.mode, self.seed, self.policy_status = mode, seed, policy_status
            self.active_checkpoint = checkpoint
            self.effective_cfg = deepcopy(candidate.cfg)
            self.clock_generation = generation
            self.clock_start, self.clock_steps = time.monotonic(), 0
            if previous is not None:
                previous.close()

    def worker(self):
        deadline, generation = time.monotonic(), self.clock_generation
        while self.running:
            with self.lock:
                started = time.monotonic()
                if generation != self.clock_generation:
                    generation, deadline = self.clock_generation, started
                period = self.env.dt*self.env.substeps
                try:
                    if started-self.last_command > .35:
                        self.env.command = np.zeros(3)
                    if not self.stopped:
                        action = np.zeros(12) if self.policy is None else self.policy.predict(self.obs, deterministic=True)[0]
                        self.obs, _, fell, _, self.info = self.env.step(action)
                        self.stopped = fell
                        self.clock_steps += 1
                        self.latest_pose = pose_snapshot(self.env, self.epoch, self.stopped)
                except Exception as exc:
                    self.stopped, self.error = True, str(exc)
                    self.env.command = np.zeros(3)
                    self.latest_pose = dict(self.latest_pose, stopped=True, error=self.error)
            deadline += period
            now = time.monotonic()
            if now-deadline > .5:
                deadline = now
            time.sleep(max(.001, deadline-now))

    def command(self, data):
        cmd = np.asarray(data.get('command'), dtype=float)
        if cmd.shape != (3,) or not np.all(np.isfinite(cmd)):
            raise ValueError('three finite command values required')
        with self.lock:
            profile = PROFILES[self.mode][0] if self.mode in PROFILES else None
            linear = profile['max_translation_m_s'] if profile else .012
            yaw = profile['max_yaw_rad_s'] if profile else .06
            self.env.command = np.clip(cmd, [-linear, -linear, -yaw], [linear, linear, yaw])
            self.last_command = time.monotonic()

    def pose(self):
        with self.lock:
            return self.latest_pose

    def state(self):
        with self.lock:
            fast = self.mode in PROFILES
            profile, profile_hash = PROFILES[self.mode] if fast else (None, None)
            elapsed = max(time.monotonic()-self.clock_start, 1e-6)
            return {'info': self.info, 'fell': self.stopped, 'controller': self.mode, 'error': self.error,
                    'seed': self.seed, 'policy_status': self.policy_status, 'sensor': self.env.sensor.status(),
                    'status': 'simulation only; walking and real transfer are unqualified',
                    'pose': self.latest_pose,
                    'interactive': {'version': 2, 'profile': profile['name'] if fast else 'Original frozen settings',
                                    'max_translation_m_s': profile['max_translation_m_s'] if fast else .012,
                                    'default_translation_m_s': profile['default_translation_m_s'] if fast else .01,
                                    'motor_target_rate_rad_s': self.effective_cfg['actuator']['command_speed_rad_s'],
                                    'cycle_s': self.env.gait.cycle_s,
                                    'real_time_factor': self.clock_steps*self.env.dt*self.env.substeps/elapsed,
                                    'effective_config_sha256': digest(self.effective_cfg),
                                    'profile_sha256': profile_hash,
                                    'status': profile['status'] if fast else 'Original checkpoint-compatible configuration; walking unqualified'},
                    'setup': {'terrain': self.env.terrain_spec, 'payload': self.env.payload,
                              'sensor_mode': self.env.sensor.mode, 'seed': self.seed,
                              'randomize': self.env.randomize, 'sensor_profile': self.env.sensor.profile,
                              'checkpoint': self.active_checkpoint}}

    def asset(self, path):
        """Serve only immutable CAD mesh bytes or files inside the viewer directory."""
        if path.startswith('/viewer/mesh/'):
            key = path.removeprefix('/viewer/mesh/').removesuffix('.stl')
            with self.lock:
                content = self.meshes.get(key)
            if content is None:
                raise FileNotFoundError(path)
            return content, 'application/octet-stream'
        relative = unquote(path.removeprefix('/viewer/'))
        target = (VIEWER_ROOT / relative).resolve()
        if not relative or not target.is_relative_to(VIEWER_ROOT) or not target.is_file():
            raise FileNotFoundError(path)
        mime = 'text/javascript; charset=utf-8' if target.suffix in ('.js', '.mjs') else mimetypes.guess_type(target)[0] or 'application/octet-stream'
        return target.read_bytes(), mime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8131)
    args = parser.parse_args()
    sim = SmoothSimulation()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def send(self, value, mime='application/json', status=200):
            body = value if isinstance(value, bytes) else json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/':
                self.send(Path(__file__).with_name('sim_remote.html').read_bytes(), 'text/html; charset=utf-8')
            elif path == '/api/state':
                self.send(sim.state())
            elif path == '/api/pose':
                self.send(sim.pose())
            elif path == '/api/model':
                with sim.lock:
                    model = sim.model
                self.send(model)
            elif path.startswith('/viewer/'):
                try:
                    content, mime = sim.asset(path)
                    self.send(content, mime)
                except (OSError, ValueError):
                    self.send({'error': 'not found'}, status=404)
            else:
                self.send({'error': 'not found'}, status=404)
        def do_POST(self):
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 1 <= size <= 8192:
                    raise ValueError('request length must be between 1 and 8192 bytes')
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('request must be an object')
                if self.path == '/api/reset': sim.reset(data)
                elif self.path == '/api/command': sim.command(data)
                elif self.path == '/api/ik':
                    q = inverse(np.asarray(data['foot_mm'], float)/1000)
                    self.send({'q_rad': q.tolist(), 'q_deg': np.degrees(q).tolist()})
                    return
                else: raise ValueError('unknown operation')
                self.send({'ok': True})
            except (ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
                self.send({'error': str(exc)}, status=400)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Smooth simulation remote: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        sim.close()


if __name__ == '__main__':
    main()
