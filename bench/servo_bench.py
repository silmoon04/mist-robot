# Bench console for Feetech STS/SCS serial-bus servos (ST-3215-C018).
# Talks the half-duplex bus over the FE-URT-2 (CH343) and serves a browser UI
# with live telemetry charts and register control.
#   python bench/servo_bench.py                 (then open http://localhost:8124/)
#   PORT=9000 python bench/servo_bench.py
#
# Safety notes baked in:
#   - goal-position writes are clamped to 0..4095 and refused unless the servo
#     reports a 9-12.6 V rail (USB 5 V only powers the logic stage)
#   - EEPROM writes (ID, baud) are gated behind an explicit unlock/relock
#   - /api/estop torques off every known ID
import http.server
import json
import math
import os
import secrets
import threading
import time
from collections import deque

import serial
import serial.tools.list_ports

try:
    from .leg_calibration import (
        CalibrationStore,
        ROLE_NAMES,
        calibration_ready,
        geometry_from_config,
    )
    from .leg_kinematics import (
        degrees,
        fk_tip_mm,
        ik_tip_mm,
        joints_from_servo_angles,
        radians_from_tick,
        servo_angles_from_joints,
        tick_target,
    )
except ImportError:  # Direct execution with ``python bench/servo_bench.py``.
    from leg_calibration import (
        CalibrationStore,
        ROLE_NAMES,
        calibration_ready,
        geometry_from_config,
    )
    from leg_kinematics import (
        degrees,
        fk_tip_mm,
        ik_tip_mm,
        joints_from_servo_angles,
        radians_from_tick,
        servo_angles_from_joints,
        tick_target,
    )

PORT = int(os.environ.get('PORT', 8124))
HERE = os.path.dirname(os.path.abspath(__file__))

# --- protocol ---------------------------------------------------------------
# STS/SMS control table. 16-bit values are little-endian on this family.
REG = {
    'id':            (5,  1),
    'baud':          (6,  1),
    'min_angle':     (9,  2),
    'max_angle':     (11, 2),
    'max_temp':      (13, 1),
    'max_volt':      (14, 1),
    'min_volt':      (15, 1),
    'max_torque':    (16, 2),
    'mode':          (33, 1),
    'torque_enable': (40, 1),
    'acceleration':  (41, 1),
    'goal_position': (42, 2),
    'goal_time':     (44, 2),
    'goal_speed':    (46, 2),
    'torque_limit':  (48, 2),
    'lock':          (55, 1),
    'position':      (56, 2),
    'speed':         (58, 2),
    'load':          (60, 2),
    'voltage':       (62, 1),
    'temperature':   (63, 1),
    'moving':        (66, 1),
    'current':       (69, 2),
}

PING, READ, WRITE, SYNC_WRITE = 0x01, 0x02, 0x03, 0x83
POS_MIN, POS_MAX = 0, 4095
RAIL_MIN, RAIL_MAX = 9.0, 12.6
MOTION_HZ = 30
MOTION_DEFAULT_SPEED_PERCENT = 70
MOTION_MAX_STEP_TICKS = 44
MOTION_SPEED = 730
MOTION_ACCELERATION = 15
MOTION_TORQUE_LIMIT = 300
MOTION_MAX_CURRENT_MA = 800
MOTION_MAX_TEMP_C = 50
MOTION_DEADMAN_SECONDS = 0.75
MOTION_MAX_ARM_SECONDS = 60.0


def motion_profile(speed_percent):
    percent = max(10, min(100, int(speed_percent)))
    max_step = round(8 + (60 - 8) * percent / 100)
    speed = round(100 + (1000 - 100) * percent / 100)
    acceleration = round(2 + (20 - 2) * percent / 100)
    return {
        'speed_percent': percent,
        'max_step_ticks': max_step,
        'speed': speed,
        'acceleration': acceleration,
        'estimated_deg_s': max_step * MOTION_HZ * 360.0 / 4096.0,
    }
CALIBRATION_PATH = os.path.join(HERE, 'leg_calibration.json')
CALIBRATION = CalibrationStore(CALIBRATION_PATH)


def checksum(body):
    return (~sum(body)) & 0xFF


