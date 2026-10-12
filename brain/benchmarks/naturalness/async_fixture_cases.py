"""Offline component evidence for production background-job delivery policy.

The production Conversation and BackgroundBrain execute unchanged. Only the
analyst's computation, websocket, audio mask, and native context transport are
controlled recorders. No model, microphone, TTS, or browser audio is exercised.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parents[1]
sys.path.insert(0, str(BRAIN))
sys.path.insert(0, str(BRAIN / "harness"))
from duplex.runtime import RobotRuntime
from duplex.server import Conversation

VERSION = "2026-09-24.async-component-2"
SCENARIOS = (
    "cancel_running_late_result", "replacement_waits_for_cleanup", "cancelled_job_reentry_after_replacement",
    "late_result_while_user_speaks", "changed_topic_revision", "duplicate_completion",
    "guard_playback", "guard_pending_audio", "guard_assistant_turn", "guard_native_delegation",
    "cancel_completed_before_delivery",
)


class Recorder:
    def __init__(self):
        self.start = time.perf_counter()
        self.events = []

    def record(self, name, **fields):
        event = {"name": name, "t_ms": (time.perf_counter() - self.start) * 1000,
                 "clock_id": "async_fixture_perf_counter", **deepcopy(fields)}
        self.events.append(event)
        return event


class SocketRecorder:
    closed = False

    def __init__(self, recorder):
        self.recorder = recorder

    async def send_json(self, event):
        self.recorder.record("production_websocket_emit", event=event)


class VoiceRecorder:
    def __init__(self, recorder):
        self.recorder = recorder
        self.turn = None
        self.contexts = []
        self.track = SimpleNamespace(append=lambda value: recorder.record("mic_packet_received", bytes=len(value)))

    async def context(self, text):
        # Preserve exactly what the production coordinator submitted. No spoken
        # output is inferred from this text or from successful method return.
        payload = json.loads(text[text.index("{"):])
        event = self.recorder.record("native_context_requested", payload=payload, text=text,
                                     native_transport="recording_double", audio_played=False)
        self.contexts.append(event)

    async def interrupt(self):
        self.recorder.record("native_interrupt_requested", native_transport="recording_double")

    async def close(self):
        pass


class MaskRecorder:
    def __init__(self, recorder):
        self.recorder = recorder
        self.pending = {}
        self.epoch = 0
        self.muted = False

    def diagnostic(self, name, **fields):
        self.recorder.record("production_diagnostic", diagnostic=name, **fields)

    async def interrupt(self):
        self.epoch += 1
        self.recorder.record("mask_interrupt_requested", epoch=self.epoch)

    async def close(self):
        pass


class ControlledAnalyst:
    """The supported BackgroundBrain.runner seam, with explicit release gates."""
    def __init__(self, recorder):
        self.recorder = recorder
        self.gates = {}
        self.results = {}

    async def __call__(self, job):
        gate = self.gates.setdefault(job["job_id"], asyncio.Event())
        self.recorder.record("controlled_analyst_waiting", job_id=job["job_id"], revision=job["revision"])
        while not gate.is_set():
            try:await gate.wait()
            except asyncio.CancelledError:
                self.recorder.record("controlled_analyst_ignored_cancellation", job_id=job["job_id"],
                                     explanation="A recording double simulates work that cannot be stopped remotely.")
        summary = self.results[job["job_id"]]
        self.recorder.record("controlled_analyst_returned", job_id=job["job_id"], revision=job["revision"],
                             status_before_return=job["status"], summary=summary)
        return summary, 0

    def release(self, job, summary):
        self.results[job["job_id"]] = summary
        self.recorder.record("fixture_released_analyst", job_id=job["job_id"], revision=job["revision"], summary=summary)
        self.gates.setdefault(job["job_id"], asyncio.Event()).set()


class Harness:
    def __init__(self):
        self.recorder = Recorder()
        self.temp = tempfile.TemporaryDirectory(prefix="mist-async-component-")
        self.c = Conversation({"runtime": RobotRuntime(Path(self.temp.name))}, SocketRecorder(self.recorder))
        self.c.voice = VoiceRecorder(self.recorder)
        self.c.mask = MaskRecorder(self.recorder)
        self.analyst = ControlledAnalyst(self.recorder)
        self.c.brain.runner = self.analyst
        self.checks = []
        self.conditions = []

    async def __aenter__(self):
        self.c.result_task = asyncio.create_task(self.c.deliver_results())
        return self

    async def __aexit__(self, *exc):
        # Release synthetic work before close joins it. No provider runs here.
        for job_id,task in list(self.c.brain.tasks.items()):
            if not task.done():self.analyst.release(self.c.brain.jobs[job_id], "Fixture teardown result, not for delivery.")
        await self.c.close()
        self.temp.cleanup()

    def check(self, name, passed, **evidence):
        row = {"name": name, "passed": bool(passed), **deepcopy(evidence)}
        self.checks.append(row)
        self.recorder.record("check", check=row)

    def condition(self, name, **value):
        row = {"name": name, **deepcopy(value)}
        self.conditions.append(row)
        self.recorder.record("fixture_condition", condition=row)

    async def user_start(self, text):
        turn_id = "controlled-user-" + str(self.c.user_revision+1)
        self.recorder.record("fixture_native_user_turn_created", turn_id=turn_id, text=text)
        await self.c.realtime_event({"type": "turn.created", "turn": {"id": turn_id, "role": "user", "transcript": text}})
        return turn_id

    async def user_end(self, turn_id, text):
        await self.c.realtime_event({"type": "turn.done", "turn": {"id": turn_id, "role": "user", "transcript": text}})
        self.recorder.record("fixture_native_user_turn_done", turn_id=turn_id, revision=self.c.user_revision)

    async def user_turn(self, text):
        turn = await self.user_start(text)
        await self.user_end(turn, text)

    async def start_job(self, question):
        begin = time.perf_counter()
        receipt = await self.c.brain.handle("start_background_task", {"question": question})
        self.recorder.record("start_job_receipt", receipt=receipt, duration_ms=(time.perf_counter()-begin)*1000,
                             revision=self.c.user_revision)
        return self.c.brain.jobs[receipt["job_id"]]

    async def cancel(self, job):
        await self.c.handle({"type": "cancel_background", "job_id": job["job_id"]})
        self.recorder.record("cancel_job_returned", job_id=job["job_id"], status=job["status"], revision=job["revision"])

    async def finish(self, job, summary):
        task = self.c.brain.tasks[job["job_id"]]
        self.analyst.release(job, summary)
        await asyncio.wait_for(asyncio.shield(task), 2)

    async def wait_for(self, predicate, timeout=2):
        deadline = time.perf_counter() + timeout
        while not predicate():
            if self.c.result_task.done():
                await self.c.result_task
                raise RuntimeError("Production delivery loop stopped early")
            if time.perf_counter() >= deadline:
                raise TimeoutError("Expected component event was not observed")
            await asyncio.sleep(.01)

    async def observe(self):
        # More than two actual .2-second production poll intervals. The policy
        # and its clock are never patched; timestamps remain measured wall time.
        await asyncio.sleep(.45)
        if self.c.result_task.done():
            await self.c.result_task
            raise RuntimeError("Production delivery loop stopped early")

    @property
    def delivered_ids(self):
        return [event["payload"]["job_id"] for event in self.c.voice.contexts]

    def result(self, case_id):
        completed_at = {}
        for event in self.recorder.events:
            payload = event.get("event", {})
            if event["name"] == "production_websocket_emit" and payload.get("type") == "brain_job" and payload.get("status") == "complete":
                completed_at.setdefault(payload["job_id"], event["t_ms"])
        delays = [{"job_id": e["payload"]["job_id"], "completion_to_context_ms": e["t_ms"]-completed_at[e["payload"]["job_id"]]}
                  for e in self.c.voice.contexts if e["payload"]["job_id"] in completed_at]
        return {"case_id": case_id, "evidence_scope": "production_component_with_controlled_transports",
                "fixture_version": VERSION, "passed": all(c["passed"] for c in self.checks),
                "checks": deepcopy(self.checks), "conditions": deepcopy(self.conditions),
                "events": deepcopy(self.recorder.events), "delivery_delays": delays,
                "jobs": [{k: deepcopy(v) for k, v in job.items() if k != "started_at"} for job in self.c.brain.jobs.values()],
                "contexts": deepcopy(self.c.voice.contexts), "final_user_revision": self.c.user_revision,
                "audio_e2e": False, "model_quality": "unmeasured", "audio_quality": "unmeasured"}


async def run_scenario(case_id):
    if case_id not in SCENARIOS:
        raise ValueError("Unknown component scenario")
    async with Harness() as h:
        c = h.c
        try:
            if case_id == "late_result_while_user_speaks":
                turn = await h.user_start("Compare cable routing while I finish explaining.")
                job = await h.start_job("Compare cable routing")
                h.condition("same_revision_user_speaking", revision=job["revision"])
                await h.finish(job, "Use the side channel after a manual cable-clearance check.")
                await h.observe()
                h.check("no_context_while_user_speaks", not h.delivered_ids)
                await h.user_end(turn, "That is the whole question.")
                await h.wait_for(lambda: len(h.delivered_ids) >= 1)
                h.check("one_context_after_same_user_turn_finishes", h.delivered_ids == [job["job_id"]])
            elif case_id in ("replacement_waits_for_cleanup", "cancelled_job_reentry_after_replacement"):
                await h.user_turn("Compare Friday cable-routing notes.")
                old = await h.start_job("Compare Friday cable-routing notes")
                await h.wait_for(lambda: old["job_id"] in h.analyst.gates)
                await h.user_turn("Correction: use Saturday instead of Friday.")
                await h.cancel(old)
                blocked = await c.brain.handle("start_background_task", {"question": "Compare Saturday cable-routing notes"})
                h.condition("replacement_blocked_until_cancelled_work_cleans_up", blocked_receipt=blocked)
                h.check("no_replacement_started_during_cleanup", blocked["job_id"] == old["job_id"]
                        and "cleaning up" in blocked.get("note", "") and len(c.brain.jobs) == 1)
                await h.finish(old, "Friday result: route the cable through the center.")
                await h.observe()
                h.check("old_result_suppressed_before_replacement", not h.delivered_ids and old["status"] == "cancelled")
                new = await h.start_job("Compare Saturday cable-routing notes")
                h.check("replacement_has_new_id_and_revision", old["job_id"] != new["job_id"] and old["revision"] < new["revision"])
                h.check("pending_new_result_not_announced", not h.delivered_ids and new["status"] == "running")
                await h.finish(new, "Saturday result: the side channel leaves more clearance.")
                await h.wait_for(lambda: len(h.delivered_ids) >= 1)
                if case_id == "cancelled_job_reentry_after_replacement":
                    h.condition("cancelled_job_reentry", description="Invoke run on the retired job after replacement. This is a stale invocation test, not concurrent provider returns.")
                    before = len([e for e in h.recorder.events if e["name"] == "controlled_analyst_returned"])
                    await c.brain.run(old)
                    after = len([e for e in h.recorder.events if e["name"] == "controlled_analyst_returned"])
                    h.check("retired_job_does_not_run_analyst_again", before == after)
                await h.observe()
                h.check("only_current_revision_delivered", h.delivered_ids == [new["job_id"]])
                h.check("old_completion_suppressed_by_real_brain", old["status"] == "cancelled" and "summary" not in old)
            else:
                await h.user_turn("Compare cable routing.")
                job = await h.start_job("Compare cable routing")
                h.check("start_returns_before_controlled_analyst_finishes", job["status"] == "running" and not h.delivered_ids)
                if case_id == "cancel_running_late_result":
                    await h.wait_for(lambda: job["job_id"] in h.analyst.gates)
                    h.condition("cancel_before_analyst_returns")
                    await h.cancel(job)
                    h.condition("fixture_injects_task_cancellation", description="Explicitly cancel the synthetic worker task; it deliberately returns late. This does not claim a remote provider stopped.")
                    c.brain.tasks[job["job_id"]].cancel()
                    await h.wait_for(lambda: any(e["name"] == "controlled_analyst_ignored_cancellation" for e in h.recorder.events))
                    await h.finish(job, "Late cancelled cable-routing result.")
                    await h.observe()
                    h.check("cancelled_job_stays_cancelled", job["status"] == "cancelled")
                    h.check("late_cancelled_summary_not_published", "summary" not in job and not h.delivered_ids)
                elif case_id == "changed_topic_revision":
                    await c.handle({"type": "playback_state", "playing": True})
                    await h.finish(job, "Old cable-routing result.")
                    await h.user_turn("Tell me a quiet ocean fact instead.")
                    await c.handle({"type": "playback_state", "playing": False})
                    h.condition("changed_topic_through_native_user_event", completed_revision=job["revision"], current_revision=c.user_revision)
                    await h.observe()
                    h.check("old_revision_not_announced", not h.delivered_ids and not job["announced"])
                    status = await c.brain.handle("background_task_status", {"job_id": job["job_id"]})
                    h.check("old_result_remains_available_to_explicit_status_read", status.get("summary") == "Old cable-routing result.")
                    h.check("historical_result_is_explicitly_stale", status["status"] == "stale" and "Historical" in status.get("note", ""))
                elif case_id == "duplicate_completion":
                    h.condition("duplicate_runner_completion_callback", description="Invoke production BackgroundBrain.run twice for the same job; this is not a network receipt ingestion path.")
                    duplicate_start = await c.brain.handle("start_background_task", {"question": "Compare cable routing"})
                    h.check("duplicate_start_reuses_running_job", duplicate_start["job_id"] == job["job_id"] and len(c.brain.jobs) == 1)
                    await h.finish(job, "Result with a duplicate completion callback.")
                    await h.wait_for(lambda: len(h.delivered_ids) >= 1)
                    await c.brain.run(job)
                    await h.observe()
                    completion_events = [e for e in h.recorder.events
                                         if e.get("name") == "production_websocket_emit"
                                         and e.get("event", {}).get("type") == "brain_job"
                                         and e["event"].get("job_id") == job["job_id"]
                                         and e["event"].get("status") == "complete"]
                    h.check("duplicate_run_does_not_emit_another_completion", len(completion_events) == 1)
                    returns = [e for e in h.recorder.events if e["name"] == "controlled_analyst_returned"]
                    h.check("duplicate_run_does_not_reinvoke_analyst", len(returns) == 1)
                    h.check("completed_result_context_requested_once", h.delivered_ids == [job["job_id"]])
                elif case_id == "cancel_completed_before_delivery":
                    await c.handle({"type": "playback_state", "playing": True})
                    await h.finish(job, "Completed result the user now cancels.")
                    h.condition("cancel_after_complete_before_context", status_before_cancel=job["status"], announced=job["announced"])
                    await h.cancel(job)
                    await c.handle({"type": "playback_state", "playing": False})
                    await h.observe()
                    h.check("cancel_completed_result_prevents_context", not h.delivered_ids,
                            actual_status_after_cancel=job["status"], delivered_job_ids=h.delivered_ids)
                else:
                    guard = case_id.removeprefix("guard_")
                    h.condition("one_active_delivery_guard", guard=guard)
                    if guard == "playback":
                        await c.handle({"type": "playback_state", "playing": True})
                    elif guard == "pending_audio":
                        c.mask.pending["controlled-audio"] = "pending"
                    elif guard == "assistant_turn":
                        await c.realtime_event({"type": "turn.created", "turn": {"role": "assistant", "id": "controlled-assistant"}})
                    elif guard == "native_delegation":
                        c.voice.turn = "controlled-native-delegation"
                    await h.finish(job, "Guarded result.")
                    await h.observe()
                    h.check("no_context_while_guard_active", not h.delivered_ids and not job["announced"])
                    if guard == "playback":
                        await c.handle({"type": "playback_state", "playing": False})
                    elif guard == "pending_audio":
                        c.mask.pending.clear()
                    elif guard == "assistant_turn":
                        await c.realtime_event({"type": "turn.done", "turn": {"role": "assistant", "id": "controlled-assistant", "transcript": "Finished."}})
                    else:
                        c.voice.turn = None
                    h.recorder.record("fixture_guard_released", guard=guard)
                    await h.wait_for(lambda: len(h.delivered_ids) >= 1)
                    h.check("context_delivered_after_guard_release", h.delivered_ids == [job["job_id"]])
        except Exception as exc:
            h.check("fixture_completed_without_exception", False, error_type=type(exc).__name__)
        return h.result(case_id)


async def run_suite(ids=None):
    cases = list(SCENARIOS if ids is None else ids)
    if not cases or any(c not in SCENARIOS for c in cases):
        raise ValueError("Select known component cases")
    rows = []
    for case in cases:
        rows.append(await run_scenario(case))
    source_files = [Path(__file__), BRAIN / "duplex/background.py", BRAIN / "duplex/server.py"]
    return {"fixture_version": VERSION, "created_utc": datetime.now(timezone.utc).isoformat(),
            "evidence_scope": "production_component_with_controlled_transports", "audio_e2e": False,
            "source_hashes": {p.relative_to(BRAIN.parent).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
            "limitations": ["Actual production delivery loop and background state policy; analyst completion is gated synthetic data.",
                            "Native context calls, websocket delivery and audio-mask state are recorded doubles.",
                            "No provider model, browser, playback, microphone, acoustic interruption or subjective voice quality is measured.",
                            "Production delivery polling remains 200 ms; recorded timings include deliberate blocked intervals.",
                            "Replacement waits for cancelled work to finish cleanup. No overlapping old/new provider requests or reordered network completions are exercised.",
                            "Cancelled work deliberately ignores an injected task cancellation; teardown releases controlled gates before joining tasks.",
                            "Duplicate completion re-enters BackgroundBrain.run; there is no separate network receipt ingestion API."],
            "passed": all(r["passed"] for r in rows), "passed_cases": sum(r["passed"] for r in rows),
            "total_cases": len(rows), "cases": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ids", help="Comma-separated component scenario IDs")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = asyncio.run(run_suite(args.ids.split(",") if args.ids else None))
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    summary = {k: report[k] for k in ("fixture_version", "evidence_scope", "audio_e2e", "passed", "passed_cases", "total_cases")}
    summary["failed_checks"] = [{"case_id": row["case_id"], **check} for row in report["cases"] for check in row["checks"] if not check["passed"]]
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
