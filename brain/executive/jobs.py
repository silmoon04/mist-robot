"""Background text jobs shared by the web console and robot ticket tool."""
from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from executive import worker

TERMINAL = {"completed", "failed", "cancelled"}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class JobManager:
    def __init__(self, run_dir: Path, runner, broadcast, max_running=2):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.runner = runner
        self.broadcast = broadcast
        self.max_running = max_running
        self.lock = threading.RLock()
        self.stopped = threading.Event()
        self.jobs = {}
        self.running = {}
        self.thread = None
        self.owns_worker = False
        try:
            saved = json.loads((self.run_dir / "jobs.json").read_text(encoding="utf-8"))
            self.jobs = {j["id"]: j for j in saved if isinstance(j, dict) and j.get("id")}
        except (OSError, ValueError, TypeError):
            pass
        # The inbox is the delivery record if a process exited before saving jobs.
        for entry in self._inbox():
            tid = entry.get("ticket_id")
            if tid:
                self.jobs[tid] = {**self.jobs.get(tid, {}), **entry, "id": tid,
                                  "status": entry.get("status", "failed" if entry.get("kind") == "error" else "completed")}
        recovered = False
        for job in self.jobs.values():
            if job.get("status") == "running":
                job.update(status="failed", completed_at=timestamp(), kind="error",
                           result="Interrupted by a server restart. Submit again to retry.",
                           grounding="unavailable", sources=[], untrusted=True)
                worker.append_inbox(self.run_dir, {**job, "ticket_id": job["id"], "ts": timestamp()})
                recovered = True
        if recovered:
            self._save()

    def _inbox(self):
        try:
            lines = (self.run_dir / "inbox.jsonl").read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        result = []
        for line in lines:
            try:
                entry = json.loads(line)
                if isinstance(entry, dict):
                    result.append(entry)
            except ValueError:
                continue
        return result

    def _save(self):
        temp = self.run_dir / "jobs.json.tmp"
        temp.write_text(json.dumps(list(self.jobs.values()), ensure_ascii=False), encoding="utf-8")
        temp.replace(self.run_dir / "jobs.json")

    def _emit(self, job):
        self._save()
        self.broadcast({"type": "job", "job": dict(job)})

    def snapshot(self):
        with self.lock:
            return [dict(j) for j in self.jobs.values()][-100:]

    def submit(self, task):
        if not isinstance(task, str) or not task.strip() or len(task) > 4000:
            raise ValueError("Enter a task of 1 to 4000 characters.")
        with self.lock:
            if self.stopped.is_set():
                raise ValueError("The background worker is shutting down.")
            if sum(j["status"] not in TERMINAL for j in self.jobs.values()) >= 20:
                raise ValueError("The background queue is full.")
            job = {"id": "J" + uuid.uuid4().hex[:12], "task": task.strip(),
                   "created_wall": timestamp(), "status": "queued"}
            with (self.run_dir / "tickets.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(job) + "\n")
            self.jobs[job["id"]] = job
            self._emit(job)
            return dict(job)

    def cancel(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            if job["status"] in TERMINAL:
                return dict(job)
            if job_id in self.running:
                self.running[job_id].set()
            job.update(status="cancelled", completed_at=timestamp(), result="Task cancelled.",
                       kind="cancelled", grounding="unavailable", sources=[], untrusted=True)
            worker.append_inbox(self.run_dir, {**job, "ticket_id": job_id, "ts": timestamp()})
            self._emit(job)
            return dict(job)

    def tick(self):
        with self.lock:
            if self.stopped.is_set():
                return
            worker.touch_alive(self.run_dir)
            for ticket in worker.read_tickets(self.run_dir):
                if ticket["id"] not in self.jobs:
                    job = {**ticket, "status": "queued"}
                    self.jobs[ticket["id"]] = job
                    self._emit(job)
            for job in list(self.jobs.values()):
                if len(self.running) >= self.max_running:
                    break
                if job["status"] != "queued":
                    continue
                cancel = threading.Event()
                self.running[job["id"]] = cancel
                job.update(status="running", started_at=timestamp())
                self._emit(job)
                threading.Thread(target=self._run, args=(dict(job), cancel), daemon=True).start()

    def _run(self, submitted, cancel):
        started = time.monotonic()
        try:
            answer = self.runner(submitted, cancel)
        except Exception as exc:
            answer = worker.pipeline_result(f"Background task failed ({type(exc).__name__}).",
                                            "error", "unavailable")
        with self.lock:
            job = self.jobs[submitted["id"]]
            self.running.pop(job["id"], None)
            if cancel.is_set() or job["status"] == "cancelled":
                return
            job.update(answer, status="failed" if answer.get("kind") == "error" else "completed",
                       completed_at=timestamp(), elapsed_s=round(time.monotonic() - started, 3),
                       untrusted=True)
            worker.append_inbox(self.run_dir, {**job, "ticket_id": job["id"], "ts": timestamp()})
            self._emit(job)

    def start(self):
        alive = self.run_dir / "worker.alive"
        if alive.exists() and time.time() - alive.stat().st_mtime < worker.ALIVE_FRESH_S:
            raise RuntimeError("Another executive worker owns this run directory.")
        self.owns_worker = True
        self.tick()
        def loop():
            while not self.stopped.wait(0.25):
                self.tick()
        self.thread = threading.Thread(target=loop, name="background-jobs", daemon=True)
        self.thread.start()

    def close(self):
        self.stopped.set()
        with self.lock:
            for job_id in list(self.running):
                self.cancel(job_id)
        if self.thread:
            self.thread.join(timeout=2)
        if self.owns_worker:
            (self.run_dir / "worker.alive").unlink(missing_ok=True)
            self.owns_worker = False


def make_runner(backend, model, thinking="low", service_tier="fast", mock=False):
    def run(ticket, cancel):
        client = None
        monitor_done = threading.Event()
        usage = {}

        def generate(prompt, requested_model, instruction=worker.EXECUTIVE_INSTRUCTION):
            nonlocal client
            if cancel.is_set():
                raise RuntimeError("cancelled")
            if backend != "codex":
                return worker.gemini_generate(prompt, requested_model, instruction=instruction)
            from codex_client import CodexClient
            # The research model gets text only, without robot or shell tools.
            client = CodexClient(model=model, thinking=thinking, service_tier=service_tier,
                                 with_memory=False, tools=[], system_prompt=instruction)
            def monitor():
                while not monitor_done.wait(0.05):
                    if cancel.is_set():
                        client.cancel_current_turn()
            threading.Thread(target=monitor, daemon=True).start()
            if cancel.is_set():
                raise RuntimeError("cancelled")
            result = client.ask(prompt, timeout=90)
            usage.update(input_tokens=result.input_tokens, output_tokens=result.output_tokens,
                         total_s=result.total_s, backend=client.backend_info,
                         cost_usd=None, cost_note="The subscription backend does not report per-turn cost.")
            if result.errors:
                raise RuntimeError("model turn failed")
            return result.text
        try:
            if mock:
                answer = worker.pipeline_result(worker.mock_pipeline(ticket["task"]), "mock", "mock")
            elif worker.classify(ticket["task"]) == "research":
                answer = worker.research_pipeline(ticket["task"], model, generate=generate,
                                                  cancelled=cancel.is_set)
            else:
                answer = worker.general_pipeline(ticket["task"], model, generate=generate)
            return {**answer, "model": None if mock else model, "usage": usage}
        finally:
            monitor_done.set()
            if client:
                client.close()
    return run