class Bus:
    """Half-duplex Feetech bus. One lock serialises every transaction."""

    def __init__(self):
        self.ser = None
        self.lock = threading.RLock()
        self.port_name = None
        self.baud = None
        self.errors = 0
        self.txns = 0

    def open(self, port_name, baud=1000000):
        with self.lock:
            self.close()
            # 30 ms, not 15: the CH343's USB latency timer is ~16 ms, so a reply
            # split across two USB transfers needs longer than one tick to arrive
            # in full. Below ~20 ms the tail is cut off and every read fails.
            self.ser = serial.Serial(port_name, baud, timeout=0.03, write_timeout=0.2)
            self.port_name, self.baud = port_name, baud
            self.errors = self.txns = 0

    def close(self):
        with self.lock:
            if self.ser:
                try:
                    self.ser.close()
                except Exception:
                    pass
            self.ser = None
            self.port_name = self.baud = None

    @property
    def is_open(self):
        return self.ser is not None and self.ser.is_open

    def _txn(self, sid, inst, params=(), expect=0, quiet=False, retries=3):
        """Retry once before reporting a failure - a single dropped frame on a
        contended bus is normal and should not surface as an error."""
        for attempt in range(retries + 1):
            r = self._txn_once(sid, inst, params, expect,
                               quiet=quiet or attempt < retries)
            if r is not None:
                return r
        return None

    def _txn_once(self, sid, inst, params=(), expect=0, quiet=False):
        """Send one packet, return the reply's parameter bytes (or None).

        quiet=True suppresses error counting - used by ping during a scan, where
        silence from an unused ID is the expected answer, not a bus fault.
        """
        if not self.is_open:
            return None
        body = [sid, len(params) + 2, inst, *params]
        pkt = bytes([0xFF, 0xFF, *body, checksum(body)])
        with self.lock:
            self.txns += 1
            try:
                # Drain leftovers by reading them, NOT with reset_input_buffer():
                # on the CH343 that flush lands asynchronously and clips the first
                # bytes of the reply, producing headerless frames ~60% of the time.
                if self.ser.in_waiting:
                    self.ser.read(self.ser.in_waiting)
                self.ser.write(pkt)
                # Blocking read - it returns the moment the byte count is met.
                # Do NOT poll in_waiting with short sleeps here: Windows' sleep
                # granularity is ~15 ms and it drags the poll loop to ~2 Hz.
                buf = self.ser.read(6 + expect)
                frame = self._parse(buf, sid, expect)
                if frame is None and self.ser.in_waiting:
                    buf += self.ser.read(self.ser.in_waiting)
                    frame = self._parse(buf, sid, expect)
                if frame is not None:
                    return frame
            except Exception:
                if not quiet:
                    self.errors += 1
                return None
        if not quiet:
            self.errors += 1
        return None

    @staticmethod
    def _parse(buf, sid, expect):
        """Find FF FF <sid> <len> <err> <params...> <chk> in buf, checksum-verified."""
        for i in range(len(buf) - 3):
            if buf[i] != 0xFF or buf[i + 1] != 0xFF or buf[i + 2] != sid:
                continue
            length = buf[i + 3]
            end = i + 4 + length          # header(4) + err + params + chk
            if end > len(buf):
                return None               # frame still arriving - wait for more
            frame = buf[i + 2:end - 1]
            if checksum(frame) != buf[end - 1]:
                continue
            data = buf[i + 5:end - 1]
            if len(data) == expect:
                return data
        return None

    def ping(self, sid):
        # One retry, not three: during a scan most IDs are silent by design, and
        # 21 addresses x 4 attempts x 50 ms would make a scan take ~4 seconds.
        return self._txn(sid, PING, (), 0, quiet=True, retries=1) is not None

    def read(self, sid, addr, size):
        d = self._txn(sid, READ, (addr, size), size)
        if d is None:
            return None
        return d[0] if size == 1 else int.from_bytes(d[:2], 'little')

    def read_block(self, sid, addr, size):
        return self._txn(sid, READ, (addr, size), size)

    def write(self, sid, addr, value, size=1):
        if size == 1:
            params = (addr, value & 0xFF)
        else:
            params = (addr, value & 0xFF, (value >> 8) & 0xFF)
        return self._txn(sid, WRITE, params, 0) is not None

    @staticmethod
    def sync_write_packet(addr, rows):
        """Build the official Feetech SyncWrite 0x83 broadcast packet."""
        items = [(int(sid), bytes(data)) for sid, data in rows]
        if not items:
            raise ValueError('sync write needs at least one servo')
        data_len = len(items[0][1])
        if not 1 <= data_len <= 32:
            raise ValueError('invalid sync-write data length')
        params = [int(addr) & 0xFF, data_len]
        seen = set()
        for sid, data in items:
            if not 0 <= sid <= 253 or sid in seen:
                raise ValueError('sync-write IDs must be unique and in 0..253')
            if len(data) != data_len:
                raise ValueError('every sync-write row must have the same length')
            seen.add(sid)
            params.extend([sid, *data])
        body = [0xFE, len(params) + 2, SYNC_WRITE, *params]
        return bytes([0xFF, 0xFF, *body, checksum(body)])

    def sync_write(self, addr, rows):
        if not self.is_open:
            return False
        packet = self.sync_write_packet(addr, rows)
        with self.lock:
            self.txns += 1
            try:
                if self.ser.in_waiting:
                    self.ser.read(self.ser.in_waiting)
                self.ser.write(packet)
                self.ser.flush()
                return True
            except Exception:
                self.errors += 1
                return False


BUS = Bus()

# --- telemetry --------------------------------------------------------------
HISTORY = 1500          # ~75 s at 20 Hz
POLL_HZ = 20


class Telemetry:
    def __init__(self):
        self.ids = []
        self.hist = {}
        self.latest = {}
        self.lock = threading.Lock()
        self.running = True
        self.seq = 0
        threading.Thread(target=self._loop, daemon=True).start()

    def track(self, ids):
        with self.lock:
            self.ids = list(ids)
            for i in ids:
                self.hist.setdefault(i, deque(maxlen=HISTORY))

    def _sample(self, sid):
        blk = BUS.read_block(sid, 56, 15)
        if not blk or len(blk) < 15:
            return None
        u16 = lambda o: int.from_bytes(blk[o:o + 2], 'little')
        # Speed and load are sign-magnitude, not two's complement, and they use
        # different sign bits: speed bit 15, load bit 10.
        raw_speed, raw_load = u16(2), u16(4)
        return {
            'position': u16(0),
            'speed': (raw_speed & 0x7FFF) * (-1 if raw_speed & 0x8000 else 1),
            'load': (raw_load & 0x3FF) * (-1 if raw_load & 0x400 else 1),
            'voltage': round(blk[6] * 0.1, 1),
            'temperature': blk[7],
            'moving': blk[10],
            'current_ma': round(u16(13) * 6.5),
        }

    def _loop(self):
        period = 1.0 / POLL_HZ
        while self.running:
            t0 = time.monotonic()
            if BUS.is_open:
                with self.lock:
                    ids = list(self.ids)
                for sid in ids:
                    s = self._sample(sid)
                    if s:
                        s['t'] = time.time()
                        with self.lock:
                            self.seq += 1
                            s['seq'] = self.seq
                            self.hist[sid].append(s)
                            self.latest[sid] = s
            time.sleep(max(0.0, period - (time.monotonic() - t0)))

    def since(self, seq):
        with self.lock:
            out = {}
            for sid, dq in self.hist.items():
                rows = [s for s in dq if s['seq'] > seq]
                if rows:
                    out[str(sid)] = rows
            return out, self.seq, dict((str(k), v) for k, v in self.latest.items())


