"""Console ownership tests using ephemeral loopback sockets and offline clients."""
import contextlib
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
from unittest import mock
import urllib.request
import uuid

from websockets.exceptions import ConnectionClosed, InvalidStatus
from websockets.sync.client import connect

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui import server, stt_proxy


class FakeEngine:
    def __init__(self):
        self.begin_count = self.close_count = self.cancel_count = 0
        self.pcm = []
        self.on_event = None

    def begin_utterance(self, sample_rate, *, on_event=None):
        self.begin_count += 1
        self.sample_rate = sample_rate
        self.on_event = on_event
        return str(uuid.uuid4())

    def send_pcm(self, pcm):
        self.pcm.append(pcm)
        self.on_event({"type": "stt_partial", "text": "Fixture words"})

    def finalize(self, timeout=8):
        seconds = sum(map(len, self.pcm)) / (2 * self.sample_rate)
        return {"final": True, "transcript": "Fixture words", "confidence": 1,
                "audio_seconds": seconds, "provider_processed_audio_seconds": seconds,
                "timings": {"recognition_total_s": 0}}

    def cancel(self):
        self.cancel_count += 1

    def close(self):
        self.close_count += 1


class ServiceLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mist-service-lifecycle-")
        self.addCleanup(self.temp.cleanup)
        self.apps = []
        self.closed_clients = []
        self.engines = []
        self.proxies = []
        self.enterContext(mock.patch.object(server, "load_env", return_value={}))
        self.enterContext(mock.patch.dict(os.environ, {
            "DEEPGRAM_API_KEY": "", "ELEVENLABS_API_KEY": ""}))
        self.enterContext(mock.patch.object(
            stt_proxy, "WarmDeepgramSTT", side_effect=AssertionError("Provider engine forbidden in lifecycle tests")))

    def options(self, *extra, executive=False):
        argv = ["--port", "0", "--stt-port", "0", "--run-dir", self.temp.name]
        if not executive:
            argv.append("--no-executive")
        return server.parse_args(argv + list(extra))

    def app_factory(self, args):
        app = server.build_app(args, use_stub=True)
        self.apps.append(app)
        if app.client is not None:
            original_close = app.client.close

            def close():
                self.closed_clients.append(app.client)
                original_close()

            app.client.close = close
        return app

    def engine_factory(self):
        engine = FakeEngine()
        self.engines.append(engine)
        return engine

    def proxy_factory(self, **kwargs):
        proxy = stt_proxy.create_proxy_server(**kwargs)
        self.proxies.append(proxy)
        return proxy

    def runtime(self, args=None, **factories):
        settings = {"app_factory": self.app_factory, "proxy_engine_factory": self.engine_factory,
                    "proxy_factory": self.proxy_factory}
        settings.update(factories)
        runtime = server.ConsoleRuntime(args or self.options(), **settings)
        self.addCleanup(runtime.close)
        return runtime

    def listener(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(listener.close)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(2)
        return listener

    def assert_port_free(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))

    def assert_port_reserved(self, port):
        with self.assertRaises(OSError):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", port))

    def assert_foreign_listener_healthy(self, listener):
        with socket.create_connection(listener.getsockname(), timeout=2) as client:
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(2)
                client.sendall(b"foreign-owner")
                self.assertEqual(connection.recv(32), b"foreign-owner")
                connection.sendall(b"still-running")
                self.assertEqual(client.recv(32), b"still-running")

    def config(self, runtime):
        url = f"http://127.0.0.1:{runtime.httpd.server_port}/api/config"
        with urllib.request.urlopen(url, timeout=2) as response:
            self.assertEqual(response.status, 200)
            return json.load(response)

    def browser(self, runtime, *, origin=None):
        origin = origin or f"http://127.0.0.1:{runtime.httpd.server_port}"
        browser = connect(runtime.app.config()["stt_proxy_url"], origin=origin,
                          compression=None, open_timeout=2, close_timeout=0.2)
        self.addCleanup(browser.close)
        return browser

    def begin(self, browser):
        utterance_id = str(uuid.uuid4())
        browser.send(json.dumps({"type": "start", "utterance_id": utterance_id, "sample_rate": 16000}))
        started = json.loads(browser.recv(timeout=2))
        self.assertEqual(started["type"], "started")
        self.assertEqual(started["utterance_id"], utterance_id)
        return utterance_id

    def test_cli_defaults_and_explicit_stub_managed_mode(self):
        args = server.parse_args([])
        self.assertEqual((args.port, args.stt_port, args.stt_mode), (8776, 8788, "managed"))
        self.assertEqual(server.parse_args(["--stub"]).stt_mode, "off")
        self.assertEqual(server.parse_args(["--watch", self.temp.name]).stt_mode, "off")
        runtime = self.runtime(self.options("--stub", "--stt-mode", "managed")).start()
        self.assertEqual(self.config(runtime)["stt_mode"], "managed")
        self.assertIsNotNone(runtime.proxy)
        self.assertEqual(self.engines, [])

    def test_normal_cli_handles_interrupt_with_owned_cleanup(self):
        runtimes = []
        original = server.ConsoleRuntime

        class ReadyThenInterrupted(original):
            def start(runtime):
                result = super().start()
                runtimes.append(runtime)
                return result

            def wait(runtime):
                raise KeyboardInterrupt

        with mock.patch.object(server, "ConsoleRuntime", ReadyThenInterrupted), contextlib.redirect_stdout(io.StringIO()) as output:
            result = server.main(["--stub", "--no-executive", "--stt-mode", "managed", "--port", "0", "--stt-port", "0", "--run-dir", self.temp.name])
        self.assertEqual(result, 0)
        self.assertIn("speech recognition: managed", output.getvalue())
        self.assertIn("shutting down", output.getvalue())
        self.assertEqual(len(runtimes), 1)
        runtime = runtimes[0]
        self.assertFalse(runtime.http_thread.is_alive())
        self.assertFalse(runtime.proxy_thread.is_alive())
        self.assert_port_free(runtime.httpd.server_port)
        self.assert_port_free(runtime.proxy.port)
        self.assertEqual(runtime.close_errors, [])

    def test_invalid_external_or_shared_ports_fail_during_parse(self):
        for arguments in (["--stt-mode", "external", "--stt-port", "0"],
                          ["--port", "41000", "--stt-port", "41000"],
                          ["--port", "-1"], ["--stt-port", "65536"]):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    server.parse_args(arguments)
                self.assertEqual(error.exception.code, 2)
        self.assertEqual(self.apps, [])

    def test_managed_reserves_both_ports_before_backend_and_creates_engine_lazily(self):
        def build_after_reservation(args):
            self.assertEqual(len(self.proxies), 1)
            self.assert_port_reserved(args.port)
            self.assert_port_reserved(self.proxies[0].port)
            self.assertEqual(self.engines, [])
            return self.app_factory(args)

        runtime = self.runtime(app_factory=build_after_reservation).start()
        config = self.config(runtime)
        self.assertEqual(config["stt_mode"], "managed")
        self.assertEqual(config["stt_proxy_url"], f"ws://127.0.0.1:{runtime.proxy.port}/stt")
        self.assertNotEqual(runtime.httpd.server_port, runtime.proxy.port)
        self.assertEqual(self.engines, [])
        browser = self.browser(runtime)
        utterance_id = self.begin(browser)
        self.assertEqual(len(self.engines), 1)
        browser.send(b"\0\0" * 20)
        self.assertEqual(json.loads(browser.recv(timeout=2))["type"], "partial")
        browser.send(json.dumps({"type": "end", "utterance_id": utterance_id}))
        final = json.loads(browser.recv(timeout=2))
        self.assertEqual((final["type"], final["transcript"]), ("final", "Fixture words"))
        self.assertEqual(self.engines[0].begin_count, 1)

    def test_wrong_origin_is_rejected_before_engine_creation(self):
        runtime = self.runtime().start()
        wrong_port = 1 if runtime.httpd.server_port != 1 else 2
        for origin in (f"http://127.0.0.1:{wrong_port}", f"http://localhost:{wrong_port}", None):
            with self.subTest(origin=origin), self.assertRaises(InvalidStatus):
                with connect(runtime.app.config()["stt_proxy_url"], origin=origin,
                             compression=None, open_timeout=2, close_timeout=0.2):
                    pass
        self.assertEqual(self.engines, [])

    def test_actual_localhost_origin_is_accepted(self):
        runtime = self.runtime().start()
        browser = self.browser(runtime, origin=f"http://localhost:{runtime.httpd.server_port}")
        self.begin(browser)
        self.assertEqual(len(self.engines), 1)

    def test_second_browser_does_not_create_another_engine(self):
        runtime = self.runtime().start()
        browser = self.browser(runtime)
        self.begin(browser)
        with self.assertRaises(InvalidStatus):
            self.browser(runtime)
        self.assertEqual(len(self.engines), 1)
        self.assertEqual(self.engines[0].close_count, 0)

    def test_close_releases_active_speech_jobs_heartbeat_backend_and_listeners(self):
        runtime = self.runtime(self.options(executive=True)).start()
        browser = self.browser(runtime)
        self.begin(browser)
        jobs = runtime.app.jobs
        started, cancelled = threading.Event(), threading.Event()

        def pending_job(ticket, cancel):
            started.set()
            if cancel.wait(3):
                cancelled.set()
            return {"result": "Fixture finished", "kind": "mock", "grounding": "mock", "sources": []}

        jobs.runner = pending_job
        job = jobs.submit("Wait for the owned runtime to close")
        jobs.tick()
        self.assertTrue(started.wait(2))
        heartbeat = Path(self.temp.name) / "worker.alive"
        self.assertTrue(heartbeat.exists())
        ports = runtime.httpd.server_port, runtime.proxy.port
        threads = runtime.http_thread, runtime.proxy_thread, runtime.background_thread, jobs.thread
        runtime.close()
        runtime.close()
        self.assertTrue(cancelled.wait(2))
        self.assertEqual(jobs.jobs[job["id"]]["status"], "cancelled")
        self.assertTrue(jobs.stopped.is_set())
        self.assertFalse(heartbeat.exists())
        self.assertEqual(self.closed_clients, [runtime.app.client])
        self.assertEqual(self.engines[0].close_count, 1)
        self.assertGreater(self.engines[0].cancel_count, 0)
        for thread in threads:
            self.assertFalse(thread.is_alive(), thread.name)
        with self.assertRaises(ConnectionClosed):
            browser.recv(timeout=2)
        for port in ports:
            self.assert_port_free(port)
        self.assertEqual(runtime.close_errors, [])

    def test_start_and_close_are_idempotent(self):
        runtime = self.runtime()
        self.assertIs(runtime.start(), runtime)
        resources = runtime.httpd, runtime.proxy, runtime.http_thread, runtime.proxy_thread
        self.assertIs(runtime.start(), runtime)
        self.assertEqual(resources, (runtime.httpd, runtime.proxy, runtime.http_thread, runtime.proxy_thread))
        self.assertEqual(len(self.apps), 1)
        self.assertEqual(len(self.proxies), 1)
        runtime.close()
        runtime.close()
        self.assertEqual(len(self.closed_clients), 1)

    def test_close_ends_an_existing_browser_event_stream(self):
        runtime = self.runtime(self.options("--stt-mode", "off")).start()
        url = f"http://127.0.0.1:{runtime.httpd.server_port}/api/events"
        with urllib.request.urlopen(url, timeout=2) as stream:
            hello = stream.readline()
            self.assertTrue(hello.startswith(b"data: "))
            self.assertEqual(json.loads(hello[6:])["type"], "hello")
            self.assertEqual(stream.readline(), b"\n")
            runtime.close()
            self.assertEqual(stream.read(), b"")
        self.assertEqual(runtime.app.bus._clients, [])

    def test_close_cannot_publish_a_speech_engine_still_being_created(self):
        entered, release, closed = threading.Event(), threading.Event(), threading.Event()
        engine = FakeEngine()
        original_close = engine.close

        def finish_engine():
            original_close()
            closed.set()

        engine.close = finish_engine

        def delayed_engine():
            entered.set()
            if not release.wait(3):
                raise RuntimeError("Fixture engine startup was not released")
            return engine

        runtime = self.runtime(proxy_engine_factory=delayed_engine).start()
        browser = self.browser(runtime)
        self.assertTrue(entered.wait(2))
        try:
            runtime.close()
            release.set()
            self.assertTrue(closed.wait(2), "Shutdown missed an engine created after it closed")
            with self.assertRaises(ConnectionClosed):
                self.begin(browser)
            self.assertEqual(engine.begin_count, 0)
            self.assertEqual(engine.close_count, 1)
            self.assertIsNone(runtime.proxy.session)
        finally:
            release.set()
            runtime.proxy.shutdown()

    def test_close_before_start_allocates_nothing(self):
        runtime = self.runtime()
        runtime.close()
        runtime.close()
        self.assertEqual((runtime.app, runtime.httpd, runtime.proxy), (None, None, None))
        self.assertEqual(self.apps, [])

    def test_occupied_http_port_fails_without_backend_or_foreign_listener_changes(self):
        foreign = self.listener()
        runtime = self.runtime(self.options("--port", str(foreign.getsockname()[1])))
        with self.assertRaises(OSError):
            runtime.start()
        self.assertEqual(self.apps, [])
        self.assertEqual(self.proxies, [])
        self.assertEqual(self.engines, [])
        self.assert_foreign_listener_healthy(foreign)

    def test_second_runtime_cannot_share_the_owned_http_port(self):
        first = self.runtime(self.options("--stt-mode", "off")).start()
        second = self.runtime(self.options("--stt-mode", "off", "--port", str(first.httpd.server_port)))
        with self.assertRaises(OSError):
            second.start()
        self.assertEqual(len(self.apps), 1)
        self.assertEqual(self.config(first)["stt_mode"], "off")

    def test_occupied_proxy_port_releases_http_without_backend_or_foreign_listener_changes(self):
        foreign = self.listener()
        runtime = self.runtime(self.options("--stt-port", str(foreign.getsockname()[1])))
        with self.assertRaises(OSError):
            runtime.start()
        self.assertEqual(self.apps, [])
        self.assertEqual(self.engines, [])
        self.assert_port_free(runtime.args.port)
        self.assert_foreign_listener_healthy(foreign)

    def test_second_runtime_cannot_share_the_owned_proxy_port(self):
        first = self.runtime().start()
        second = self.runtime(self.options("--stt-port", str(first.proxy.port)))
        with self.assertRaises(OSError):
            second.start()
        self.assertEqual(len(self.apps), 1)
        self.assert_port_free(second.args.port)
        self.begin(self.browser(first))
        self.assertEqual(len(self.engines), 1)

    def test_missing_proxy_dependency_releases_http_before_backend_startup(self):
        original_import = __import__

        def without_proxy_dependency(name, *args, **kwargs):
            if name == "ui.stt_proxy":
                raise ModuleNotFoundError("Fixture missing speech dependency")
            return original_import(name, *args, **kwargs)

        runtime = self.runtime(proxy_factory=None)
        with mock.patch("builtins.__import__", side_effect=without_proxy_dependency):
            with self.assertRaisesRegex(ImportError, "Fixture missing speech dependency"):
                runtime.start()
        self.assertEqual(self.apps, [])
        self.assertEqual(self.engines, [])
        self.assert_port_free(runtime.args.port)

    def test_backend_startup_failure_releases_both_unserved_sockets(self):
        def failed_backend(args):
            self.assert_port_reserved(args.port)
            self.assert_port_reserved(self.proxies[0].port)
            raise RuntimeError("Fixture backend failed")

        runtime = self.runtime(app_factory=failed_backend)
        with self.assertRaisesRegex(RuntimeError, "Fixture backend failed"):
            runtime.start()
        self.assertEqual(self.engines, [])
        self.assert_port_free(runtime.args.port)
        self.assert_port_free(self.proxies[0].port)
        self.assertEqual(runtime.close_errors, [])

    def test_foreign_job_heartbeat_survives_failed_startup(self):
        heartbeat = Path(self.temp.name) / "worker.alive"
        heartbeat.write_text("foreign-worker", encoding="utf-8")
        runtime = self.runtime(self.options(executive=True))
        with self.assertRaisesRegex(RuntimeError, "Another executive worker"):
            runtime.start()
        self.assertEqual(heartbeat.read_text(encoding="utf-8"), "foreign-worker")
        self.assertIsNone(runtime.app)
        self.assertEqual(self.apps, [])
        self.assertEqual(self.closed_clients, [])
        self.assert_port_free(runtime.args.port)
        self.assert_port_free(self.proxies[0].port)
        self.assertEqual(runtime.close_errors, [])

    def test_external_and_off_never_own_or_stop_foreign_proxy(self):
        foreign = self.listener()
        port = foreign.getsockname()[1]
        for mode in ("external", "off"):
            with self.subTest(mode=mode):
                runtime = self.runtime(self.options("--stt-mode", mode, "--stt-port", str(port))).start()
                config = self.config(runtime)
                self.assertEqual(config["stt_mode"], mode)
                self.assertEqual(config["stt_proxy_url"], f"ws://127.0.0.1:{port}/stt" if mode == "external" else None)
                self.assertIsNone(runtime.proxy)
                self.assertIsNone(runtime.proxy_thread)
                runtime.close()
                self.assert_foreign_listener_healthy(foreign)
        self.assertEqual(self.proxies, [])
        self.assertEqual(self.engines, [])


if __name__ == "__main__":
    unittest.main()
