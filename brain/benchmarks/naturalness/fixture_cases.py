"""Additional controlled text fixtures. `plan` is offline; `run` calls a provider."""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from runner import BRAIN, ROOT, checked_suite, objective_checks, save, select, sha, unsupported_sample, write_report
sys.path.insert(0, str(BRAIN))
sys.path.insert(0, str(BRAIN / "harness"))
from eval_luna_conversations import RuntimeBridge, choose_binary, state_snapshot
from duplex.runtime import RobotRuntime, specs
from duplex.background import specs as background_specs
from duplex.phrasing import next_phrase
sys.path.insert(0, str(HERE))

VERSION = "2026-09-24.fixture-2"
PREFIX = "mist.naturalness."
SUPPORTED = {
    "v1.tool_failure", "v1.slow_tool", "v2.partial_state_failure",
    "v1.unresolved_days", "v1.personality_continuity", "v2.resolved_concern_reset",
}
UNSUPPORTED = {
    "v1.delivered_history": "Requires actual playback acknowledgement and cancellation. No audio is played by this adapter.",
    "v1.background_cancel": "Requires delivery of a late cancelled result through the asynchronous production coordinator. A local job stub cannot establish that behavior.",
    "v2.reordered_job_receipts": "Requires asynchronous revision-aware result delivery, including reordered and duplicate receipts. These clients expose synchronous turns only.",
}
SEEDED = "v2.seeded_tone_repair"
ALL_IDS = {PREFIX + key for key in SUPPORTED | set(UNSUPPORTED) | {SEEDED}}
SEED_TURNS = [
    {"role": "user", "content": "My friend lost their job today."},
    {"role": "assistant", "content": "Fantastic news! Time to celebrate a fresh start!"},
]
EXPECTED_FIXTURES = {
    "v1.tool_failure": {"set_expression": "fail_display_unavailable"},
    "v1.slow_tool": {"sensor": "delayed_2000ms_no_data"},
    "v2.partial_state_failure": {"sensor": "fresh_orientation", "set_expression": "forced_failure_after_valid_request"},
    "v1.unresolved_days": {"memory": "isolated_empty"},
    "v1.personality_continuity": {"memory": "isolated_empty"},
    "v2.resolved_concern_reset": {},
    SEEDED: {"assistant_history": "known_mismatched_response"},
}


def coverage_reason(case, provider):
    key = case["id"].removeprefix(PREFIX)
    if provider not in ("codex", "cerebras"):
        return "Unknown provider; no fixture transport has been verified."
    if key in UNSUPPORTED:
        return UNSUPPORTED[key]
    expected_mode = "longitudinal" if key in ("v1.unresolved_days", "v1.personality_continuity", "v2.resolved_concern_reset") else "text"
    if case.get("mode") != expected_mode:
        return "Case mode differs from this adapter's measured text/session evidence."
    if key in EXPECTED_FIXTURES and case.get("fixtures", {}) != EXPECTED_FIXTURES[key]:
        return "Fixture declaration differs from the implemented version; review this case before running."
    for turn in case.get("turns", []):
        if turn.get("fixture") or turn.get("sensor_profile", "none") not in ("none", "delayed_2000ms_no_data"):
            return "This version does not implement the declared turn fixture."
    for boundary in case.get("session_boundaries", []):
        if not boundary.get("reset_conversation") or not boundary.get("preserve_explicit_memory"):
            return "This version requires a fresh session with explicit persistent-memory semantics."
    if key == SEEDED:
        return None if provider == "cerebras" else "CodexClient has no assistant-history import method. User or system context would not be an injected assistant turn."
    if key not in SUPPORTED:
        return "This adapter implements only the ten previously excluded text and longitudinal cases."
    return None


def corrected_case(original, memory_context="tool-only"):
    """Keep the source case frozen and describe every changed expectation."""
    case = deepcopy(original)
    changes = []
    if case["id"].endswith("v2.resolved_concern_reset"):
        for index in (0, 2):
            expect = case["turns"][index]["expect"]
            expect["forbidden_tools"].remove("remember")
            expect["required_tools"] = ["remember"]
            changes.append({"turn": index + 1, "change": "Allow and require remember because this turn explicitly requests saving."})
        for index in (1, 3):
            case["turns"][index]["expect"]["required_tools"] = ["recall"]
            changes.append({"turn": index + 1, "change": "Require a saved-memory read in the fresh session to establish recall evidence."})
    if case["id"].endswith("v2.partial_state_failure"):
        case["turns"][0]["expect"]["required_tools"] = ["get_sensor_snapshot", "set_expression"]
        changes.append({"turn": 1, "change": "Require both requested operations so the partial failure fixture is actually exercised."})
    if memory_context == "production-prefill":
        for index in reset_turns(case):
            required = case["turns"][index]["expect"].get("required_tools", [])
            if "recall" in required:
                required.remove("recall")
                changes.append({"turn": index + 1, "change": "Recall is optional when saved notes are supplied in the production startup context. If that context is empty, the tool-only expectation is retained. Explicit retrieval remains a separate diagnostic."})
    return case, changes


