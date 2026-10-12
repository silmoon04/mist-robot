"""Interactive simulator with a separate faster crawl and unchanged legacy modes."""
from __future__ import annotations
import argparse
import base64
from copy import deepcopy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'locomotion/scripts'))
import numpy as np
import pybullet as p
from PIL import Image
from locomotion.model import load_config
from locomotion.mist_env import MistEnv
from locomotion.kinematics import inverse
from locomotion.sensor_sim import SimulatedIMU
from locomotion.sim_remote import Simulation
from locomotion.scripts.experimental_fast_crawl import preview_config
from locomotion.scripts.experimental_fast_crawl_v3 import WideRecoveryFastCrawl

PROFILE_PATH = Path(__file__).with_name('profiles') / 'interactive_fast.json'
PROFILE_BYTES = PROFILE_PATH.read_bytes()
PROFILE = json.loads(PROFILE_BYTES)
PROFILE_SHA256 = hashlib.sha256(PROFILE_BYTES).hexdigest()
if PROFILE['shift_m'] != .005 * PROFILE['cycle_s'] / 3.2:
    raise ValueError('This preview requires a body shift scaled with its cycle')

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def fast_config():
    return preview_config(PROFILE['command_speed_rad_s'])

def add_floor_grid(env):
    """Draw 10 cm world landmarks without adding collision geometry."""
    if env.terrain != 'flat':
        return []
    vertices, indices = [], []
    for axis in (0, 1):
        half_x, half_y = (1., .0005) if axis == 0 else (.0005, 1.)
        for tick in range(-10, 11):
            x, y = (0., tick*.1) if axis == 0 else (tick*.1, 0.)
            start = len(vertices)
            vertices.extend([[x-half_x, y-half_y, .00045], [x+half_x, y-half_y, .00045],
                             [x+half_x, y+half_y, .00045], [x-half_x, y+half_y, .00045]])
            indices.extend([start, start+1, start+2, start, start+2, start+3])
    # One visual mesh avoids per-body shadow work in the software renderer.
    shape = env._call(p.createVisualShape, p.GEOM_MESH, vertices=vertices, indices=indices,
                      rgbaColor=[.56, .66, .68, 1.])
    return [env._call(p.createMultiBody, baseMass=0, baseCollisionShapeIndex=-1,
                     baseVisualShapeIndex=shape)]

