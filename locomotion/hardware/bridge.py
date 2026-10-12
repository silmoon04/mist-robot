"""Loopback remote and USB bridge. Simulation is the default; hardware needs calibration."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import secrets
import threading
import time
from typing import Any

HERE = Path(__file__).resolve().parent
JOINTS = tuple(f"{leg}_{joint}" for leg in ("FL", "FR", "RL", "RR") for joint in ("yaw", "hip", "knee"))
R7_LIMITS = ((-55, 55), (-30, 65), (5, 115)) * 4
TICKS_PER_RAD = 4096 / (2 * math.pi)


class InterlockError(ValueError):
    pass


def joint_values(q: Any) -> list[float]:
    if not isinstance(q, (list, tuple)) or len(q) != 12:
        raise InterlockError("q must have 12 radians in FL, FR, RL, RR yaw/hip/knee order")
    out = []
    for name, value, bounds in zip(JOINTS, q, R7_LIMITS):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise InterlockError(f"{name}: angle must be finite")
        if not math.radians(bounds[0]) <= value <= math.radians(bounds[1]):
            raise InterlockError(f"{name}: outside provisional R7 CAD limits {bounds}")
        out.append(float(value))
    return out


@dataclass(frozen=True)
class Calibration:
    data: dict
    digest: str

    @classmethod
    def load(cls, path: Path) -> "Calibration":
        data = json.loads(path.read_text())
        if data.get("model") != "mist_r7_direct" or data.get("schema_version") != 1:
            raise InterlockError("requires schema 1 mist_r7_direct calibration; old four-bar ticks are incompatible")
        if data.get("verified_on_robot") is not True:
            raise InterlockError("calibration has not been verified on this robot")
        if data.get("estop_nc_verified") is not True:
            raise InterlockError("normally closed physical stop loop must be verified first")
        rows = data.get("joints", [])
        if len(rows) != 12 or [r.get("name") for r in rows] != list(JOINTS):
            raise InterlockError("requires one ordered calibration row per direct-drive joint")
        seen = set()
        for index, row in enumerate(rows):
            name = row["name"]
            if row.get("measured") is not True:
                raise InterlockError(f"{name}: measurements have not been confirmed")
            for key in ("id", "center_tick", "min_tick", "max_tick", "sign"):
                if type(row.get(key)) is not int:
                    raise InterlockError(f"{name}: {key} must be an integer")
            if not 1 <= row["id"] <= 253 or row["id"] in seen:
                raise InterlockError("servo IDs must be unique in 1..253")
            seen.add(row["id"])
            if row["sign"] not in (-1, 1):
                raise InterlockError(f"{name}: sign must be -1 or +1")
            if not 0 <= row["min_tick"] <= row["center_tick"] <= row["max_tick"] <= 4095:
                raise InterlockError(f"{name}: invalid non-wrapping tick limits")
            angle = row.get("reference_rad")
            if isinstance(angle, bool) or not isinstance(angle, (int, float)) or not math.isfinite(angle):
                raise InterlockError(f"{name}: reference_rad must be measured and finite")
            lower, upper = R7_LIMITS[index]
            if not math.radians(lower) <= angle <= math.radians(upper):
                raise InterlockError(f"{name}: reference angle lies outside R7 CAD bounds")
        encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return cls(data, hashlib.sha256(encoded).hexdigest())

    def ticks(self, q: Any) -> list[int]:
        out = []
        for angle, row in zip(joint_values(q), self.data["joints"]):
            tick = round(row["center_tick"] + row["sign"] * (angle - row["reference_rad"]) * TICKS_PER_RAD)
            if not row["min_tick"] <= tick <= row["max_tick"]:
                raise InterlockError(f"{row['name']}: requested tick {tick} exceeds measured limits")
            out.append(tick)
        return out

    def radians(self, ticks: list[int]) -> list[float]:
        if len(ticks) != 12:
            raise InterlockError("incomplete telemetry")
        return [r["reference_rad"] + r["sign"] * (t - r["center_tick"]) / TICKS_PER_RAD for t, r in zip(ticks, self.data["joints"])]

    def header(self) -> str:
        rows = self.data["joints"]
        def array(key):
            return ", ".join(str(row[key]) for row in rows)
        return (
            "// Generated from measured direct-drive calibration. Keep this profile with the host JSON.\n"
            "#pragma once\n#include <stdint.h>\n"
            "constexpr bool PROFILE_CONFIGURED = true;\n"
            f'constexpr char PROFILE_HASH[] = "{self.digest}";\n'
            f"constexpr uint8_t SERVO_IDS[12] = {{{array('id')}}};\n"
            f"constexpr int16_t MIN_TICKS[12] = {{{array('min_tick')}}};\n"
            f"constexpr int16_t MAX_TICKS[12] = {{{array('max_tick')}}};\n"
        )


class SerialLink:
    """One request/ack at a time; async telemetry never substitutes for an ack."""
    def __init__(self, port: str):
        import serial
        self.serial = serial.Serial(port, 460800, timeout=0.02, write_timeout=0.2)
        self.lock = threading.RLock()
        self.telemetry = {}
        self.imu_packet = {}
        self.imu_received_at = 0.0
        self.seq = 0
        self.received_at = 0.0
        # Opening USB commonly resets the ESP32. Status also recovers a still-running sequence.
        time.sleep(2.0)
        self.request("status", sequenced=False)

    def request(self, op: str, sequenced: bool = True, **payload) -> dict:
        with self.lock:
            if sequenced:
                self.seq += 1
            request = {"op": op, "seq": self.seq, **payload}
            self.serial.write((json.dumps(request, allow_nan=False) + "\n").encode())
            deadline = time.monotonic() + 0.6
            while time.monotonic() < deadline:
                line = self.serial.readline()
                if not line:
                    continue
                try:
                    response = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    continue
                if response.get("kind") == "telemetry":
                    self.telemetry = response
                    self.received_at = time.monotonic()
                if response.get("kind") == "imu":
                    self.imu_packet = response
                    self.imu_received_at = time.monotonic()
                if response.get("kind") == "ack" and response.get("op") == op and response.get("seq") == request["seq"]:
                    if op == "status":
                        self.seq = max(self.seq, int(response.get("last_seq", 0)))
                        self.telemetry = response
                        self.received_at = time.monotonic()
                    if not response.get("ok"):
                        raise InterlockError(response.get("error", "firmware refused request"))
                    return response
            raise InterlockError("ESP32 acknowledgement timeout; firmware watchdog must stop motion")

    def close(self):
        try:
            self.request("estop")
        finally:
            self.serial.close()


class Bridge:
    def __init__(self, calibration: Calibration | None = None, link: SerialLink | None = None):
        if link is not None and calibration is None:
            raise InterlockError("hardware requires measured R7 calibration")
        self.calibration, self.link = calibration, link
        self.lock = threading.RLock()
        self.armed = False
        self.intent_generation = 0
        self.slew_credit = [2 / TICKS_PER_RAD] * 12
        self.fault = None
        self.last_heartbeat = 0.0
        self.arm_time = 0.0
        self.last_q_time = 0.0
        self.q = [math.radians(x) for x in (0, 30, 81) * 4]
        self.running = True
        self.gait = None
        self.gait_start = 0.0
        self.command = [0.0, 0.0, 0.0]
        if link:
            status = link.request("status", sequenced=False)
            if status.get("profile_hash") != calibration.digest:
                raise InterlockError("firmware and host calibration hashes differ")
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def status(self):
        with self.lock:
            return {"mode": "hardware commissioning" if self.link else "dry-run", "armed": self.armed,
                    "intent_generation":self.intent_generation, "fault": self.fault, "q": self.q, "joint_order": JOINTS,
                    "calibrated": self.calibration is not None, "profile_hash": self.calibration.digest if self.calibration else None,
                    "gait_active": self.gait is not None, "telemetry": self.link.telemetry if self.link else {},
                    "imu_raw": self.link.imu_packet if self.link else {},
                    "hardware_gait": "disabled until body IMU and loaded commissioning are validated"}

    def _disarm(self, reason=None, estop=False):
        self.intent_generation += 1
        self.armed, self.gait = False, None
        if reason:
            self.fault = reason
        if self.link:
            self.link.request("estop" if estop else "disarm")

    def handle(self, data: dict) -> dict:
        with self.lock:
            op = data.get("op")
            if op == "status":
                return self.status()
            if op in ("estop", "disarm"):
                self._disarm("remote stop" if op == "estop" else None, op == "estop")
            elif op == "clear":
                if data.get("intent_generation") != self.intent_generation:
                    raise InterlockError("stale clear intent")
                if self.armed:
                    raise InterlockError("disarm before clearing a fault")
                if self.link:
                    self.link.request("clear")
                self.fault = None
            elif op == "arm":
                if data.get("intent_generation") != self.intent_generation or self.armed:
                    raise InterlockError("stale or duplicate arm intent")
                if self.fault:
                    raise InterlockError("clear the latched fault after inspection")
                if self.link:
                    if data.get("unloaded_fixture_confirmed") is not True:
                        raise InterlockError("confirm the robot is restrained with no foot load")
                    status=self.link.request("status",sequenced=False)
                    response = self.link.request("arm", profile_hash=self.calibration.digest, intent_generation=status.get("intent_generation"))
                    self.q = self.calibration.radians(response["ticks"])
                self.armed = True
                self.intent_generation += 1
                self.slew_credit = [2 / TICKS_PER_RAD] * 12
                self.arm_time = self.last_heartbeat = self.last_q_time = time.monotonic()
            elif op == "heartbeat":
                if not self.armed:
                    raise InterlockError("remote is disarmed")
                self.last_heartbeat = time.monotonic()
                if self.link:
                    self.link.request("heartbeat")
            elif op == "q":
                q = joint_values(data.get("q"))
                if not self.armed:
                    raise InterlockError("arm before sending targets")
                if self.link:
                    now = time.monotonic()
                    dt = min(0.1, max(0.0, now - self.last_q_time))
                    credits=[min(.05+2/TICKS_PER_RAD,c+.5*dt) for c in self.slew_credit]
                    changes=[abs(a-b) for a,b in zip(q,self.q)]
                    if any(d>c+1e-12 for d,c in zip(changes,credits)):
                        raise InterlockError("joint target step exceeds commissioning rate 0.5 rad/s")
                    self.link.request("ticks", ticks=self.calibration.ticks(q))
                    self.last_q_time = now
                    self.slew_credit=[c-d for c,d in zip(credits,changes)]
                self.q, self.gait = q, None
            elif op == "gait":
                if self.link:
                    raise InterlockError("physical gait is disabled; fixed-body IMU and loaded commissioning are missing")
                if not self.armed:
                    raise InterlockError("arm the dry-run first")
                command = data.get("command")
                if not isinstance(command, list) or len(command) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) for x in command):
                    raise InterlockError("command must be [vx_m_s, vy_m_s, yaw_rad_s]")
                if abs(command[0]) > 0.05 or abs(command[1]) > 0.05 or abs(command[2]) > 0.2:
                    raise InterlockError("remote preview limits: vx/vy <=0.05 m/s, yaw <=0.2 rad/s")
                from locomotion.gait import CrawlController
                self.gait = self.gait or CrawlController()
                self.gait_start = time.monotonic()
                self.command = command
            elif op == "ik":
                # Analytic direct R7 leg solve in local yaw coordinates; no hardware write.
                xyz = data.get("xyz_m")
                if not isinstance(xyz, list) or len(xyz) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) for x in xyz):
                    raise InterlockError("xyz_m must be three finite metres")
                x, y, z = xyz
                planar = math.hypot(x, y) - 0.082
                c = (planar * planar + z * z - 0.09**2 - 0.105**2) / (2 * 0.09 * 0.105)
                if not -1 <= c <= 1:
                    raise InterlockError("target outside R7 leg reach")
                knee = math.acos(c)
                hip = math.atan2(-z, planar) - math.atan2(0.105 * math.sin(knee), 0.09 + 0.105 * math.cos(knee))
                angles = [math.atan2(y, x), hip, knee]
                joint_values(angles * 4)
                return {"q_leg": angles, "preview_only": True}
            else:
                raise InterlockError("unknown operation")
            return self.status()

    def _worker(self):
        while self.running:
            time.sleep(0.03)
            with self.lock:
                if not self.armed:
                    continue
                now = time.monotonic()
                try:
                    if now - self.last_heartbeat > 0.3:
                        self._disarm("browser heartbeat timeout", estop=True)
                    elif now - self.arm_time > 60:
                        self._disarm("60 second commissioning window expired", estop=True)
                    elif self.gait is not None:
                        self.q = joint_values(self.gait.position_targets(now - self.gait_start, self.command, attitude=(0.,0.), phone_mass_kg=.155).tolist())
                    elif self.link and now - self.link.received_at > 0.25:
                        status = self.link.request("status", sequenced=False)
                        if not status.get("armed") or status.get("fault"):
                            self.armed = False
                            self.fault = status.get("fault") or "firmware disarmed"
                except Exception as exc:
                    self.armed, self.gait, self.fault = False, None, str(exc)
                    if self.link:
                        try:
                            self.link.request("estop")
                        except Exception:
                            pass

    def close(self):
        self.running = False
        self.thread.join(timeout=1.0)
        if self.link:
            self.link.close()


def serve(bridge: Bridge, port: int):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, value, mime="application/json"):
            body = value if isinstance(value, bytes) else json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                return self.send(403, {"error": "loopback Host required"})
            if self.path == "/":
                body = (HERE / "remote.html").read_text().replace("__SESSION_TOKEN__", token).encode()
                return self.send(200, body, "text/html; charset=utf-8")
            if self.path == "/api/status":
                return self.send(200, bridge.status())
            return self.send(404, {"error": "unknown route"})

        def do_POST(self):
            if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}") or self.headers.get("X-Mist-Token") != token:
                return self.send(403, {"error": "local session token required"})
            if self.path != "/api/command":
                return self.send(404, {"error": "unknown route"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 1 <= size <= 4096:
                    raise InterlockError("invalid request size")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise InterlockError("JSON object required")
                return self.send(200, bridge.handle(data))
            except (ValueError, KeyError, TypeError) as exc:
                return self.send(400, {"error": str(exc)})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"MIST {'hardware commissioning' if bridge.link else 'dry-run'} remote: http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()
        bridge.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8130)
    parser.add_argument("--serial", help="ESP32 USB serial port; omitted means dry-run")
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--write-header", type=Path, help="generate the firmware profile from verified measurements")
    args = parser.parse_args()
    calibration = Calibration.load(args.calibration) if args.calibration else None
    if args.write_header:
        if not calibration:
            parser.error("--write-header needs --calibration")
        args.write_header.write_text(calibration.header())
        print(f"Wrote calibrated profile {calibration.digest}")
        return
    if args.serial and not calibration:
        parser.error("--serial requires measured --calibration")
    link = SerialLink(args.serial) if args.serial else None
    try:
        bridge = Bridge(calibration, link)
    except Exception:
        if link:
            link.close()
        raise
    serve(bridge, args.port)


if __name__ == "__main__":
    main()