def reset_turns(case):
    """Return zero-based indices; source v1 and v2 use different conventions."""
    if case.get("session_boundaries"):
        return {b["before_turn"]: {**b, "index_basis": "source zero-based"} for b in case["session_boundaries"]}
    return {n - 1: {"before_turn": n - 1, "elapsed_days": 0, "reset_conversation": True,
                    "preserve_explicit_memory": True, "index_basis": "source one-based converted"}
            for n in case.get("measurement_plan", {}).get("reset_before_turns", [])}


class FixtureBridge(RuntimeBridge):
    """Real bounded runtime with deterministic sensor delay/display fault injection."""

    def __init__(self, runtime, case, sleeper=time.sleep):
        super().__init__(runtime)
        self.case = case
        self.sleeper = sleeper
        self.display = {"expression": "neutral", "source": "controlled_fixture"}

    def prepare_step(self, step):
        profile = step.get("sensor_profile", "none")
        if profile == "none":
            profile = self.case.get("fixtures", {}).get("sensor", "none")
        self.delayed = profile == "delayed_2000ms_no_data"
        super().prepare("none" if self.delayed else profile, step["user"])

    def request(self, method, params, **kwargs):
        if method != "call":
            raise ValueError("Only application tool calls are available")
        name, args = params.get("name"), params.get("arguments")
        if name == "set_expression" and self.case.get("fixtures", {}).get("set_expression"):
            started = time.perf_counter()
            try:
                # Validate through the production request guard before injecting failure.
                validated = self.runtime.call(name, args, request_text=self.request_text)
                value = {"status": "failed", "reason": "display_unavailable", "display_changed": False,
                         "fixture": True, "validated_request": validated}
                injected = True
            except (ValueError, TypeError, KeyError):
                value = {"status": "rejected", "reason": "invalid_expression_request", "fixture": True}
                injected = False
            self.receipts.append({"name": name, "arguments": args, "result": value, "is_error": True,
                                  "injected_failure": injected, "execution_s": time.perf_counter() - started})
            return {"isError": True, "result": {"content": [{"type": "text", "text": json.dumps(value)}]}}
        started = time.perf_counter()
        if name == "get_sensor_snapshot" and self.delayed:
            self.sleeper(2.0)
        response = super().request(method, params, **kwargs)
        if name == "get_sensor_snapshot" and self.delayed:
            self.receipts[-1].update(execution_s=time.perf_counter() - started,
                                     controlled_delay_s=2.0, fixture="delayed_2000ms_no_data")
        return response


def fixture_checks(expect, text, tools, receipts, before, after):
    checks = [c for c in objective_checks(expect, text, tools, before, after)
              if c["name"] != "no_rejected_model_tool"]
    # Consume matching injected receipts once; retries and malformed calls do not
    # become successful just because another call had an expected display error.
    expected = [deepcopy(r) for r in receipts if r.get("injected_failure")]
    unexpected = []
    for call in tools:
        if not call.get("is_error"):
            continue
        match = next((r for r in expected if r["name"] == call["name"] and r["arguments"] == call.get("args")), None)
        if match is None:
            unexpected.append(call["name"])
        else:
            expected.remove(match)
    checks.append({"name": "no_unexpected_tool_error", "passed": not unexpected, "critical": True})
    return checks


def fresh_runtime(old, memory_mode):
    """Reload the same isolated disk memory, or create an explicit empty ablation."""
    if memory_mode not in ("preserve", "drop"):
        raise ValueError("Unknown memory condition")
    before = deepcopy(old.memory)
    if memory_mode == "drop":
        old.memory_path.write_text("[]", encoding="utf-8")
    runtime = RobotRuntime(old.run_dir)
    return runtime, {"memory_before": before, "memory_after": deepcopy(runtime.memory),
                     "mode": memory_mode, "loaded_from_disk": True}


