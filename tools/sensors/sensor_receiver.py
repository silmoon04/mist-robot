#!/usr/bin/env python3
"""
Sensor-stream receiver for the Mi 9 SE robot sensor node.

Listens for packets from a phone sensor-streaming app (e.g. "Sensorstream
IMU+GPS" in UDP mode) and prints parsed accelerometer / gyroscope /
magnetometer (and any extra) values. Format-agnostic: it parses the common
"timestamp, code, x,y,z, code, x,y,z, ..." layout and falls back to printing
the raw packet so you can see data regardless of the exact app.

Usage:
    python sensor_receiver.py                 # UDP on 0.0.0.0:5555
    python sensor_receiver.py 5555 udp
    python sensor_receiver.py 5555 tcp        # TCP (pair with: adb reverse tcp:5555 tcp:5555)
"""
import socket, sys

PORT  = int(sys.argv[1]) if len(sys.argv) > 1 else 5555
PROTO = (sys.argv[2] if len(sys.argv) > 2 else "udp").lower()

# Sensorstream IMU+GPS prefixes each triple with a numeric sensor code:
CODE = {3: "ACCEL(m/s^2)", 4: "GYRO(rad/s)", 5: "MAG(uT)",
        81: "ORIENT", 82: "LIN_ACCEL", 83: "GRAVITY"}

def parse(line):
    try:
        nums = [float(p.strip()) for p in line.replace(";", ",").split(",") if p.strip()]
    except ValueError:
        return None
    out, i = [], 1  # index 0 is the timestamp
    while i < len(nums):
        code = int(nums[i])
        if code in CODE and i + 4 <= len(nums):
            out.append((CODE[code], nums[i + 1:i + 4]))
            i += 4
        else:
            i += 1
    return out

def show(addr, raw):
    line = raw.decode("utf-8", "replace").strip()
    if not line:
        return
    parsed = parse(line)
    if parsed:
        s = "   ".join(f"{n}=[{v[0]:+.3f}, {v[1]:+.3f}, {v[2]:+.3f}]" for n, v in parsed)
        print(f"{addr[0]:<15} {s}")
    else:
        print(f"{addr[0]:<15} RAW: {line[:140]}")

def main():
    print(f"Listening {PROTO.upper()} on 0.0.0.0:{PORT}   (Ctrl+C to stop)")
    if PROTO == "tcp":
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", PORT)); srv.listen(1)
        conn, addr = srv.accept(); print("TCP client:", addr)
        buf = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                show(addr, line)
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", PORT))
        while True:
            data, addr = s.recvfrom(8192)
            show(addr, data)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped")
