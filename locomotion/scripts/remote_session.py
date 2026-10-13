"""Run the two loopback remotes as a managed simulation-only session."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

REPO = Path(__file__).resolve().parents[2]
RUNTIME = REPO / "locomotion" / ".remote-session"
RECORD = RUNTIME / "session.json"
SERVICES = {
    "simulation": (8131, "/api/state", [str(REPO / "locomotion/sim_remote.py"), "--port", "8131"]),
    "joints": (8130, "/api/status", ["-m", "locomotion.hardware.bridge", "--port", "8130"]),
}


def process_identity(pid):
    """Bind a PID to this supervisor and its kernel start time."""
    try:
        proc = Path("/proc") / str(int(pid))
        fields = (proc / "stat").read_text().rsplit(") ", 1)[1].split()
        command = (proc / "cmdline").read_bytes().split(b"\0")
        if str(Path(__file__).resolve()).encode() not in command or b"run" not in command:
            return None
        return fields[19]
    except (OSError, ValueError, TypeError, IndexError):
        return None


def owned_session(record):
    return bool(record and process_identity(record.get("pid", -1)) == record.get("start_ticks")
                and record.get("start_ticks") is not None)


def read_record():
    try:
        value = json.loads(RECORD.read_text())
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def health(name):
    port, route, _ = SERVICES[name]
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{route}", timeout=1) as response:
            value = json.load(response)
        if name == "simulation":
            accepted = isinstance(value, dict) and {"controller", "info", "sensor", "image"} <= value.keys()
        else:
            accepted = isinstance(value, dict) and value.get("mode") == "dry-run" and len(value.get("q", [])) == 12
        return {"ready": accepted, "url": f"http://127.0.0.1:{port}/",
                "mode": value.get("mode", "simulation") if isinstance(value, dict) else None,
                "error": None if accepted else "Port is occupied by a different or non-dry-run service."}
    except (OSError, ValueError, TypeError, urllib.error.URLError) as error:
        return {"ready": False, "url": f"http://127.0.0.1:{port}/", "error": str(error)}


def status():
    record = read_record()
    return {"managed_session": owned_session(record), "services": {name: health(name) for name in SERVICES},
            "log_directory": str(RUNTIME), "hardware": "Robot under construction; session uses simulation and dry-run only."}


def run():
    if sys.platform != "linux":
        raise RuntimeError("Run this session inside WSL using Start MIST Remote.cmd.")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    import fcntl
    with (RUNTIME / "session.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                current = status()
                if current["managed_session"] and all(row["ready"] for row in current["services"].values()):
                    print(json.dumps(current, indent=2), flush=True)
                    return
                time.sleep(.25)
            raise RuntimeError("Existing session did not become ready. Inspect the remote logs.")
        run_locked()


def write_record(record):
    temporary = RUNTIME / f"session-{os.getpid()}.tmp"
    temporary.write_text(json.dumps(record, indent=2) + "\n")
    temporary.replace(RECORD)


def run_locked():
    prior = read_record()
    if owned_session(prior):
        print(json.dumps(status(), indent=2), flush=True)
        return
    record = {"pid": os.getpid(), "start_ticks": process_identity(os.getpid()), "owned_services": []}
    if record["start_ticks"] is None:
        raise RuntimeError("Could not bind the session to its process identity.")
    write_record(record)
    children, logs = {}, []
    closing = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: closing.set())
    signal.signal(signal.SIGINT, lambda *_: closing.set())
    try:
        sys.path.insert(0, str(REPO))
        from locomotion.provenance import check_sources
        expected = json.loads((REPO / "locomotion/handoff/MSI_STATE.json").read_text())["frozen_sources"]
        check_sources(expected)
        for name, (_, _, arguments) in SERVICES.items():
            current = health(name)
            if current["ready"]:
                continue  # An already running remote belongs to its original owner.
            if current.get("mode") is not None:
                raise RuntimeError(f"{name}: {current['error']}")
            log = (RUNTIME / f"{name}.log").open("ab")
            logs.append(log)
            children[name] = subprocess.Popen([sys.executable, *arguments], cwd=REPO,
                                              stdout=log, stderr=subprocess.STDOUT)
            record["owned_services"].append(name)
            write_record(record)
        deadline = time.monotonic() + 30
        while not closing.is_set():
            failures = [name for name, child in children.items() if child.poll() is not None]
            if failures:
                raise RuntimeError(f"Remote exited: {', '.join(failures)}. Read logs in {RUNTIME}.")
            if all(health(name)["ready"] for name in SERVICES):
                break
            if time.monotonic() > deadline:
                raise RuntimeError(f"Remotes did not become ready. Read logs in {RUNTIME}.")
            closing.wait(.25)
        print(json.dumps(status(), indent=2), flush=True)
        while not closing.wait(1):
            if any(child.poll() is not None for child in children.values()):
                raise RuntimeError(f"A managed remote exited. Read logs in {RUNTIME}.")
    finally:
        for child in children.values():
            if child.poll() is None:
                child.terminate()
        for child in children.values():
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        for log in logs:
            log.close()
        # A separate invocation may inspect the record, but only this PID owns it.
        if read_record() == record:
            RECORD.unlink(missing_ok=True)


def stop():
    record = read_record()
    if not owned_session(record):
        print("No managed session is running. Remotes started separately are left running.")
        return
    try:
        descriptor = os.pidfd_open(record["pid"])
    except ProcessLookupError:
        print("Managed session has already stopped.")
        return
    try:
        if not owned_session(record):
            print("Session identity changed; no process was stopped.")
            return
        signal.pidfd_send_signal(descriptor, signal.SIGTERM)
    finally:
        os.close(descriptor)
    deadline = time.monotonic() + 12
    while owned_session(record):
        if time.monotonic() > deadline:
            raise RuntimeError("Session shutdown did not finish; no unrelated process was stopped.")
        time.sleep(.1)
    print("Managed session stopped. Remotes started separately are left running.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "status", "stop"))
    args = parser.parse_args()
    if args.action == "status":
        print(json.dumps(status(), indent=2))
    elif args.action == "stop":
        stop()
    else:
        run()


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        print(f"MIST remote: {error}", file=sys.stderr)
        raise SystemExit(1)