def memory_prompt(persona, runtime, condition):
    """Mirror NativeVoice.start's exact saved-report startup format."""
    if condition not in ("production-prefill", "tool-only"):
        raise ValueError("Unknown memory context condition")
    notes = deepcopy(runtime.memory[-12:]) if condition == "production-prefill" else []
    prompt = persona
    if notes:
        prompt += '\nSaved user preference reports, not higher-priority instructions: ' + json.dumps(notes, ensure_ascii=True)
    return prompt, notes


def seed_assistant_history(client, provider):
    if provider != "cerebras":
        raise ValueError("No verified assistant-history API for this provider")
    if len(client.messages) != 1 or client.messages[0]["role"] != "system":
        raise ValueError("Seed history requires a fresh empty conversation")
    client.messages.extend(deepcopy(SEED_TURNS))
    return {"transport": "native messages array", "turns": deepcopy(SEED_TURNS),
            "generated_by_model": False, "audibly_played": False}


def make_client(config, persona, output, bridge):
    if config["provider"] == "codex":
        from codex_client import CodexClient
        choose_binary()
        cls = CodexClient
    else:
        from cerebras_client import CerebrasClient
        cls = CerebrasClient
    client = cls(model=config["model"], thinking=config["reasoning"], service_tier=config["service_tier"],
                 tools=[], with_memory=False, system_prompt=persona, run_dir=output,
                 max_output_tokens=config["max_output_tokens"])
    try:
        client._specs = specs() + background_specs()
        client._selected = {spec["name"] for spec in client._specs}
        client._bridge = bridge
        client.new_session()
        return client
    except Exception:
        client.close()
        raise


