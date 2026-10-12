"""Editable preflight case and scoring spec for the Nova/Flux/Scribe speech bench.

This is not a frozen manifest: it references the existing 2026-09-24 cached,
synthetic fixtures and must be independently reviewed before any trial. The
scorer deliberately separates event mechanics from semantic oracle judgments.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import hashlib
import re
import wave
from pathlib import Path
from typing import Any

FIXTURE_ROOT = "brain/results/e2e_20260924/fixtures_v2/audio"
SOURCE_MANIFEST = "brain/results/e2e_20260924/fixtures_v2/manifest.json"
SOURCE_SUITE_SHA256 = "29a694dd96260e26f413e13fd32a8d84e72de573139fe4631faf2451114f6ae9"


@dataclass(frozen=True)
class Case:
    id: str
    fixture: str
    expected_transcript: tuple[str, ...]
    semantic_constraints: tuple[str, ...]
    class_name: str
    # Timing bounds are relative to the specified segment or final input sample.
    timing: dict[str, Any]
    wait_windows_ms: tuple[tuple[int, int], ...] = ()
    expected_reply: bool = True
    expected_stop: bool = False
    preserve_backchannel: bool = False
    entity_tokens: tuple[tuple[str, ...], ...] = ()
    notes: tuple[str, ...] = ()
    seed_text: str | None = None
    seed_delay_after_playback_ms: int | None = None


CASES = (
    Case("normal_end", "audio_phrase_seam-1.wav",
         ("Explain how a screw, washer and bracket fit together in four short sentences.",),
         ("answer the assembly explanation request", "do not answer before the full utterance ends"),
         "completed_turn", {"utterance_end_ms": 5880,
                            "reply_latency_anchor": "input_last_nonsilent_sample",
                            "reply_latency_ms_max": 2500, "early_reply_before_final_segment": False},
         expected_reply=True, notes=("Synthetic one-segment request; segment end 5880 ms.",)),
    Case("unfinished_pause_resume", "audio_long_pause-1.wav",
         ("The green bracket", "is the one that", "needs sanding."),
         ("retain the unfinished clause across pauses", "respond only after the final fragment"),
         "unfinished_turn", {"utterance_end_ms": 5560,
                             "reply_latency_anchor": "input_last_nonsilent_sample",
                             "reply_latency_ms_max": 2500, "early_reply_before_final_segment": False},
         wait_windows_ms=((1240, 2540), (3260, 4360)), expected_reply=True,
         entity_tokens=(("green", "bracket"), ("sanding",)),
         notes=("Fragments are independently synthesized with exact silent gaps; not natural slow speech.",)),
    Case("yeah_backchannel", "audio_backchannel_yes-1.wav", ("yeah",),
         ("preserve a supportive acknowledgement", "do not yield the floor or restart the explanation"),
         "backchannel", {"utterance_start_ms": 0, "utterance_end_ms": 520,
                         "backchannel_response_window_ms": (0, 900)},
         expected_reply=False, preserve_backchannel=True,
         seed_text="The bracket has three checks. First the screw clearance, then the fit, then the cable path.",
         seed_delay_after_playback_ms=900,
         notes=("Inject during seeded assistant speech 900 ms after playback starts; seed content is in source manifest.",)),
    Case("explicit_stop", "audio_stop-1.wav", ("Stop talking.",),
         ("cancel active response and queued speech", "do not continue the stopped answer"),
         "stop", {"command_end_ms": 1240, "stop_latency_anchor": "command_start",
                  "stop_latency_ms_max": 900}, expected_reply=False, expected_stop=True,
         seed_text="Let me explain the bracket in three steps.",
         seed_delay_after_playback_ms=800),
    Case("correction", "audio_correction-1.wav", ("Wait, I said landscape.",),
         ("replace portrait with landscape in the pending task", "do not retain the superseded orientation"),
         "correction", {"utterance_start_ms": 0, "utterance_end_ms": 1560,
                        "reply_latency_anchor": "input_last_nonsilent_sample",
                        "reply_latency_ms_max": 2500}, entity_tokens=(("landscape",),),
         seed_text="The portrait phone holder needs camera clearance.",
         seed_delay_after_playback_ms=1000),
    Case("negated_stop", "audio_negated_stop-1.wav", ("Do not stop, I am listening.",),
         ("preserve negation", "continue the existing explanation without cancellation"),
         "non_stop", {"utterance_start_ms": 0, "utterance_end_ms": 2560},
         expected_reply=False, expected_stop=False,
         seed_text="There are three checks.", seed_delay_after_playback_ms=800),
    Case("quoted_stop", "audio_quoted_stop-1.wav",
         ("The label says stop talking, but I want you to read the whole label.",),
         ("treat stop talking as quoted label content", "read or discuss the full label without cancellation"),
         "quoted_content", {"utterance_start_ms": 0, "utterance_end_ms": 3720},
         expected_reply=True, expected_stop=False),
    Case("face_request", "audio_sad_mouth-1.wav",
         ("Show sad variation two and say a calm goodnight with a short pause between sentences.",),
         ("request sad face variation two", "speak a calm goodnight with a short pause"),
         "face_and_speech", {"utterance_start_ms": 0, "utterance_end_ms": 5280,
                             "reply_latency_anchor": "input_last_nonsilent_sample",
                             "reply_latency_ms_max": 2500},
         notes=("Face action requires a browser/render receipt; speech or expression-call receipt alone does not prove visible delivery.",)),
)

ARMS = tuple(f"{model}-jev-{jev}" for model in ("Nova", "Flux", "Scribe")
             for jev in ("off", "on"))
CORE_REPETITIONS = 2
CORE_TRIALS = len(CASES) * len(ARMS) * CORE_REPETITIONS  # 96; root-selected bounded slice.
LEGACY_SUBSET_TRIALS = 8
SHADOW_OPTIONAL_TRIALS = 8


def score_trial(case: Case, *, events: list[dict], transcript: list[dict],
                audio_clock: dict, semantic_judgments: dict | None = None,
                task_receipts: list[dict] | None = None,
                accepted_transcript: str | None = None,
                raw_provider_transcript: str | None = None,
                active_user_turn_id: str | None = None,
                input_user_turn_ids: list[str] | tuple[str, ...] | set[str] = (),
                input_start_ms: float | None = None,
                seed_turn_id: str | None = None) -> dict:
    """Deterministic per-metric score from captured evidence.

    `transcript` contains event transcript rows; `accepted_transcript` is the
    full final assembled user string after provider revisions. Pass
    `raw_provider_transcript` separately when retained. Output events use the
    production lineage contract: input has `benchmark_turn_id` and generated
    assistant text/audio has `benchmark_parent_user_turn_id`; early-output
    detection includes every ID in `input_user_turn_ids`, while task completion
    and missed-reply scoring use the final `active_user_turn_id`. Seed output
    (turn ID only) is excluded. `input_start_ms` filters global reset events. The adapter must
    supply `seed_playback_active_at_input` from its playback clock for stop and
    unwanted-stop metrics. Semantic judgments are explicit case-keyed oracle
    labels; no response phrase lookup is done here. Missing evidence is
    `None`/unavailable, never converted to a model failure.
    """
    accepted_rows = [row for row in transcript
                     if row.get("role") == "user" and row.get("final", True)]
    accepted_text = (accepted_transcript if accepted_transcript is not None else
                     " ".join(str(row.get("text", "")) for row in accepted_rows))
    raw_text = raw_provider_transcript
    user_text = accepted_text.casefold()
    entities = {}
    for group in case.entity_tokens:
        key = "+".join(group)
        entities[key] = all(token.casefold() in user_text for token in group)

    event_types = [str(e.get("type", e.get("event", ""))).casefold() for e in events]
    # Match the production bench adapter's lineage fields. Never count seed TTS
    # as a reply to the input; it has a turn ID but no parent user turn ID.
    all_input_ids = set(input_user_turn_ids)
    if active_user_turn_id:
        all_input_ids.add(active_user_turn_id)
    correlated = [e for e in events if all_input_ids and
                  e.get("benchmark_parent_user_turn_id") in all_input_ids]
    final_correlated = [e for e in correlated if e.get("benchmark_parent_user_turn_id") == active_user_turn_id]
    cancel_events = [e for e in events if str(e.get("type", e.get("event", ""))).casefold()
                     in {"audio_reset", "playback_cancelled", "playback_interrupt", "cancel_ack"}
                     and input_start_ms is not None and e.get("t_ms", -1) >= input_start_ms]
    correlated_reply = [e for e in correlated if e.get("type") in {"transcript_delta", "audio"}
                        and (e.get("role") == "assistant" or e.get("type") == "audio")]
    reply_events = correlated_reply
    anchor = audio_clock.get("input_last_nonsilent_sample_ms")
    clip_start = audio_clock.get("clip_start_ms")
    first_reply = next((e.get("t_ms") for e in reply_events if isinstance(e.get("t_ms"), (int, float))), None)
    latency = round(first_reply - anchor, 3) if isinstance(first_reply, (int, float)) \
        and isinstance(anchor, (int, float)) else None
    judgment = semantic_judgments or {}
    capture_complete = audio_clock.get("capture_complete") is True

    stt_available = bool(accepted_text)
    seed_audio = [e for e in events if e.get("type") == "audio" and seed_turn_id
                  and e.get("benchmark_turn_id") == seed_turn_id]
    floor_kept = any(e.get("type") == "debug_model" and e.get("phase") in
                     {"floor_backchannel_kept", "floor_preserved"}
                     and (input_start_ms is None or e.get("t_ms", -1) >= input_start_ms)
                     and (not active_user_turn_id or not e.get("benchmark_parent_user_turn_id") or
                          e.get("benchmark_parent_user_turn_id") == active_user_turn_id)
                     for e in events)
    # audio_reset events are playback-global in this adapter, so a reset during
    # the seeded-turn overlap counts against preservation even without lineage.
    seed_playback_active = audio_clock.get("seed_playback_active_at_input")
    valid_resets = [e for e in cancel_events if e.get("was_playing") is True or
                    ("was_playing" not in e and seed_playback_active is True)]
    seed_reset = bool(valid_resets) and seed_turn_id is not None
    stop_observed = bool(valid_resets) and bool(seed_turn_id) and seed_playback_active is True
    stop_event = valid_resets[0] if valid_resets else None
    unwanted_stop_case = case.id in {"yeah_backchannel", "negated_stop"}
    final_reply = [e for e in final_correlated if e.get("type") in {"transcript_delta", "audio"}
                   and (e.get("role") == "assistant" or e.get("type") == "audio")]
    face_applied = any(e.get("type") == "face" and e.get("source") in {"model", "director"}
                       and str(e.get("expression", "")).casefold() == "sad" and e.get("variant") == 2
                       for e in events)
    backchannel_transcript = case.preserve_backchannel and any(x in user_text for x in ("yeah", "yes", "mm-hm"))
    final_end = case.timing.get("utterance_end_ms")
    early_reply = (first_reply is not None and isinstance(clip_start, (int, float))
                   and isinstance(final_end, (int, float))
                   and first_reply < clip_start + final_end)
    return {
        "case_id": case.id,
        "metrics": {
            "stt_entity_fidelity": {"available": stt_available, "entities": entities,
                                    "pass": all(entities.values()) if entities else None},
            "stt_wer_diagnostic": {"available": stt_available,
                                   "accepted_transcript": accepted_text or None,
                                   "raw_provider_transcript": raw_text,
                                   "reference": " ".join(case.expected_transcript),
                                   "word_error_rate": (word_error_rate(" ".join(case.expected_transcript), accepted_text)
                                                       if stt_available else None),
                                   "normalization": "lowercase; remove punctuation only; no aliases or substitutions"},
            "false_premature_response": {
                "available": isinstance(anchor, (int, float)),
                "observed": first_reply is not None,
                "latency_from_last_nonsilent_sample_ms": latency,
                "reply_before_final_segment_end": early_reply if isinstance(clip_start, (int, float)) else None,
                "pass": (not early_reply) if isinstance(clip_start, (int, float)) else
                        (latency is None or latency >= 0),
            },
            "missed_reply": {"available": case.expected_reply and (bool(final_reply) or capture_complete),
                             "pass": (bool(final_reply) if final_reply else False if capture_complete else None)
                             if case.expected_reply else None},
            "preserved_backchannel": {"available": case.preserve_backchannel and
                                       (capture_complete or bool(cancel_events) or bool(correlated_reply)),
                                       "transcript_preserved": backchannel_transcript if case.preserve_backchannel else None,
                                       "floor_decision_kept": floor_kept if case.preserve_backchannel else None,
                                       "seed_not_cancelled": (not seed_reset) if case.preserve_backchannel else None,
                                       "no_new_assistant_reply": (not bool(correlated_reply)) if case.preserve_backchannel else None,
                                       "pass": (False if seed_reset or bool(correlated_reply) else
                                                all((backchannel_transcript, floor_kept)) if capture_complete else None)
                                       if case.preserve_backchannel else None},
            "interruption_stop": {"available": case.expected_stop and seed_playback_active is True and
                                  (stop_observed or capture_complete),
                                  "stop_observed": stop_observed if case.expected_stop else None,
                                  "latency_from_input_start_ms": (round(stop_event["t_ms"] - input_start_ms, 3)
                                                                   if case.expected_stop and stop_observed else None),
                                  "pass": (stop_observed if stop_observed else False if capture_complete else None)
                                  if case.expected_stop and seed_playback_active is True else None},
            "unwanted_stop": {"available": unwanted_stop_case and seed_playback_active is True and
                              (bool(valid_resets) or capture_complete),
                              "observed": bool(valid_resets) if unwanted_stop_case else None,
                              "pass": (False if valid_resets else True if capture_complete else None)
                              if (unwanted_stop_case and seed_playback_active is True) else None},
            "applied_requested_face": {"available": case.id == "face_request" and bool(events),
                                       "pass": face_applied if events else None,
                                       "visible_frame_measured": False},
            "semantic_constraints": {"available": all(k in judgment for k in case.semantic_constraints),
                                     "checks": {k: judgment.get(k) for k in case.semantic_constraints},
                                     "pass": all(judgment.get(k) is True for k in case.semantic_constraints)
                                     if all(k in judgment for k in case.semantic_constraints) else None},
            "grounded_task_receipt": {"available": task_receipts is not None,
                                      "receipts": task_receipts, "measured": False},
        },
        "hard_gates": {
            "no_early_assistant_output": (not early_reply) if isinstance(clip_start, (int, float))
                                          and case.timing.get("early_reply_before_final_segment") is False
                                          else judgment.get("no_early_assistant_output"),
            "stop_command_honored": (stop_observed if stop_observed else False if capture_complete else None)
                                    if case.expected_stop and seed_playback_active is True else None,
            "negated_stop_not_canceled": (False if valid_resets else True if capture_complete else None)
                                         if case.id == "negated_stop" and seed_playback_active is True else None,
            "required_semantics_pass": (all(judgment.get(k) is True for k in case.semantic_constraints)
                                        if all(k in judgment for k in case.semantic_constraints) else None),
            "requested_face_applied": (face_applied
                                        if case.id == "face_request" and events else None),
        },
        "event_type_counts": {kind: event_types.count(kind) for kind in sorted(set(event_types))},
    }


def _wer_tokens(text: str) -> list[str]:
    # Keep apostrophes internal where possible; punctuation is otherwise stripped.
    value = text.casefold().replace("’", "'")
    value = re.sub(r"(?<!\w)'|'(?!\w)", " ", value)
    return re.findall(r"\b[\w]+(?:'[\w]+)?\b", value)


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Standard word edit distance/reference length diagnostic, no alias fixes."""
    ref, hyp = _wer_tokens(reference), _wer_tokens(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    row = list(range(len(hyp) + 1))
    for i, word in enumerate(ref, 1):
        nxt = [i]
        for j, guess in enumerate(hyp, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (word != guess)))
        row = nxt
    return row[-1] / len(ref)