TEL = Telemetry()


def rail_ok(sid):
    """True if this servo reports a motor-capable rail."""
    s = TEL.latest.get(sid)
    v = s['voltage'] if s else BUS.read(sid, *REG['voltage'])
    if v is None:
        return False, None
    v = v if isinstance(v, float) else v * 0.1
    return (RAIL_MIN <= v <= RAIL_MAX), v


# --- three-servo test-leg calibration --------------------------------------
def leg_config_payload():
    config = CALIBRATION.load()
    return {
        'config': config,
        'ready': calibration_ready(config),
        'path': CALIBRATION_PATH,
    }


def servo_snapshot(sid):
    """Read a compact snapshot directly from one servo without moving it."""
    if not BUS.ping(sid):
        return {'present': False, 'id': sid}
    voltage_raw = BUS.read(sid, *REG['voltage'])
    current_raw = BUS.read(sid, *REG['current'])
    snapshot = {
        'present': True,
        'id': sid,
        'torque_enabled': BUS.read(sid, *REG['torque_enable']),
        'position': BUS.read(sid, *REG['position']),
        'voltage': round(voltage_raw * 0.1, 1) if voltage_raw is not None else None,
        'temperature': BUS.read(sid, *REG['temperature']),
        'current_ma': round(current_raw * 6.5) if current_raw is not None else None,
    }
    snapshot['register_reads_ok'] = all(
        snapshot[name] is not None
        for name in ('torque_enabled', 'position', 'voltage', 'temperature')
    )
    return snapshot


def leg_hardware_check():
    if not BUS.is_open:
        return {
            'pass': False,
            'safe_to_calibrate': False,
            'reason': 'serial bus is not connected',
            'roles': {},
            'warnings': ['Connect the FE-URT-2, then scan the bus.'],
        }

    config = CALIBRATION.load()
    roles = {}
    warnings = []
    safe = True
    tracked_ids = set(TEL.ids)
    ping_only_roles = []
    for name in ROLE_NAMES:
        role_config = config['roles'][name]
        sid = int(role_config['id'])
        snapshot = servo_snapshot(sid)
        roles[name] = snapshot
        if not snapshot['present']:
            safe = False
            warnings.append(f'{name}: ID {sid} did not answer')
            continue
        tracked_ids.add(sid)
        if not snapshot['register_reads_ok']:
            safe = False
            ping_only_roles.append(name)
            warnings.append(f'{name}: ID {sid} pings but its registers are unreadable')
        if snapshot['torque_enabled'] is None:
            safe = False
        elif snapshot['torque_enabled'] != 0:
            safe = False
            warnings.append(f'{name}: torque is enabled; turn it off before calibration')
        volts = snapshot['voltage']
        if volts is None:
            safe = False
            warnings.append(f'{name}: rail voltage could not be read')
        elif not RAIL_MIN <= volts <= RAIL_MAX:
            safe = False
            warnings.append(f'{name}: rail {volts} V is outside {RAIL_MIN}-{RAIL_MAX} V')
        temperature = snapshot['temperature']
        if temperature is not None and temperature > 50:
            safe = False
            warnings.append(f'{name}: {temperature} C is too warm for a cold bench check')
        current = snapshot['current_ma']
        if snapshot['torque_enabled'] == 0 and current is not None and current > 250:
            safe = False
            warnings.append(f'{name}: {current} mA with torque off needs investigation')
    present_ids = [snapshot['id'] for snapshot in roles.values() if snapshot.get('present')]
    if ping_only_roles and present_ids == [1]:
        warnings.insert(0,
            'Probable duplicate factory ID 1: disconnect two servos and assign IDs one at a time')
    TEL.track(sorted(tracked_ids))
    return {
        'pass': safe,
        'safe_to_calibrate': safe,
        'ready': calibration_ready(config),
        'roles': roles,
        'warnings': warnings,
    }


def require_torque_off(sid):
    if not BUS.is_open:
        raise RuntimeError('serial bus is not connected')
    torque = BUS.read(sid, *REG['torque_enable'])
    if torque is None:
        raise RuntimeError(f'ID {sid} did not answer')
    if torque != 0:
        raise RuntimeError(f'ID {sid} torque is enabled; turn it off first')


def require_all_leg_torque_off(config):
    for role_name in ROLE_NAMES:
        require_torque_off(int(config['roles'][role_name]['id']))


def linkage_guard(config, joints_rad):
    q3_deg = joints_rad[2] * 180.0 / 3.141592653589793
    linkage = config['linkage']
    relative_input = q3_deg - float(linkage['reference_q3_deg'])
    cad_minimum = float(linkage['relative_input_min_deg'])
    cad_maximum = float(linkage['relative_input_max_deg'])
    margin = float(linkage.get('commissioning_margin_deg', 0.0))
    minimum = cad_minimum + margin
    maximum = cad_maximum - margin
    return {
        'relative_input_deg': relative_input,
        'minimum_deg': minimum,
        'maximum_deg': maximum,
        'within_limits': minimum <= relative_input <= maximum,
        'within_cad_limits': cad_minimum <= relative_input <= cad_maximum,
        'cad_minimum_deg': cad_minimum,
        'cad_maximum_deg': cad_maximum,
        'commissioning_margin_deg': margin,
        'nearest_safe_boundary_deg': min(relative_input - minimum, maximum - relative_input),
        'q3_safe_min_deg': float(linkage['reference_q3_deg']) + minimum,
        'q3_safe_max_deg': float(linkage['reference_q3_deg']) + maximum,
        'q3_cad_min_deg': float(linkage['reference_q3_deg']) + cad_minimum,
        'q3_cad_max_deg': float(linkage['reference_q3_deg']) + cad_maximum,
    }