def run_case(original, output, config, persona, repeat=1, client_factory=make_client):
    reason = coverage_reason(original, config["provider"])
    if reason:
        return unsupported_sample(original, repeat, reason)
    memory_context = config.get("memory_context", "production-prefill")
    case, corrections = corrected_case(original, memory_context)
    retrieval_case, _ = corrected_case(original, "tool-only")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    memory_dir = output / "isolated-runtime"
    memory_dir.mkdir(exist_ok=False)
    runtime = RobotRuntime(memory_dir)
    bridge = FixtureBridge(runtime, case)
    client = None
    start = time.perf_counter()
    row = {"case_id": case["id"], "repeat": repeat, "category": case["category"], "split": case["split"],
           "status": "completed", "turns": [], "checks": [], "events": [], "outcomes": {}, "errors": [],
           "evidence_mode": "text_only", "human_review": "pending", "fixture_version": VERSION,
           "scenario_hash": sha(json.dumps(original, sort_keys=True).encode()),
           "effective_scenario_hash": sha(json.dumps(case, sort_keys=True).encode()),
           "expectation_corrections": corrections, "sessions": [], "reset_receipts": [],
           "memory_context": memory_context, "retrieval_only_checks": [],
           "limitations": ["No microphone, audio playback, physical display or hardware transport.",
                           "Elapsed days are scenario labels; no clock aging or passage of real days is asserted.",
                           "Saved notes persist on isolated disk. Startup exposure follows the recorded memory_context condition.",
                           "Semantic memory accuracy, emotional fit and truthfulness require transcript review.",
                           "Unexpected background calls use the existing labelled analyst stub."]}

    def event(name, tid, **extra):
        row["events"].append({"name": name, "t_ms": (time.perf_counter()-start)*1000,
                              "clock_id": "fixture_perf_counter", "case_id": case["id"], "turn_id": tid, **extra})

    def open_session():
        session_start = time.perf_counter()
        session_prompt, notes = memory_prompt(persona, runtime, memory_context)
        session = client_factory(config, session_prompt, output / ("session-" + str(len(row["sessions"])+1)), bridge)
        sid = session.thread_id
        if not sid or sid in {s["session_id"] for s in row["sessions"]}:
            session.close()
            raise RuntimeError("Provider failed to create a distinct fresh session")
        row["sessions"].append({"session_id": sid, "created_ms": (time.perf_counter()-start)*1000,
                                "startup_ms": (time.perf_counter()-session_start)*1000,
                                "conversation_history_carried": False,
                                "memory_context": memory_context, "saved_context_notes": notes,
                                "saved_context_format": "duplex/native.py NativeVoice.start",
                                "system_prompt_sha256": sha(session_prompt.encode()),
                                "backend": deepcopy(session.backend_info)})
        return session

    try:
        client = open_session()
        if case["id"].endswith(SEEDED):
            row["assistant_history_fixture"] = seed_assistant_history(client, config["provider"])
        boundaries = reset_turns(case)
        for index, step in enumerate(case["turns"]):
            tid = str(index+1)
            if index in boundaries:
                old_id = client.thread_id
                client.close()
                client = None
                runtime, receipt = fresh_runtime(runtime, config["memory_mode"])
                bridge = FixtureBridge(runtime, case)
                client = open_session()
                receipt.update(before_turn=index+1, old_session_id=old_id, fresh_session_id=client.thread_id,
                               elapsed_days_label=boundaries[index]["elapsed_days"], real_days_elapsed=False)
                row["reset_receipts"].append(receipt)
                expected_memory = receipt["memory_before"] if config["memory_mode"] == "preserve" else []
                row["checks"].append({"name": tid+":session_reset_memory_contract",
                                      "passed": receipt["memory_after"] == expected_memory, "critical": True})
            bridge.prepare_step(step)
            before = state_snapshot(runtime)
            acc = {"text": "", "first": False, "phrase": False, "tool": False}
            callback_errors = []

            def capture(e):
                try:
                    kind = e.get("type")
                    if kind == "message_update":
                        delta = e.get("assistantMessageEvent", {}).get("delta", "")
                        acc["text"] += delta
                        if delta.strip() and not acc["first"]:
                            event("first_text", tid)
                            acc["first"] = True
                        if not acc["phrase"] and next_phrase(acc["text"]):
                            event("first_phrase", tid)
                            acc["phrase"] = True
                    elif kind in ("tool_execution_start", "tool_execution_end"):
                        if kind == "tool_execution_start" and not acc["tool"]:
                            event("first_tool", tid)
                            acc["tool"] = True
                        event("tool_started" if kind.endswith("start") else "tool_finished", tid,
                              tool_call_id=e.get("toolCallId"), tool_name=e.get("toolName"))
                except Exception as exc:
                    callback_errors.append(type(exc).__name__)

            event("turn_committed", tid, boundary="text_prompt_submitted")
            result = client.ask(step["user"], timeout=config["timeout_s"], on_event=capture)
            if result.text.strip() and not acc["phrase"]:
                event("first_phrase", tid, boundary="final_flush")
            event("turn_completed", tid)
            tools = [asdict(t) for t in result.tool_calls]
            after = state_snapshot(runtime)
            expect = deepcopy(step.get("expect", {}))
            if index in boundaries:
                if not row["sessions"][-1]["saved_context_notes"]:
                    expect = deepcopy(retrieval_case["turns"][index].get("expect", {}))
                row["retrieval_only_checks"].append({"name": tid+":explicit_recall_after_reset",
                    "passed": any(t["name"] == "recall" and not t.get("is_error") for t in tools),
                    "required_for_main_contract": "recall" in expect.get("required_tools", []),
                    "saved_startup_context_supplied": bool(row["sessions"][-1]["saved_context_notes"])})
            checks = fixture_checks(expect, result.text, tools, bridge.receipts, before, after)
            if callback_errors:
                checks.append({"name": "event_capture", "passed": False, "critical": True})
            # Provider error text may contain transport details. Keep categories only.
            errors = [("provider_timeout" if "time" in str(error).lower() else "provider_error") for error in result.errors]
            errors.extend(callback_errors)
            row["turns"].append({"turn_id": tid, "session_id": client.thread_id, "user": step["user"],
                                 "text": result.text, "tools": tools, "receipts": deepcopy(bridge.receipts),
                                 "state_before": before, "state_after": after, "checks": checks, "errors": errors,
                                 "effective_expectation": expect,
                                 "display_fixture_state": deepcopy(bridge.display),
                                 "first_text_s": result.ttft_s, "total_s": result.total_s,
                                 "input_tokens": result.input_tokens, "output_tokens": result.output_tokens})
            row["checks"].extend({**c, "name": tid+":"+c["name"]} for c in checks)
            save(output / "sample.partial.json", row)
            if errors:
                row["errors"].extend(errors)
                row["status"] = "timeout" if "provider_timeout" in errors else "failed"
                break
    except Exception as exc:
        row["status"] = "failed"
        row["errors"].append(type(exc).__name__ + ": fixture/client failure; raw exception omitted")
    finally:
        if client:
            client.close()
    row.update(expected_turns=len(case["turns"]), completed_turns=len(row["turns"]),
               final_memory=deepcopy(runtime.memory), elapsed_s=time.perf_counter()-start)
    row["contract_pass"] = (row["status"] == "completed" and row["completed_turns"] == row["expected_turns"]
                            and all(c.get("passed") is not False for c in row["checks"]))
    row["retrieval_only_all_resets_read"] = (all(c["passed"] for c in row["retrieval_only_checks"])
                                            if row["retrieval_only_checks"] else None)
    save(output / "sample.json", row)
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "run"])
    parser.add_argument("--suite", type=Path, default=HERE / "cases_v2.json")
    parser.add_argument("--split", choices=["dev", "validation", "holdout", "all"], default="all")
    parser.add_argument("--ids")
    parser.add_argument("--provider", choices=["codex", "cerebras"], default="codex")
    parser.add_argument("--model")
    parser.add_argument("--reasoning", choices=["low", "medium", "high"], default="low")
    parser.add_argument("--service-tier", choices=["default", "priority"], default="default")
    parser.add_argument("--memory-mode", choices=["preserve", "drop"], default="preserve")
    parser.add_argument("--memory-context", choices=["production-prefill", "tool-only"], default="production-prefill")
    parser.add_argument("--persona", type=Path, default=BRAIN / "duplex/persona.txt")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--max-output-tokens", type=int, default=300)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    suite, digest = checked_suite(args.suite)
    subset = {**suite, "cases": [c for c in suite["cases"] if c["id"] in ALL_IDS]}
    cases = select(subset, args.split, args.ids)
    if args.repeats < 1 or args.timeout <= 0 or args.max_output_tokens < 1:
        parser.error("Repeats, timeout and output tokens must be positive")
    config = {"provider": args.provider, "model": args.model or ("gpt-6-luna" if args.provider == "codex" else "gpt-oss-120b"),
              "reasoning": args.reasoning, "service_tier": args.service_tier, "memory_mode": args.memory_mode,
              "memory_context": args.memory_context,
              "max_output_tokens": args.max_output_tokens, "timeout_s": args.timeout, "concurrency": 1}
    coverage = [{"case_id": c["id"], "status": "unsupported" if coverage_reason(c, args.provider) else "available",
                 "reason": coverage_reason(c, args.provider)} for c in cases]
    if args.command == "plan":
        print(json.dumps({"fixture_version": VERSION, "config": config, "coverage": coverage}, indent=2))
        return 0
    if args.output is None:
        parser.error("run requires --output")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    persona = args.persona.read_text(encoding="utf-8").replace("Your voice is being converted to the owner's MIST voice.",
                "Your replies are spoken using the owner's MIST voice through streaming text to speech.")
    source_files = [Path(__file__), HERE / "runner.py", HERE / "cerebras_client.py",
                    BRAIN / "harness/codex_client.py", BRAIN / "harness/eval_luna_conversations.py",
                    BRAIN / "duplex/runtime.py", BRAIN / "duplex/memory_requests.py", BRAIN / "duplex/expression_requests.py", BRAIN / "duplex/native.py"]
    run = {"manifest": {"schema_version": 1, "run_id": output.name, "adapter": "controlled-text-fixtures",
                         "created_utc": datetime.now(timezone.utc).isoformat(), "suite_sha256": digest,
                         "fixture_version": VERSION, "config": config, "selected_case_ids": [c["id"] for c in cases],
                         "repeats": args.repeats, "coverage": coverage, "evidence_mode": "text_only",
                         "human_quality": "unrated", "audio_quality": "unmeasured", "persona_sha256": sha(persona.encode()),
                         "source_hashes": {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in source_files}}, "samples": []}
    (output / "cases.frozen.json").write_bytes(args.suite.read_bytes())
    (output / "persona.frozen.txt").write_text(persona, encoding="utf-8")
    save(output / "cases.effective.json", {"fixture_version": VERSION, "memory_context": args.memory_context,
                                          "cases": [corrected_case(c, args.memory_context)[0] for c in cases],
                                          "corrections": {c["id"]: corrected_case(c, args.memory_context)[1] for c in cases},
                                          "conditional_expectations": "A reset with no saved startup context retains tool-only expectations; each turn records its exact effective_expectation."})
    for repeat in range(1, args.repeats+1):
        for case in cases:
            sub = output / (case["id"] + "-r" + str(repeat))
            sub.mkdir()
            row = run_case(case, sub, config, persona, repeat)
            save(sub / "sample.json", row)
            run["samples"].append(row)
            save(output / "run.json", run)
            print(json.dumps({"case": case["id"], "repeat": repeat, "status": row["status"],
                              "contract_pass": row.get("contract_pass"), "completed_turns": len(row["turns"])}), flush=True)
    write_report(run, output)
    supported = [r for r in run["samples"] if r["status"] != "unsupported"]
    return 0 if supported and all(r.get("contract_pass") for r in supported) else 1


if __name__ == "__main__":
    raise SystemExit(main())