class InteractiveSimulation(Simulation):
    def __init__(self):
        self.clock_generation = 0
        self.clock_start = time.monotonic()
        self.clock_steps = 0
        super().__init__()

    def reset(self, data):
        if not isinstance(data, dict):
            raise ValueError('request must be an object')
        mode = data.get('controller', 'fast')
        with self.lock:
            if mode != 'fast':
                super().reset(data)
                self.effective_cfg = deepcopy(self.env.cfg)
            else:
                if data.get('checkpoint'):
                    raise ValueError('Faster crawl does not load checkpoints; choose PPO/SAC with its original settings or clear the path.')
                seed = int(data.get('seed', 42))
                if seed < 0:
                    raise ValueError('seed must be nonnegative')
                randomize = data.get('randomize', False)
                if not isinstance(randomize, bool):
                    raise ValueError('randomize must be boolean')
                sensor_mode = data.get('sensor_mode', 'mpu6050')
                sensor = SimulatedIMU(sensor_mode, data.get('sensor_profile'))
                sensor_profile = sensor.profile if sensor_mode != 'none' else None
                cfg = fast_config()
                candidate = MistEnv(command=(0, 0, 0), terrain=data.get('terrain', 'flat'),
                                    payload=float(data.get('payload', .155)), randomize=randomize,
                                    max_steps=100000, sensor_mode=sensor_mode, sensor_profile=sensor_profile, config=cfg)
                try:
                    candidate.gait = WideRecoveryFastCrawl(config=cfg, cycle_s=PROFILE['cycle_s'],
                                                          shift_m=PROFILE['shift_m'],
                                                          recovery_start=PROFILE['recovery_start'],
                                                          translational_stride_gain=PROFILE['translational_stride_gain'])
                    obs, info = candidate.reset(seed=seed)
                    add_floor_grid(candidate)
                    stream = io.BytesIO()
                    Image.fromarray(candidate.render()).save(stream, format='JPEG', quality=80)
                    preview = base64.b64encode(stream.getvalue()).decode()
                except Exception:
                    candidate.close()
                    raise
                previous = getattr(self, 'env', None)
                self.env, self.obs, self.info, self.image = candidate, obs, info, preview
                self.stopped, self.last_command, self.policy, self.error = False, 0., None, None
                self.mode, self.seed, self.policy_status = mode, seed, 'preview_unqualified'
                self.effective_cfg = cfg
                if previous is not None:
                    previous.close()
            self.clock_generation += 1
            self.clock_start, self.clock_steps = time.monotonic(), 0
            self.active_checkpoint = str(Path(data['checkpoint']).expanduser().resolve()) if mode in ('ppo', 'sac') else ''

    def worker(self):
        deadline = time.monotonic()
        next_frame = deadline
        generation = self.clock_generation
        while self.running:
            started = time.monotonic()
            with self.lock:
                if generation != self.clock_generation:
                    generation = self.clock_generation
                    deadline, next_frame = started, started
                period = self.env.dt * self.env.substeps
                try:
                    if started-self.last_command > .35:
                        self.env.command = np.zeros(3)
                    if not self.stopped:
                        action = np.zeros(12) if self.policy is None else self.policy.predict(self.obs, deterministic=True)[0]
                        self.obs, _, fell, _, self.info = self.env.step(action)
                        self.stopped = fell
                        self.clock_steps += 1
                    # The viewer polls at 5 Hz. Render against wall deadlines rather than every five physics steps.
                    if started >= next_frame and not self.stopped:
                        self._render()
                        next_frame = time.monotonic()+.2
                except Exception as exc:
                    self.stopped, self.error = True, str(exc)
            deadline += period
            now = time.monotonic()
            if now-deadline > .5:
                deadline = now  # Bound catch-up after a stall; do not change the physics timestep.
            time.sleep(max(.001, deadline-now))

    def command(self, data):
        cmd = np.asarray(data.get('command'), dtype=float)
        if cmd.shape != (3,) or not np.all(np.isfinite(cmd)):
            raise ValueError('three finite command values required')
        with self.lock:
            linear = PROFILE['max_translation_m_s'] if self.mode == 'fast' else .012
            yaw = PROFILE['max_yaw_rad_s'] if self.mode == 'fast' else .06
            self.env.command = np.clip(cmd, [-linear, -linear, -yaw], [linear, linear, yaw])
            self.last_command = time.monotonic()

    def state(self):
        with self.lock:
            result = super().state()
            fast = self.mode == 'fast'
            elapsed = max(time.monotonic()-self.clock_start, 1e-6)
            result['interactive'] = {
                'version': 1, 'profile': PROFILE['name'] if fast else 'Original frozen settings',
                'max_translation_m_s': PROFILE['max_translation_m_s'] if fast else .012,
                'default_translation_m_s': PROFILE['default_translation_m_s'] if fast else .01,
                'motor_target_rate_rad_s': self.effective_cfg['actuator']['command_speed_rad_s'],
                'cycle_s': self.env.gait.cycle_s,
                'real_time_factor': self.clock_steps*self.env.dt*self.env.substeps/elapsed,
                'effective_config_sha256': digest(self.effective_cfg),
                'profile_sha256': PROFILE_SHA256 if fast else None,
                'status': PROFILE['status'] if fast else 'Original checkpoint-compatible configuration; walking unqualified'
            }
            result['setup'] = {'terrain': self.env.terrain_spec, 'payload': self.env.payload,
                               'sensor_mode': self.env.sensor.mode, 'seed': self.seed,
                               'randomize': self.env.randomize, 'sensor_profile': self.env.sensor.profile,
                               'checkpoint': self.active_checkpoint}
            return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8131)
    args = parser.parse_args()
    sim = InteractiveSimulation()
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
            if self.path == '/':
                self.send(Path(__file__).with_name('sim_remote.html').read_bytes(), 'text/html; charset=utf-8')
            elif self.path == '/api/state':
                self.send(sim.state())
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
                if self.path == '/api/reset':
                    sim.reset(data)
                elif self.path == '/api/command':
                    sim.command(data)
                elif self.path == '/api/ik':
                    q = inverse(np.asarray(data['foot_mm'], float)/1000)
                    self.send({'q_rad': q.tolist(), 'q_deg': np.degrees(q).tolist()})
                    return
                else:
                    raise ValueError('unknown operation')
                self.send({'ok': True})
            except (ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
                self.send({'error': str(exc)}, status=400)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Interactive simulation remote: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        sim.close()

if __name__ == '__main__':
    main()