def leg_ik_payload(body):
    config = CALIBRATION.load()
    geometry = geometry_from_config(config)
    target = (
        float(body['x_mm']),
        float(body['y_mm']),
        float(body['z_mm']),
    )
    knee_sign = int(body.get('knee_sign', config['knee_sign']))
    result = ik_tip_mm(geometry, target, knee_sign=knee_sign)
    payload = {
        'reachable': result.reachable,
        'target_mm': list(result.target_mm),
        'workspace_mm': {
            'planar_distance': result.planar_distance_mm,
            'minimum': result.min_reach_mm,
            'maximum': result.max_reach_mm,
        },
        'reason': result.reason,
        'calibration_ready': calibration_ready(config),
        'motion_enabled': False,
    }
    if not result.reachable:
        return payload

    joints_rad = result.joints_rad
    servo_rad = servo_angles_from_joints(joints_rad)
    joint_deg = degrees(joints_rad)
    linkage_check = linkage_guard(config, joints_rad)
    tick_targets = {}
    for name in ROLE_NAMES:
        try:
            target_tick = tick_target(name, servo_rad[name], config['roles'][name])
            tick_targets[name] = {
                'requested': target_tick.requested_tick,
                'within_limits': target_tick.within_limits,
                'min': target_tick.min_tick,
                'max': target_tick.max_tick,
            }
        except ValueError as error:
            tick_targets[name] = {'requested': None, 'within_limits': None, 'reason': str(error)}
    known_limits = all(value['within_limits'] is not None for value in tick_targets.values())
    raw_limits_pass = (
        all(value['within_limits'] for value in tick_targets.values())
        if known_limits else None
    )
    combined_pass = (
        False if not linkage_check['within_limits']
        else raw_limits_pass
    )
    payload.update({
        'joints_deg': {'roll': joint_deg[0], 'hip': joint_deg[1], 'knee': joint_deg[2]},
        'servo_deg': {name: round(value * 180.0 / 3.141592653589793, 6)
                      for name, value in servo_rad.items()},
        'ticks': tick_targets,
        'raw_limits_pass': raw_limits_pass,
        'linkage_check': linkage_check,
        'within_calibrated_limits': combined_pass,
        'fk_error_mm': result.fk_error_mm,
    })
    return payload


def current_leg_pose():
    config = CALIBRATION.load()
    raw = {}
    servo_angles = {}
    errors = []
    for name in ROLE_NAMES:
        role = config['roles'][name]
        sid = int(role['id'])
        if not BUS.is_open:
            errors.append('serial bus is not connected')
            break
        position = BUS.read(sid, *REG['position'])
        if position is None:
            errors.append(f'{name}: ID {sid} position read failed')
            continue
        raw[name] = position
        try:
            servo_angles[name] = radians_from_tick(position, role)
        except ValueError as error:
            errors.append(f'{name}: {error}')
    payload = {'ticks': raw, 'errors': errors}
    if len(servo_angles) == len(ROLE_NAMES):
        joints = joints_from_servo_angles(servo_angles)
        tip = fk_tip_mm(geometry_from_config(config), joints)
        joint_deg = degrees(joints)
        payload.update({
            'joints_deg': {'roll': joint_deg[0], 'hip': joint_deg[1], 'knee': joint_deg[2]},
            'servo_deg': {name: value * 180.0 / 3.141592653589793
                          for name, value in servo_angles.items()},
            'tip_mm': {'x': tip[0], 'y': tip[1], 'z': tip[2]},
            'linkage_check': linkage_guard(config, joints),
        })
    return payload


_WORKSPACE_CACHE = {'key': None, 'value': None}


def _angle_range(role):
    low = radians_from_tick(int(role['min_tick']), role)
    high = radians_from_tick(int(role['max_tick']), role)
    return min(low, high), max(low, high)


def leg_workspace(config=None):
    """Return calibrated joint ROM and a sampled planar foot envelope."""
    config = config or CALIBRATION.load()
    if not calibration_ready(config):
        raise ValueError('complete calibration is required to build the workspace')
    key = json.dumps({
        'geometry': config['geometry'],
        'linkage': config['linkage'],
        'roles': config['roles'],
    }, sort_keys=True)
    if _WORKSPACE_CACHE['key'] == key:
        return _WORKSPACE_CACHE['value']

    geometry = geometry_from_config(config)
    q1_min, q1_max = _angle_range(config['roles']['roll'])
    q2_min, q2_max = _angle_range(config['roles']['hip'])
    alpha_min, alpha_max = _angle_range(config['roles']['knee_driver'])
    linkage = config['linkage']
    margin = math.radians(float(linkage.get('commissioning_margin_deg', 0.0)))
    q3_min = math.radians(float(linkage['reference_q3_deg']) +
                          float(linkage['relative_input_min_deg'])) + margin
    q3_max = math.radians(float(linkage['reference_q3_deg']) +
                          float(linkage['relative_input_max_deg'])) - margin

    def planar_tip(q2, q3):
        return (
            geometry.hip_offset_mm + geometry.femur_mm * math.sin(q2)
            + geometry.tibia_mm * math.sin(q2 + q3),
            geometry.femur_mm * math.cos(q2)
            + geometry.tibia_mm * math.cos(q2 + q3),
        )

    lower_curve, upper_curve, projection_samples = [], [], []
    q2_steps, q3_steps = 160, 80
    for index in range(q2_steps + 1):
        q2 = q2_min + (q2_max - q2_min) * index / q2_steps
        low = max(q3_min, alpha_min - q2)
        high = min(q3_max, alpha_max - q2)
        if low > high:
            continue
        low_tip, high_tip = planar_tip(q2, low), planar_tip(q2, high)
        lower_curve.append({'x': low_tip[0], 'down': low_tip[1]})
        upper_curve.append({'x': high_tip[0], 'down': high_tip[1]})
        for knee_index in range(q3_steps + 1):
            q3 = low + (high - low) * knee_index / q3_steps
            x, down = planar_tip(q2, q3)
            projection_samples.append((x, down, q2, q3))
    if not projection_samples:
        raise ValueError('calibrated hip, knee-driver and coupled ranges do not overlap')

    envelope = lower_curve + list(reversed(upper_curve))
    result = {
        'ranges_deg': {
            'roll': [math.degrees(q1_min), math.degrees(q1_max)],
            'hip': [math.degrees(q2_min), math.degrees(q2_max)],
            'knee_driver_absolute': [math.degrees(alpha_min), math.degrees(alpha_max)],
            'knee_relative': [math.degrees(q3_min), math.degrees(q3_max)],
        },
        'envelope': envelope,
        '_projection_samples': projection_samples,
        '_ranges_rad': {
            'roll': (q1_min, q1_max),
        },
    }
    _WORKSPACE_CACHE['key'] = key
    _WORKSPACE_CACHE['value'] = result
    return result


