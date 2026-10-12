"""Slow, command-conditioned crawl for the R7 yaw/pitch mechanism."""
from __future__ import annotations
import math
import json
import xml.etree.ElementTree as ET
import numpy as np
try:
    from .model import LEGS, MOUNTS, NEUTRAL, REPO, load_config
    from .kinematics import forward, inverse, jacobian, LIMITS
except ImportError:
    from model import LEGS, MOUNTS, NEUTRAL, REPO, load_config
    from kinematics import forward, inverse, jacobian, LIMITS


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.]])


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1., 0], [-s, 0, c]])


class CrawlController:
    def __init__(self, cycle_s=3.2, lift_m=.012, shift_m=.020, config=None):
        self.cycle_s, self.lift_m, self.shift_m = cycle_s, lift_m, shift_m
        self.nominal = {leg: np.asarray(MOUNTS[leg]['xyz']) +
                        rz(MOUNTS[leg]['yaw']) @ forward(NEUTRAL) for leg in LEGS}
        # Each leg swings alone; diagonal ordering spreads the body shifts.
        self.offset = dict(zip(('FL', 'RR', 'FR', 'RL'), (0., .25, .50, .75)))
        self._load_position_model(config)

    def _load_position_model(self, config=None):
        cfg = load_config() if config is None else config
        source = ET.parse(REPO / cfg['sources']['leg_urdf']).getroot()
        manifest = json.loads((REPO / cfg['sources']['leg_manifest']).read_text())
        self.model_masses, self.model_com = {}, {}
        for name in ('coxa', 'femur', 'tibia'):
            inertial = source.find(f"link[@name='{name}']/inertial")
            self.model_masses[name] = float(inertial.find('mass').get('value'))
            self.model_com[name] = np.fromstring(inertial.find('origin').get('xyz'), sep=' ')
        source_leg_mass = sum(float(link.find('inertial/mass').get('value')) for link in source.findall('link'))
        fixture_mass = next(part['solid_mass_kg'] for part in manifest['parts'] if part['name'] == 'bench_mounting_plate')
        body_keys = ('hub_solid_pla', 'battery', 'electronics_harness', 'phone_mount', 'phone_pan_servo', 'phone_pan_horn')
        body_mass = sum(cfg['body'][name + '_mass_kg'] for name in body_keys)
        self.model_mass_without_phone = body_mass + 4 * (source_leg_mass - fixture_mass)
        self.position_kp = np.asarray(cfg['actuator']['kp_nm_rad'], dtype=float)
        if self.position_kp.shape != (3,) or np.any(self.position_kp <= 0):
            raise ValueError('position feedforward needs positive yaw, hip and knee gains')
        self.last_position_bias = np.zeros(12)

    def support_weights(self, time_s, command):
        """Scheduled support only; these weights are not measured contacts."""
        command = np.asarray(command, dtype=float)
        if command.shape != (3,) or not np.isfinite(command).all():
            raise ValueError('command must contain finite vx, vy, yaw_rate')
        if np.max(np.abs(command)) < 1e-8:
            return np.ones(4)
        weights = []
        for leg in LEGS:
            phase = (time_s / self.cycle_s - self.offset[leg]) % 1.
            if phase < .76:
                weight = 1.
            elif phase < .82:
                weight = 1. - (phase - .76) / .06
            elif phase < .97:
                weight = 0.
            else:
                weight = (phase - .97) / .03
            weights.append(weight)
        return np.asarray(weights)

    def estimate_support_forces(self, time_s, command, q=None, phone_mass_kg=.155):
        """Estimate vertical support loads from planned feet and nominal mass.

        The moment balance assumes the horizontal centre of mass is centred.
        Mass offsets, terrain contact and dynamic loads remain model errors.
        """
        if not np.isfinite(phone_mass_kg) or phone_mass_kg < 0:
            raise ValueError('phone mass must be finite and nonnegative')
        q = self.targets(time_s, command) if q is None else np.asarray(q, dtype=float)
        if q.shape not in ((12,), (4, 3)) or not np.isfinite(q).all():
            raise ValueError('support model requires twelve finite angles')
        q = q.reshape(4, 3)
        points = np.asarray([np.asarray(MOUNTS[leg]['xyz']) + rz(MOUNTS[leg]['yaw']) @ forward(angles)
                             for leg, angles in zip(LEGS, q)])
        matrix = np.vstack([np.ones(4), points[:, 0], points[:, 1]])
        weights = np.diag(self.support_weights(time_s, command))
        total_force = (self.model_mass_without_phone + phone_mass_kg) * 9.81
        forces = weights @ matrix.T @ np.linalg.solve(matrix @ weights @ matrix.T, [total_force, 0., 0.])
        # Ground cannot pull a foot down. Project negative estimates to zero
        # and conserve total weight; this loses moment balance if the planned
        # centre lies outside the support polygon.
        forces = np.maximum(0., forces)
        if forces.sum() <= 0:
            raise ValueError('planned support cannot carry the nominal mass')
        return forces * (total_force / forces.sum())

    def _gravity_torque(self, angles):
        yaw, hip_angle, knee_angle = angles
        yaw_rotation, hip_rotation = rz(yaw), ry(hip_angle)
        hip = yaw_rotation @ [.082, 0., 0.]
        knee = hip + yaw_rotation @ hip_rotation @ [.09, 0., 0.]
        com = {
            'coxa': yaw_rotation @ self.model_com['coxa'],
            'femur': hip + yaw_rotation @ hip_rotation @ self.model_com['femur'],
            'tibia': knee + yaw_rotation @ ry(hip_angle + knee_angle) @ self.model_com['tibia'],
        }
        gravity = {name: np.array([0., 0., -mass * 9.81]) for name, mass in self.model_masses.items()}
        pitch_axis = yaw_rotation @ [0., 1., 0.]
        yaw_torque = sum(np.cross(com[name], gravity[name])[2] for name in self.model_masses)
        hip_torque = sum(np.cross(com[name] - hip, gravity[name]) @ pitch_axis for name in ('femur', 'tibia'))
        knee_torque = np.cross(com['tibia'] - knee, gravity['tibia']) @ pitch_axis
        return np.array([yaw_torque, hip_torque, knee_torque])

    def position_targets(self, time_s, command, attitude=None, phone_mass_kg=.155):
        """Add bounded model support/gravity bias for finite-gain servos.

        This adds estimated static torque divided by nominal position gain.
        It uses the source masses, commanded gait phase and known phone mass.
        It does not read simulator contacts, velocity, or randomized motors.
        These gains and static load estimates still need bench identification.
        """
        geometric = self.targets(time_s, command, attitude).reshape(4, 3)
        forces = self.estimate_support_forces(time_s, command, geometric, phone_mass_kg)
        biased = []
        for angles, force in zip(geometric, forces):
            torque = -jacobian(angles).T @ np.array([0., 0., force]) - self._gravity_torque(angles)
            bias = np.clip(torque / self.position_kp, -.12, .12)
            biased.append(np.clip(angles + bias, LIMITS[:, 0], LIMITS[:, 1]))
        result = np.asarray(biased)
        self.last_position_bias = (result - geometric).ravel()
        return result.ravel()

    def targets(self, time_s, command, attitude=None):
        cmd = np.asarray(command, dtype=float)
        if cmd.shape != (3,) or not np.all(np.isfinite(cmd)):
            raise ValueError('command must contain finite vx, vy, yaw_rate')
        if np.max(np.abs(cmd)) < 1e-8:
            return np.tile(NEUTRAL, 4)
        ramp = min(1., max(0., time_s / 1.5))
        body_shift = np.zeros(3)
        points = {}
        for leg in LEGS:
            phase = (time_s / self.cycle_s - self.offset[leg]) % 1.
            velocity = np.r_[cmd[:2], 0.] + cmd[2] * np.cross([0., 0., 1.], self.nominal[leg])
            stride = velocity * self.cycle_s * .8
            length = np.linalg.norm(stride[:2])
            if length > .035:
                stride *= .035 / length
            if phase < .8:
                along, lift = .5 - phase / .8, 0.
            else:
                u = (phase - .8) / .2
                along, lift = -.5 + u*u*(3.-2.*u), self.lift_m * math.sin(math.pi*u)**2
            points[leg] = self.nominal[leg] + ramp * (stride * along + [0., 0., lift])
            # Shift away before lifting, then return while all feet have contact.
            if phase > .73:
                u = (phase - .73) / .27
                envelope = math.sin(math.pi*u)**2
                direction = self.nominal[leg][:2] / np.linalg.norm(self.nominal[leg][:2])
                body_shift[:2] -= ramp * self.shift_m * envelope * direction
        correction = np.eye(3)
        if attitude is not None:
            roll, pitch = np.clip(np.asarray(attitude)[:2], -.25, .25)
            # Small measured-attitude compensation, with no world-position input.
            cr, sr, cp, sp = math.cos(.5*roll), math.sin(.5*roll), math.cos(.5*pitch), math.sin(.5*pitch)
            correction = np.array([[cp, sp*sr, sp*cr], [0, cr, -sr], [-sp, cp*sr, cp*cr]]).T
        result = []
        for leg in LEGS:
            point = correction @ (points[leg] - body_shift) - MOUNTS[leg]['xyz']
            result.extend(inverse(rz(-MOUNTS[leg]['yaw']) @ point))
        return np.asarray(result)
