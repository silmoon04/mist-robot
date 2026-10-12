"""Exercise the HTTP console and concurrent executive lifecycle without network APIs."""
from pathlib import Path
import json
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui import server
from executive.jobs import JobManager


def main():
    with tempfile.TemporaryDirectory(prefix="mist-ui-") as tmp:
        args = server.parse_args(["--stub", "--no-executive", "--run-dir", tmp])
        app = server.build_app(args, use_stub=True)
        server.start_background(app)
        started = threading.Event()
        finish = threading.Event()
        def delayed(ticket, cancel):
            started.set()
            finish.wait(3)
            return {"result": "Fixture complete", "kind": "mock", "grounding": "mock", "sources": []}
        app.jobs = JobManager(Path(tmp), delayed, app.broadcast, max_running=1)
        app.jobs.start()
        httpd = server.make_server(app, 0)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        def request(path, body=None):
            req = urllib.request.Request(base+path, data=json.dumps(body).encode() if body is not None else None,
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=3) as response:
                    return response.status, json.load(response)
            except urllib.error.HTTPError as error:
                return error.code, json.load(error)
        try:
            status, result = request("/api/jobs", {"task": "Write a tiny fixture"})
            assert status == 202, result
            job_id = result["job"]["id"]
            assert started.wait(2), "Background job did not start"
            t0 = time.monotonic()
            status, reply = request("/api/say", {"text": "Can we chat while you work?"})
            assert status == 202 and time.monotonic()-t0 < .5, reply
            deadline = time.monotonic()+2
            while app.busy and time.monotonic() < deadline:
                time.sleep(.01)
            assert not app.busy and not finish.is_set(), "Chat waited on executive"
            status, cancelled = request("/api/jobs/cancel", {"id": job_id})
            assert status == 200 and cancelled["job"]["status"] == "cancelled"
            finish.set()
            deadline = time.monotonic()+2
            while app.jobs.running and time.monotonic() < deadline:
                time.sleep(.01)
            assert app.jobs.snapshot()[0]["status"] == "cancelled", "Late result overwrote cancellation"
            inbox = [json.loads(line) for line in (Path(tmp)/"inbox.jsonl").read_text().splitlines()]
            assert len(inbox) == 1 and inbox[0]["kind"] == "cancelled"
            status, result = request("/api/jobs", {"task": "Write another fixture"})
            assert status == 202
            deadline = time.monotonic()+2
            while time.monotonic()<deadline:
                jobs = request("/api/jobs")[1]["jobs"]
                if jobs[-1]["status"]=="completed": break
                time.sleep(.02)
            assert jobs[-1]["status"] == "completed" and jobs[-1]["grounding"] == "mock"
            assert request("/api/jobs", {"task": []})[0] == 400
            assert request("/api/jobs/cancel", {"id": {}})[0] == 400
            assert request("/api/say", {"text": []})[0] == 400
            assert request("/api/speech", {"text": [], "provider": "elevenlabs", "client_protocol": 2,
                                          "request_id": "invalid-text-fixture", "purpose": "manual"})[0] == 400
            status, config = request("/api/config")
            assert status == 200 and config["hardware_connected"] is False
            assert config["stub"] and len(config["jobs"]) == 2
            recovered = JobManager(Path(tmp), delayed, lambda event: None)
            assert len(recovered.snapshot()) == 2
            assert recovered.snapshot()[-1]["status"] == "completed"
            history_before=list(app.history)
            status, changed=request("/api/profile", {"profile":"astra"})
            assert status==200 and changed["profile"]=="astra"
            assert app.args.model=="gpt-6-astra" and app.history==history_before
            status, changed=request("/api/profile", {"profile":"responsive"})
            assert status==200 and app.args.model=="gpt-5.3-codex-spark"
            assert app.args.service_tier=="default" and app.args.executive_model=="gpt-6-astra"
            assert app.args.executive_service_tier=="fast"
            assert request("/api/profile", {"profile":"unknown"})[0]==400
            original_ask = app.client.ask
            def metadata_ask(*a, **kw):
                kw["on_event"]({"type": "backend_timing", "phase": "turn_accepted", "timings": {"client_lock_wait_s": .001}})
                answer = original_ask(*a, **kw)
                kw["on_event"]({"type": "face_expression", "expression": "happy", "source": "assistant_metadata"})
                answer.timings = {"client_lock_wait_s": .001}
                return answer
            app.client.ask = metadata_ask
            assert request("/api/say", {"text": "Show a UI-only expression", "request_id": "timing-fixture"})[0] == 202
            deadline = time.monotonic()+2
            while app.busy and time.monotonic()<deadline:
                time.sleep(.01)
            metric = json.loads((Path(tmp)/"turn_metrics.jsonl").read_text().splitlines()[-1])
            assert metric["server_timing"]["request_id"] == "timing-fixture"
            assert metric["server_timing"]["queue_wait_s"] >= 0
            assert metric["backend_timings"]["client_lock_wait_s"] == .001
            assert request("/api/config")[1]["display_face"] == "happy"
            assert json.loads((Path(tmp)/"robot_state.json").read_text())["face"] == "neutral", "Display metadata must not mutate robot state"
            app.client.ask = original_ask
            # Stop before the scheduled chat worker has reached client.ask().
            gate = threading.Event()
            calls = []
            original_run, original_ask = app._run_turn, app.client.ask
            app._run_turn = lambda text, cancel: (gate.wait(2), original_run(text, cancel))
            def counted(*a, **kw):
                calls.append(True)
                return original_ask(*a, **kw)
            app.client.ask = counted
            assert request("/api/say", {"text": "This must stop before the model starts"})[0] == 202
            assert request("/api/interrupt", {})[1]["interrupted"]
            gate.set()
            deadline = time.monotonic()+2
            while app.busy and time.monotonic()<deadline:
                time.sleep(.01)
            assert not calls and not app.busy, "Immediate stop was lost before ask"
        finally:
            app._stop_background = True
            app.jobs.close()
            httpd.shutdown(); httpd.server_close()
    with tempfile.TemporaryDirectory(prefix="mist-restart-") as tmp:
        path = Path(tmp)
        (path/"jobs.json").write_text(json.dumps([
            {"id": "interrupted", "task": "Test restart", "status": "running"}]))
        recovered = JobManager(path, lambda *a: {}, lambda event: None)
        assert recovered.snapshot()[0]["status"] == "failed"
        inbox = path/"inbox.jsonl"
        entries = [json.loads(line) for line in inbox.read_text().splitlines()]
        assert len(entries) == 1 and entries[0]["ticket_id"] == "interrupted"
        assert entries[0]["kind"] == "error", "Restart failure must reach check_inbox"
        JobManager(path, lambda *a: {}, lambda event: None)
        assert len(inbox.read_text().splitlines()) == 1, "Restart error delivered twice"
        recovered.submit("Queued during shutdown test")
        recovered.close()
        recovered.tick()
        assert not recovered.running, "tick started new work after close"
        try:
            recovered.submit("Must reject closed worker")
            raise AssertionError("Closed worker accepted work")
        except ValueError:
            pass
    print("PASS: HTTP background queue, chat concurrency, cancellation, late-result suppression, completion, restart and malformed requests.")

if __name__ == "__main__":
    main()