def preflight_fixtures(fixture_dir: str | Path, manifest_path: str | Path) -> dict:
    """Validate the expected source manifest digest and actual cached WAVs.

    All discrepancies are returned explicitly. A caller must resolve any flag
    before freezing; this function does not copy, edit, or repair fixtures.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    flags = []
    if manifest.get("suite_sha256") != SOURCE_SUITE_SHA256:
        flags.append({"kind": "source_manifest_hash_mismatch",
                      "expected": SOURCE_SUITE_SHA256,
                      "observed": manifest.get("suite_sha256")})
    assets = {row.get("file"): row for row in manifest.get("assets", [])}
    checks = []
    for case in CASES:
        asset = assets.get(case.fixture)
        if asset is None:
            flags.append({"kind": "asset_missing_from_manifest", "case_id": case.id,
                          "file": case.fixture})
            continue
        path = Path(fixture_dir) / case.fixture
        if not path.exists():
            flags.append({"kind": "fixture_file_missing", "case_id": case.id, "file": case.fixture})
            continue
        with wave.open(str(path), "rb") as wav:
            actual_ms = wav.getnframes() * 1000 / wav.getframerate()
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        declared_ms = float(asset["duration_ms"])
        match = abs(actual_ms - declared_ms) < 0.51
        hash_match = actual_hash == asset.get("sha256")
        row = {"case_id": case.id, "file": case.fixture, "declared_duration_ms": declared_ms,
               "actual_duration_ms": round(actual_ms, 3), "duration_matches": match,
               "expected_sha256": asset.get("sha256"), "actual_sha256": actual_hash,
               "hash_matches": hash_match}
        checks.append(row)
        if not match:
            flags.append({"kind": "duration_mismatch", **row})
        if not hash_match:
            flags.append({"kind": "fixture_hash_mismatch", **row})
    return {"source_manifest_sha256": manifest.get("suite_sha256"), "checks": checks,
            "flags": flags, "ready_to_freeze": not flags}


def aggregate(results: list[dict]) -> dict:
    """Return independent metric rates and hard-gate counts; no ordinal total."""
    names = ("stt_entity_fidelity", "false_premature_response", "missed_reply",
             "preserved_backchannel", "interruption_stop", "unwanted_stop",
             "applied_requested_face", "semantic_constraints")
    metrics = {}
    for name in names:
        values = [r["metrics"][name]["pass"] for r in results
                  if r["metrics"][name]["available"] and r["metrics"][name]["pass"] is not None]
        metrics[name] = {"n": len(values), "passed": sum(v is True for v in values),
                         "failed": sum(v is False for v in values)}
    wers = [r["metrics"]["stt_wer_diagnostic"]["word_error_rate"] for r in results
            if r["metrics"]["stt_wer_diagnostic"]["available"] and
            r["metrics"]["stt_wer_diagnostic"]["word_error_rate"] is not None]
    metrics["stt_wer_diagnostic"] = {"n": len(wers), "mean_word_error_rate":
                                     (sum(wers) / len(wers) if wers else None)}
    return {"trials": len(results), "metrics": metrics,
            "hard_gate_failures": sum(any(v is False for v in r["hard_gates"].values()) for r in results)}