def public_workspace_payload(config=None):
    workspace = leg_workspace(config)
    return {
        'ranges_deg': workspace['ranges_deg'],
        'envelope': workspace['envelope'],
    }


def project_leg_target(body):
    """Project a cursor target to the nearest calibrated, coupled-safe pose."""
    config = CALIBRATION.load()
    workspace = leg_workspace(config)
    original = (float(body['x_mm']), float(body['y_mm']), float(body['z_mm']))
    if not all(math.isfinite(value) for value in original):
        raise ValueError('target coordinates must be finite')
    x, y, z = original
    desired_down = math.hypot(y, z)
    desired_roll = math.atan2(y, -z)
    q1_min, q1_max = workspace['_ranges_rad']['roll']
    q1 = max(q1_min, min(q1_max, desired_roll))

    best = min(
        workspace['_projection_samples'],
        key=lambda sample: (sample[0] - x) ** 2 + (sample[1] - desired_down) ** 2,
    )
    projected_x, projected_down, q2, q3 = best
    projected = (
        projected_x,
        projected_down * math.sin(q1),
        -projected_down * math.cos(q1),
    )
    ik = leg_ik_payload({
        'x_mm': projected[0], 'y_mm': projected[1], 'z_mm': projected[2],
        'knee_sign': -1,
    })
    if not ik['reachable'] or ik['within_calibrated_limits'] is not True:
        raise RuntimeError('nearest workspace sample failed the final calibrated limit check')
    distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(original, projected)))
    return {
        'requested_target_mm': {'x': x, 'y': y, 'z': z},
        'target_mm': {'x': projected[0], 'y': projected[1], 'z': projected[2]},
        'projected': distance > 0.25,
        'projection_distance_mm': distance,
        'joints_deg': {'roll': math.degrees(q1), 'hip': math.degrees(q2),
                       'knee': math.degrees(q3)},
        'ik': ik,
    }


