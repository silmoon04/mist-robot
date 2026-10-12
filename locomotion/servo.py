"""Identifiable position-servo proxy; thermal/current values are estimates."""
from collections import deque
import numpy as np
try:
    from .model import load_config
except ImportError:
    from model import load_config


class ServoBank:
    def __init__(self, q, rng, randomize=True, torque_cap=None, dt=None, config=None):
        cfg = load_config() if config is None else config
        actuator, ranges = cfg['actuator'], cfg['randomization']
        dt = 1/cfg['simulation']['physics_hz'] if dt is None else dt
        self.dt = dt
        self.cap = float(actuator['torque_limit_nm'] if torque_cap is None else torque_cap)
        self.strength = rng.uniform(*ranges['torque_scale'], 12) if randomize else np.ones(12)
        self.voltage = float(rng.uniform(*ranges['voltage_v'])) if randomize else actuator['nominal_voltage_v']
        self.kp = np.tile(actuator['kp_nm_rad'], 4) * (rng.uniform(*ranges['kp_scale'], 12) if randomize else 1)
        self.kd = np.tile(actuator['kd_nm_s_rad'], 4)
        if self.kp.shape != (12,) or self.kd.shape != (12,):
            raise ValueError('actuator kp and kd require yaw, hip and knee values')
        self.deadband = np.radians(rng.uniform(*ranges['deadband_deg'], 12)) if randomize else np.full(12, actuator['position_deadband_rad'])
        self.delay_steps = int(round((rng.uniform(*ranges['motor_latency_s']) if randomize else actuator['latency_s'])/dt))
        self.speed = actuator['command_speed_rad_s']
        self.no_load_speed = actuator['no_load_speed_rad_s']
        self.stall = actuator['stall_torque_nm']
        self.friction = actuator['coulomb_friction_nm']
        self.quantization = actuator['position_quantization_rad']
        self.queue = deque([np.array(q).copy() for _ in range(self.delay_steps + 1)], maxlen=self.delay_steps + 1)
        self.target = np.array(q).copy()
        self.thermal = actuator['thermal_proxy']
        self.nominal_voltage = actuator['nominal_voltage_v']
        self.rated_torque = actuator['rated_torque_nm']
        self.temperature = np.full(12, self.thermal['ambient_c'], dtype=float)
        self.saturation = np.zeros(12, dtype=bool)
        self.torque = np.zeros(12)

    def advance(self, desired, q, qdot):
        ticks = self.quantization
        self.queue.append(np.round(np.asarray(desired)/ticks)*ticks)
        delayed = self.queue[0]
        # Loaded command slew is an estimate, below the C018 no-load speed.
        slew = self.speed*self.voltage/self.nominal_voltage * self.dt
        self.target += np.clip(delayed-self.target, -slew, slew)
        error = self.target - np.round(q/ticks)*ticks
        error = np.sign(error)*np.maximum(0., np.abs(error)-self.deadband)
        requested = self.kp*error-self.kd*qdot
        t = self.thermal
        thermal = np.clip((t['zero_torque_c']-self.temperature)/(t['zero_torque_c']-t['derate_start_c']), 0., 1.)
        envelope = self.stall*np.maximum(0., 1.-np.abs(qdot)/(self.no_load_speed*self.voltage/self.nominal_voltage))
        available = np.minimum(self.cap, envelope)*self.strength*(self.voltage/self.nominal_voltage)*thermal
        self.saturation = np.abs(requested) > available
        self.torque = np.clip(requested, -available, available) - self.friction*np.tanh(qdot/.05)
        self.temperature += self.dt*(t['heating_c_s_at_rated_torque']*(self.torque/self.rated_torque)**2-t['cooling_s_inv']*(self.temperature-t['ambient_c']))
        return self.torque

    def description(self):
        return {'torque_cap_nm': self.cap, 'motor_strength': self.strength.tolist(),
                'voltage_v': self.voltage, 'delay_s': self.delay_steps*self.dt,
                'kp': self.kp.tolist(), 'backlash_deadband_rad': self.deadband.tolist(),
                'thermal_model': 'estimated first-order proxy, not a identified winding model'}
