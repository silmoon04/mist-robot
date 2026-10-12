"""Isolated launcher regressions; never start MIST services or open serial."""
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from locomotion.hardware.bridge import Bridge
from locomotion.scripts import remote_session as session


@unittest.skipUnless(sys.platform == "linux", "Session ownership uses Linux /proc and pidfd")
class RemoteSessionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="mist-session-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        self.record_path = self.runtime / "session.json"
        for name, value in (("RUNTIME", self.runtime), ("RECORD", self.record_path)):
            replacement = patch.object(session, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)

    def spawn_unrelated(self):
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

        def cleanup():
            if child.poll() is None:
                child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)

        self.addCleanup(cleanup)
        return child

    def assert_stop_does_not_signal(self, record):
        self.record_path.write_text(json.dumps(record), encoding="utf-8")
        with patch.object(session.os, "pidfd_open") as pidfd, \
                patch.object(session.signal, "pidfd_send_signal") as send, \
                patch.object(session.os, "kill") as kill, \
                redirect_stdout(io.StringIO()) as output:
            session.stop()
        pidfd.assert_not_called()
        send.assert_not_called()
        kill.assert_not_called()
        self.assertIn("No managed session", output.getvalue())

    def test_malformed_records_never_signal(self):
        for pid in (None, {}, [], "not-a-pid"):
            with self.subTest(pid=pid):
                record = {"pid": pid, "start_ticks": "123", "owned_services": []}
                self.assertIsNone(session.process_identity(pid))
                self.assertFalse(session.owned_session(record))
                self.assert_stop_does_not_signal(record)
        for content in ("{incomplete", "[]", "null"):
            with self.subTest(content=content):
                self.record_path.write_text(content, encoding="utf-8")
                self.assertIsNone(session.read_record())
                with patch.object(session.os, "pidfd_open") as pidfd, \
                        redirect_stdout(io.StringIO()):
                    session.stop()
                pidfd.assert_not_called()

    def test_stale_record_cannot_stop_unrelated_live_process(self):
        child = self.spawn_unrelated()
        ticks = (Path("/proc") / str(child.pid) / "stat").read_text().rsplit(") ", 1)[1].split()[19]
        # Even a matching real start time cannot substitute for script identity.
        for recorded_ticks in (ticks, "stale-start-time"):
            with self.subTest(start_ticks=recorded_ticks):
                self.assert_stop_does_not_signal(
                    {"pid": child.pid, "start_ticks": recorded_ticks, "owned_services": []}
                )
                self.assertIsNone(child.poll())

    def test_current_process_is_not_a_session_supervisor(self):
        ticks = (Path("/proc") / str(os.getpid()) / "stat").read_text().rsplit(") ", 1)[1].split()[19]
        self.assertIsNone(session.process_identity(os.getpid()))
        self.assertFalse(session.owned_session({"pid": os.getpid(), "start_ticks": ticks}))

    def test_health_accepts_real_dry_run_status_and_rejects_hardware_status(self):
        bridge = Bridge()
        bridge.close()
        payload = {"value": bridge.status()}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                if self.path != "/api/status":
                    self.send_error(404)
                    return
                body = json.dumps(payload["value"]).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            services = {"joints": (server.server_port, "/api/status", [])}
            with patch.object(session, "SERVICES", services):
                dry_run = session.health("joints")
                self.assertTrue(dry_run["ready"])
                self.assertEqual(dry_run["mode"], "dry-run")
                # Use the actual status producer with an inert link object;
                # no hardware constructor, worker or serial request runs.
                with patch.object(bridge, "link", SimpleNamespace(telemetry={}, imu_packet={})):
                    payload["value"] = bridge.status()
                hardware = session.health("joints")
                self.assertFalse(hardware["ready"])
                self.assertEqual(hardware["mode"], "hardware commissioning")
                self.assertIn("non-dry-run", hardware["error"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

    def test_second_child_failure_cleans_owned_children_and_preserves_external_process(self):
        external = self.spawn_unrelated()
        state = self.root / "locomotion" / "handoff" / "MSI_STATE.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({"frozen_sources": {}}), encoding="utf-8")
        services = {
            "simulation": (0, "/unused", ["-c", "import time; time.sleep(60)"]),
            "joints": (0, "/unused", ["-c", "import sys; print('fixture child failure', file=sys.stderr, flush=True); sys.exit(7)"]),
        }
        real_popen = subprocess.Popen
        children = []
        log_handles = []

        def spawn(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            log_handles.append(kwargs["stdout"])
            return child

        previous_handlers = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
        previous_path = sys.path.copy()
        try:
            with patch.object(session, "REPO", self.root), \
                    patch.object(session, "SERVICES", services), \
                    patch.object(session, "process_identity", return_value="isolated-supervisor"), \
                    patch.object(session, "health", return_value={"ready": False, "error": "fixture absent"}), \
                    patch.object(session.subprocess, "Popen", side_effect=spawn), \
                    patch("locomotion.provenance.check_sources") as sources, \
                    redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, "Remote exited: joints"):
                    session.run_locked()
            sources.assert_called_once_with({})
            self.assertEqual(len(children), 2)
            self.assertIsNotNone(children[0].poll())
            self.assertEqual(children[1].poll(), 7)
            self.assertIsNone(external.poll())
            self.assertFalse(self.record_path.exists())
            self.assertIn("fixture child failure", (self.runtime / "joints.log").read_text())
            self.assertTrue(all(handle.closed for handle in log_handles))
        finally:
            for number, handler in previous_handlers.items():
                signal.signal(number, handler)
            sys.path[:] = previous_path
            for child in children:
                if child.poll() is None:
                    child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
        for number, handler in previous_handlers.items():
            self.assertEqual(signal.getsignal(number), handler)


if __name__ == "__main__":
    unittest.main()