class MotionController:
    """Guarded 20 Hz drag controller with a server-side deadman."""

    def __init__(self):
        self.lock = threading.RLock()
        self.active = False
        self.token = None
        self.ids = []
        self.commanded = {}
        self.desired = {}
        self.armed_at = 0.0
        self.last_heartbeat = 0.0
        self.last_reason = 'never armed'
        self.profile = motion_profile(MOTION_DEFAULT_SPEED_PERCENT)
        threading.Thread(target=self._loop, daemon=True).start()

    @staticmethod
    def _goal_rows(ids, ticks, speed=MOTION_SPEED, acceleration=MOTION_ACCELERATION):
        rows = []
        for sid in ids:
            position = int(ticks[sid])
            rows.append((sid, bytes([
                acceleration,
                position & 0xFF, (position >> 8) & 0xFF,
                0, 0,
                speed & 0xFF, (speed >> 8) & 0xFF,
            ])))
        return rows

    def _sync_goals(self, ids, ticks):
        return BUS.sync_write(REG['acceleration'][0], self._goal_rows(
            ids, ticks, self.profile['speed'], self.profile['acceleration']))

    def arm(self, confirmed=False, speed_percent=MOTION_DEFAULT_SPEED_PERCENT):
        if not confirmed:
            raise RuntimeError('fixture/hands-clear confirmation is required')
        config = CALIBRATION.load()
        if not calibration_ready(config):
            raise RuntimeError('reference ticks, signs and both endpoints must be calibrated first')
        self.profile = motion_profile(speed_percent)
        check = leg_hardware_check()
        if not check['safe_to_calibrate']:
            raise RuntimeError('; '.join(check['warnings']) or 'hardware safety check failed')

        ids = [int(config['roles'][name]['id']) for name in ROLE_NAMES]
        positions = {}
        servo_angles = {}
        for name, sid in zip(ROLE_NAMES, ids):
            role = config['roles'][name]
            snapshot = check['roles'][name]
            position = int(snapshot['position'])
            if not int(role['min_tick']) <= position <= int(role['max_tick']):
                raise RuntimeError(f'{name}: current tick {position} is outside its calibrated range')
            if BUS.read(sid, *REG['mode']) != 0:
                raise RuntimeError(f'{name}: ID {sid} is not in angle-servo mode 0')
            positions[sid] = position
            servo_angles[name] = radians_from_tick(position, role)
        joints = joints_from_servo_angles(servo_angles)
        guard = linkage_guard(config, joints)
        if not guard['within_limits']:
            raise RuntimeError(
                f"current relative linkage input {guard['relative_input_deg']:.1f} deg "
                f"is outside {guard['minimum_deg']:.1f}..{guard['maximum_deg']:.1f} deg"
            )

        for sid in ids:
            if not BUS.write(sid, REG['torque_limit'][0], MOTION_TORQUE_LIMIT, 2):
                raise RuntimeError(f'ID {sid}: could not set the temporary torque limit')
        if not self._sync_goals(ids, positions):
            raise RuntimeError('could not preload synchronized current-position goals')

        enabled = []
        try:
            for sid in ids:
                if not BUS.write(sid, REG['torque_enable'][0], 1, 1):
                    raise RuntimeError(f'ID {sid}: torque enable failed')
                enabled.append(sid)
        except Exception:
            for sid in enabled:
                BUS.write(sid, REG['torque_enable'][0], 0, 1)
            raise

        now = time.monotonic()
        with self.lock:
            self.active = True
            self.token = secrets.token_urlsafe(18)
            self.ids = ids
            self.commanded = dict(positions)
            self.desired = dict(positions)
            self.armed_at = now
            self.last_heartbeat = now
            self.last_reason = 'armed and holding current pose'
            token = self.token
        TEL.track(ids)
        tip = fk_tip_mm(geometry_from_config(config), joints)
        joint_deg = degrees(joints)
        return {
            'token': token,
            'pose': {
                'joints_deg': {'roll': joint_deg[0], 'hip': joint_deg[1], 'knee': joint_deg[2]},
                'servo_deg': {name: value * 180.0 / 3.141592653589793
                              for name, value in servo_angles.items()},
                'tip_mm': {'x': tip[0], 'y': tip[1], 'z': tip[2]},
                'linkage_check': guard,
            },
            **self.state(),
        }

    def _check_token(self, token):
        with self.lock:
            if not self.active or not token or token != self.token:
                raise RuntimeError('motion session is not armed or its token expired')

    def heartbeat(self, token):
        self._check_token(token)
        with self.lock:
            self.last_heartbeat = time.monotonic()
        return self.state()

    def set_target(self, token, body):
        self._check_token(token)
        projection = project_leg_target(body)
        result = projection['ik']
        config = CALIBRATION.load()
        desired = {}
        for name in ROLE_NAMES:
            sid = int(config['roles'][name]['id'])
            desired[sid] = int(result['ticks'][name]['requested'])
        with self.lock:
            if not self.active or token != self.token:
                raise RuntimeError('motion session expired while projecting the target')
            self.desired = desired
            self.last_heartbeat = time.monotonic()
            self.last_reason = 'following guarded drag target'
        return {'accepted': True, 'ticks': desired, 'ik': result,
                'projection': projection, **self.state()}

    def disarm(self, token=None, reason='user disarm'):
        with self.lock:
            if token is not None and self.active and token != self.token:
                raise RuntimeError('motion token does not match the active session')
            ids = list(self.ids)
            was_active = self.active
            self.active = False
            self.token = None
            self.desired = {}
            self.last_reason = reason
        disabled = []
        for sid in ids:
            if BUS.is_open and BUS.write(sid, REG['torque_enable'][0], 0, 1):
                disabled.append(sid)
        return {'ok': True, 'was_active': was_active, 'torque_off': disabled,
                'reason': reason}

    def state(self):
        with self.lock:
            now = time.monotonic()
            return {
                'active': self.active,
                'commanded': dict(self.commanded),
                'desired': dict(self.desired),
                'reason': self.last_reason,
                'deadman_ms': max(0, round((MOTION_DEADMAN_SECONDS -
                                            (now - self.last_heartbeat)) * 1000))
                    if self.active else 0,
                'arm_remaining_s': max(0.0, MOTION_MAX_ARM_SECONDS -
                                       (now - self.armed_at)) if self.active else 0.0,
                'limits': {
                    'loop_hz': MOTION_HZ,
                    **self.profile,
                    'torque_limit_per_mille': MOTION_TORQUE_LIMIT,
                    'max_current_ma': MOTION_MAX_CURRENT_MA,
                    'max_temperature_c': MOTION_MAX_TEMP_C,
                },
            }

    def _telemetry_fault(self, now):
        if now - self.armed_at < 1.0:
            return None
        for sid in self.ids:
            sample = TEL.latest.get(sid)
            if not sample or time.time() - sample['t'] > 0.8:
                return f'ID {sid}: live telemetry timeout'
            if not RAIL_MIN <= sample['voltage'] <= RAIL_MAX:
                return f"ID {sid}: rail {sample['voltage']} V outside safe range"
            if sample['temperature'] > MOTION_MAX_TEMP_C:
                return f"ID {sid}: temperature {sample['temperature']} C exceeded limit"
            if abs(sample['current_ma']) > MOTION_MAX_CURRENT_MA:
                return f"ID {sid}: current {sample['current_ma']} mA exceeded limit"
        return None

    def _loop(self):
        period = 1.0 / MOTION_HZ
        while True:
            time.sleep(period)
            with self.lock:
                if not self.active:
                    continue
                now = time.monotonic()
                if now - self.last_heartbeat > MOTION_DEADMAN_SECONDS:
                    fault = 'deadman timeout: browser heartbeat stopped'
                elif now - self.armed_at > MOTION_MAX_ARM_SECONDS:
                    fault = 'maximum 60 second arm window expired'
                else:
                    fault = self._telemetry_fault(now)
                ids = list(self.ids)
                commanded = dict(self.commanded)
                desired = dict(self.desired)
            if fault:
                self.disarm(reason=fault)
                continue
            next_ticks = {}
            changed = False
            for sid in ids:
                current = commanded[sid]
                delta = desired[sid] - current
                step = max(-self.profile['max_step_ticks'],
                           min(self.profile['max_step_ticks'], delta))
                next_ticks[sid] = current + step
                changed = changed or step != 0
            if changed:
                if not self._sync_goals(ids, next_ticks):
                    self.disarm(reason='synchronized goal write failed')
                    continue
                with self.lock:
                    if self.active:
                        self.commanded = next_ticks


