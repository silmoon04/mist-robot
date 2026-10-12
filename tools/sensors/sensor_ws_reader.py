#!/usr/bin/env python3
"""
Read live IMU + magnetometer from the phone's SensorServer app over a USB tunnel.

Setup:
    adb forward tcp:8080 tcp:8080          # PC localhost:8080 -> phone:8080 (no WiFi/firewall)
    pip install websocket-client
    python sensor_ws_reader.py             # connects to ws://127.0.0.1:8080

SensorServer multiplexes several sensors on /sensors/connect?types=[...]; each
JSON message carries {"type", "values":[x,y,z], "accuracy", "timestamp"}.
"""
import json, sys
import websocket  # 'websocket-client' package

HOST  = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:8080"
TYPES = ["android.sensor.accelerometer",
         "android.sensor.gyroscope",
         "android.sensor.magnetic_field"]
URL   = f'ws://{HOST}/sensors/connect?types={json.dumps(TYPES)}'

latest = {}

def fmt(v):
    return "[%+8.3f %+8.3f %+8.3f]" % (v[0], v[1], v[2]) if v else "[    --       --       --   ]"

def on_open(ws):
    print("connected:", URL, flush=True)

def on_message(ws, msg):
    d = json.loads(msg)
    latest[d["type"].split(".")[-1]] = d["values"]
    print("ACC %s  GYR %s  MAG %s" % (
        fmt(latest.get("accelerometer")),
        fmt(latest.get("gyroscope")),
        fmt(latest.get("magnetic_field"))), flush=True)

def on_error(ws, e):
    print("ERR:", e, flush=True)

def on_close(ws, code, reason):
    print("closed:", code, reason, flush=True)

if __name__ == "__main__":
    websocket.WebSocketApp(URL, on_open=on_open, on_message=on_message,
                           on_error=on_error, on_close=on_close).run_forever()