MOTION = MotionController()


# --- HTTP -------------------------------------------------------------------
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        raw = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        n = int(self.headers.get('Content-Length', 0) or 0)
        return json.loads(self.rfile.read(n) or b'{}')

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/api/ports':
            ports = [{'device': p.device, 'desc': p.description, 'hwid': p.hwid}
                     for p in serial.tools.list_ports.comports()]
            return self._json({'ports': ports,
                               'connected': BUS.port_name, 'baud': BUS.baud})
        if path == '/api/telemetry':
            q = dict(kv.split('=', 1) for kv in self.path.split('?')[1].split('&')) \
                if '?' in self.path else {}
            rows, seq, latest = TEL.since(int(q.get('since', 0)))
            return self._json({'rows': rows, 'seq': seq, 'latest': latest,
                               'ids': TEL.ids, 'open': BUS.is_open,
                               'txns': BUS.txns, 'errors': BUS.errors})
        if path == '/api/leg/config':
            return self._json(leg_config_payload())
        if path == '/api/leg/workspace':
            try:
                return self._json(public_workspace_payload())
            except ValueError as error:
                return self._json({'error': str(error)}, 409)
        if path == '/api/leg/motion_state':
            return self._json(MOTION.state())
        if path in ('/', '/index.html'):
            self.path = '/index.html'
        return super().do_GET()

    def do_POST(self):
        path = self.path.split('?')[0]
        try:
            b = self._body()
        except Exception:
            return self._json({'error': 'bad json'}, 400)

        if path == '/api/connect':
            try:
                BUS.open(b['port'], int(b.get('baud', 1000000)))
                return self._json({'ok': True, 'port': BUS.port_name, 'baud': BUS.baud})
            except Exception as e:
                return self._json({'error': str(e)}, 400)

        if path == '/api/disconnect':
            MOTION.disarm(reason='bus disconnect')
            BUS.close()
            TEL.track([])
            return self._json({'ok': True})

        if path == '/api/scan':
            found = []
            for sid in range(int(b.get('from', 0)), int(b.get('to', 20)) + 1):
                if BUS.ping(sid):
                    found.append(sid)
            TEL.track(found)
            info = {}
            for sid in found:
                max_volt = BUS.read(sid, *REG['max_volt'])
                min_volt = BUS.read(sid, *REG['min_volt'])
                info[str(sid)] = {
                    'max_volt': max_volt * 0.1 if max_volt is not None else None,
                    'min_volt': min_volt * 0.1 if min_volt is not None else None,
                    'max_temp': BUS.read(sid, *REG['max_temp']),
                    'mode': BUS.read(sid, *REG['mode']),
                }
            return self._json({'found': found, 'info': info})

        if path == '/api/leg/check':
            return self._json(leg_hardware_check())

        if path == '/api/leg/sign':
            try:
                config = CALIBRATION.set_sign(str(b['role']), int(b['sign']))
                return self._json({'ok': True, 'config': config,
                                   'ready': calibration_ready(config)})
            except (KeyError, TypeError, ValueError) as error:
                return self._json({'error': str(error)}, 400)

        if path == '/api/leg/capture_neutral':
            if b.get('confirm') is not True:
                return self._json({'error': 'set confirm=true after placing the leg in the printed reference pose'}, 409)
            try:
                config = CALIBRATION.load()
                captured = {}
                for name in ROLE_NAMES:
                    sid = int(config['roles'][name]['id'])
                    require_torque_off(sid)
                    position = BUS.read(sid, *REG['position'])
                    if position is None:
                        raise RuntimeError(f'{name}: ID {sid} position read failed')
                    captured[name] = position
                for name, position in captured.items():
                    config['roles'][name]['center_tick'] = position
                config = CALIBRATION.save(config)
                return self._json({'ok': True, 'captured': captured, 'config': config,
                                   'ready': calibration_ready(config)})
            except (RuntimeError, ValueError) as error:
                return self._json({'error': str(error)}, 409)

        if path == '/api/leg/capture_limit':
            try:
                role = str(b['role'])
                field = str(b['field'])
                if field not in ('min_tick', 'max_tick'):
                    raise ValueError('field must be min_tick or max_tick')
                config = CALIBRATION.load()
                if role not in ROLE_NAMES:
                    raise ValueError(f'unknown role: {role}')
                sid = int(config['roles'][role]['id'])
                require_all_leg_torque_off(config)
                position = BUS.read(sid, *REG['position'])
                if position is None:
                    raise RuntimeError(f'{role}: ID {sid} position read failed')
                config = CALIBRATION.capture(role, field, position)
                return self._json({'ok': True, 'role': role, 'field': field,
                                   'tick': position, 'config': config,
                                   'ready': calibration_ready(config)})
            except (KeyError, RuntimeError, TypeError, ValueError) as error:
                return self._json({'error': str(error)}, 409)

        if path == '/api/leg/capture_endpoint':
            try:
                role = str(b['role'])
                endpoint = str(b['endpoint']).lower()
                config = CALIBRATION.load()
                if role not in ROLE_NAMES:
                    raise ValueError(f'unknown role: {role}')
                if endpoint not in ('a', 'b'):
                    raise ValueError('endpoint must be a or b')
                sid = int(config['roles'][role]['id'])
                require_all_leg_torque_off(config)
                position = BUS.read(sid, *REG['position'])
                if position is None:
                    raise RuntimeError(f'{role}: ID {sid} position read failed')
                config = CALIBRATION.capture_endpoint(role, endpoint, position)
                role_config = config['roles'][role]
                return self._json({
                    'ok': True,
                    'role': role,
                    'endpoint': endpoint,
                    'tick': position,
                    'sorted_range': {
                        'min': role_config.get('min_tick'),
                        'max': role_config.get('max_tick'),
                    },
                    'config': config,
                    'ready': calibration_ready(config),
                })
            except (KeyError, RuntimeError, TypeError, ValueError) as error:
                return self._json({'error': str(error)}, 409)

        if path == '/api/leg/ik':
            try:
                return self._json(leg_ik_payload(b))
            except (KeyError, TypeError, ValueError) as error:
                return self._json({'error': str(error)}, 400)

        if path == '/api/leg/current_pose':
            try:
                return self._json(current_leg_pose())
            except RuntimeError as error:
                return self._json({'error': str(error)}, 409)

        if path == '/api/leg/project':
            try:
                return self._json(project_leg_target(b))
            except (KeyError, TypeError, ValueError, RuntimeError) as error:
                return self._json({'error': str(error)}, 400)

        if path == '/api/leg/arm':
            try:
                return self._json(MOTION.arm(
                    confirmed=b.get('confirm') is True,
                    speed_percent=b.get('speed_percent', MOTION_DEFAULT_SPEED_PERCENT),
                ))
            except RuntimeError as error:
                MOTION.disarm(reason=f'arm refused: {error}')
                return self._json({'error': str(error)}, 409)

        if path == '/api/leg/heartbeat':
            try:
                return self._json(MOTION.heartbeat(str(b.get('token', ''))))
            except RuntimeError as error:
                return self._json({'error': str(error)}, 409)

        if path == '/api/leg/move':
            try:
                target = dict(b)
                token = str(target.pop('token', ''))
                return self._json(MOTION.set_target(token, target))
            except RuntimeError as error:
                MOTION.disarm(reason=f'move refused: {error}')
                return self._json({'error': str(error)}, 409)
            except (KeyError, TypeError, ValueError) as error:
                MOTION.disarm(reason=f'invalid move request: {error}')
                return self._json({'error': str(error)}, 400)

        if path == '/api/leg/disarm':
            try:
                token = b.get('token')
                return self._json(MOTION.disarm(
                    token=str(token) if token else None,
                    reason=str(b.get('reason', 'user disarm')),
                ))
            except RuntimeError as error:
                return self._json({'error': str(error)}, 409)

        if path == '/api/torque':
            sid, on = int(b['id']), 1 if b.get('on') else 0
            return self._json({'ok': BUS.write(sid, REG['torque_enable'][0], on, 1)})

        if path == '/api/goal':
            sid = int(b['id'])
            pos = max(POS_MIN, min(POS_MAX, int(b['position'])))
            ok, v = rail_ok(sid)
            if not ok and not b.get('force'):
                return self._json({'error': f'rail {v} V outside {RAIL_MIN}-{RAIL_MAX} V '
                                            f'- motor stage will not drive', 'volts': v}, 409)
            if 'acceleration' in b and b['acceleration'] is not None:
                BUS.write(sid, REG['acceleration'][0], max(0, min(255, int(b['acceleration']))), 1)
            if 'speed' in b and b['speed'] is not None:
                BUS.write(sid, REG['goal_speed'][0], max(0, min(4095, int(b['speed']))), 2)
            return self._json({'ok': BUS.write(sid, REG['goal_position'][0], pos, 2),
                               'position': pos})

        if path == '/api/estop':
            motion_stop = MOTION.disarm(reason='E-STOP')
            done = list(motion_stop['torque_off'])
            done.extend(sid for sid in TEL.ids
                        if sid not in done and BUS.write(sid, REG['torque_enable'][0], 0, 1))
            return self._json({'ok': True, 'torque_off': done})

        if path == '/api/reg_read':
            sid, addr, size = int(b['id']), int(b['addr']), int(b.get('size', 1))
            return self._json({'value': BUS.read(sid, addr, size)})

        if path == '/api/reg_write':
            sid, addr = int(b['id']), int(b['addr'])
            size, val = int(b.get('size', 1)), int(b['value'])
            if addr < 40 and not b.get('eeprom_ok'):
                return self._json({'error': f'addr {addr} is EEPROM - set eeprom_ok'}, 409)
            return self._json({'ok': BUS.write(sid, addr, val, size)})

        if path == '/api/set_id':
            old, new = int(b['id']), int(b['new_id'])
            if not (0 <= new <= 253):
                return self._json({'error': 'new id must be 0..253'}, 400)
            if BUS.ping(new) and new != old:
                return self._json({'error': f'id {new} already answers on this bus'}, 409)
            BUS.write(old, REG['lock'][0], 0, 1)          # unlock EEPROM
            ok = BUS.write(old, REG['id'][0], new, 1)
            time.sleep(0.05)
            BUS.write(new, REG['lock'][0], 1, 1)          # relock at the new address
            time.sleep(0.05)
            confirmed = BUS.ping(new)
            return self._json({'ok': ok and confirmed, 'confirmed': confirmed, 'new_id': new})

        return self._json({'error': 'unknown endpoint'}, 404)


if __name__ == '__main__':
    with http.server.ThreadingHTTPServer(('127.0.0.1', PORT), Handler) as httpd:
        print(f'servo bench at http://localhost:{PORT}/   (serving {HERE})')
        print('  ctrl-c to stop; every tracked servo is torqued off on exit')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            MOTION.disarm(reason='server shutdown')
            for sid in TEL.ids:
                if sid not in MOTION.ids:
                    BUS.write(sid, REG['torque_enable'][0], 0, 1)
            BUS.close()
            print('\ntorque off, bus closed.')
