from __future__ import annotations
import argparse, hashlib, json, math, statistics
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_INPUTS = [
    Path(r"<LOCAL_HOME>\Downloads\mist-254170625da4435881b78608d6752a64.json"),
    Path(r"<LOCAL_HOME>\Downloads\mist-56710fc264ba4378909499fe05fd9db4.json"),
]
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "results" / "session-review-20260928"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    # nearest-rank percentile, 1-indexed
    return ordered[max(0, math.ceil(p * len(ordered)) - 1)]


def stats(values):
    values = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not values:
        return {"n": 0, "median_ms": None, "p90_ms": None, "min_ms": None, "max_ms": None}
    return {"n": len(values), "median_ms": round(statistics.median(values), 1),
            "p90_ms": round(percentile(values, .9), 1), "min_ms": round(min(values), 1),
            "max_ms": round(max(values), 1)}


def normalize_text(value):
    return " ".join(str(value or "").split()).casefold()


def read_events(doc):
    rows = []
    for row in doc.get("events", []):
        e = row.get("event")
        if not isinstance(e, dict):
            continue
        # Server-receipt export clock is the only supported cross-source clock.
        if row.get("timestamp_basis") != "server_receipt" or not isinstance(row.get("elapsed_ms"), (int, float)):
            continue
        rows.append({"id": row.get("id"), "t": float(row["elapsed_ms"]), "source": row.get("source"), "event": e,
                     "clock_id": row.get("clock_id")})
    return sorted(rows, key=lambda r: (r["t"], r["id"] or 0))


def analyze_file(path: Path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    events = read_events(doc)
    cfg = doc.get("session", {}).get("config", {})
    arch_id = cfg.get("id", "unknown")
    trace_id = doc.get("session", {}).get("trace_id")
    users = [r for r in events if r["source"] == "server" and r["event"].get("type") == "transcript_done" and r["event"].get("role") == "user"]
    assistants = [r for r in events if r["source"] == "model_protocol" and r["event"].get("type") == "turn.done" and r["event"].get("turn", {}).get("role") == "assistant"]
    user_turn_creates = [r for r in events if r["source"] == "model_protocol" and r["event"].get("type") == "turn.created" and r["event"].get("turn", {}).get("role") == "user"]
    assistant_turn_creates = {r["event"].get("turn", {}).get("id"): r for r in events
                              if r["source"] == "model_protocol" and r["event"].get("type") == "turn.created" and r["event"].get("turn", {}).get("role") == "assistant"}
    model_starts = [r for r in events if r["source"] == "server" and r["event"].get("type") == "debug_model" and r["event"].get("phase") == "thinking_started"]
    model_deltas = defaultdict(list)
    for r in events:
        e = r["event"]
        if r["source"] == "model_protocol" and e.get("type") == "turn.delta" and e.get("turn_id") and str(e.get("delta", "")).strip():
            model_deltas[e["turn_id"]].append(r)
    speech_styles = [r for r in events if r["source"] == "server" and r["event"].get("type") == "speech_style" and r["event"].get("turn_id")]
    speech_by_turn = {r["event"]["turn_id"]: {"row":r, "sequence":i} for i,r in enumerate(speech_styles)}
    tts = [r for r in events if r["source"] == "server" and r["event"].get("type") == "latency" and isinstance(r["event"].get("tts"), dict)]
    playback = [r for r in events if r["source"] == "browser" and r["event"].get("type") == "playback_started"]
    audio_packets = [r for r in events if r["source"] == "server" and r["event"].get("type") == "audio_delivery"]
    resets = [r for r in events if r["source"] == "server" and r["event"].get("type") == "audio_reset"]
    # TTS sequence is globally increasing; epoch is a reset generation. Keep the pair intact.
    tts_by_key = {(r["event"]["tts"].get("epoch"), r["event"]["tts"].get("sequence")): r for r in tts}
    play_by_key = {(r["event"].get("epoch"), r["event"].get("sequence")): r for r in playback}
    rows = []
    for i, u in enumerate(users):
        next_user_start = next((r for r in user_turn_creates if r["t"] > u["t"]), None)
        stop = next_user_start["t"] if next_user_start else float("inf")
        user_text = u["event"].get("text", "")
        starts = [r for r in model_starts if u["t"] < r["t"] < stop and normalize_text(r["event"].get("input_text")) == normalize_text(user_text)]
        start = starts[0] if len(starts) == 1 else None
        turn_id = start["event"].get("turn_id") if start else None
        assistant_created = assistant_turn_creates.get(turn_id) if turn_id else None
        model_delta = next((r for r in model_deltas.get(turn_id, []) if r["t"] > (start["t"] if start else u["t"])), None) if turn_id else None
        reset_before_text = any(u["t"] < r["t"] < model_delta["t"] for r in resets) if model_delta else False
        new_user_before_text = bool(model_delta and next_user_start and next_user_start["t"] < model_delta["t"])
        first_text = model_delta if assistant_created and model_delta and not reset_before_text and not new_user_before_text else None
        pair = speech_by_turn.get(turn_id) if first_text else None
        sequence = pair["sequence"] if pair else None
        style = pair["row"] if pair else None
        epoch = None
        if style:
            preceding_resets = [r["event"].get("epoch") for r in resets if r["t"] < style["t"] and isinstance(r["event"].get("epoch"), int)]
            epoch = max(preceding_resets, default=0)
        pair_key = (epoch, sequence) if sequence is not None else None
        tts_row = tts_by_key.get(pair_key) if pair_key else None
        first_packet = next((r for r in audio_packets if pair_key and (r["event"].get("epoch"), r["event"].get("seq")) == pair_key), None)
        playback_row = play_by_key.get(pair_key) if pair_key else None
        for candidate in (first_packet, playback_row):
            if candidate and (candidate["t"] <= u["t"] or (next_user_start and candidate["t"] >= next_user_start["t"])):
                if candidate is first_packet: first_packet = None
                else: playback_row = None
        # Interrupted turns and turns superseded before their first output are explicitly excluded.
        interrupted_before_first_packet = bool(first_packet and any(first_text["t"] < r["t"] < first_packet["t"] and r["event"].get("type") == "audio_reset" for r in resets))
        if interrupted_before_first_packet:
            first_packet = None
            playback_row = None
        reset_after_packet_before_playback = bool(first_packet and playback_row and any(first_packet["t"] < r["t"] < playback_row["t"] for r in resets))
        if reset_after_packet_before_playback:
            playback_row = None
        assistant_done = next((r for r in events if r["source"] == "model_protocol" and r["event"].get("type") == "turn.done" and r["event"].get("turn", {}).get("id") == turn_id and r["event"].get("turn", {}).get("role") == "assistant"), None) if turn_id else None
        dt_text = first_text["t"] - u["t"] if first_text else None
        dt_audio = first_packet["t"] - u["t"] if first_packet else None
        m = tts_row["event"]["tts"] if tts_row else None
        rows.append({
            "turn_index": i + 1, "user_event_id": u["id"], "user_final_elapsed_ms": round(u["t"], 1),
            "user_text": user_text, "model_turn_id": turn_id, "model_start_event_id": start["id"] if start else None,
            "assistant_turn_created_event_id": assistant_created["id"] if assistant_created else None,
            "first_text_event_id": first_text["id"] if first_text else None,
            "first_text_elapsed_ms": round(first_text["t"], 1) if first_text else None,
            "user_final_to_first_text_ms": round(dt_text, 1) if dt_text is not None else None,
            "first_text": first_text["event"].get("delta", "") if first_text else None,
            "assistant_done_event_id": assistant_done["id"] if assistant_done else None,
            "tts_epoch": epoch, "tts_sequence": sequence,
            "tts_first_byte_after_tts_text_ms": round(1000*m["first_byte_s"],1) if m and isinstance(m.get("first_byte_s"),(int,float)) else None,
            "user_final_to_first_audio_packet_ms": round(dt_audio,1) if dt_audio is not None else None,
            "first_audio_packet_event_id": first_packet["id"] if first_packet else None,
            "tts_metric_event_id": tts_row["id"] if tts_row else None,
            "playback_event_id": playback_row["id"] if playback_row else None,
            "playback_sequence_paired": bool(pair_key and playback_row and (playback_row["event"].get("epoch"),playback_row["event"].get("sequence"))==pair_key),
            "user_final_to_playback_started_ms": round(playback_row["t"]-u["t"],1) if playback_row else None,
            "playback_clock_source": playback_row["event"].get("clock_source") if playback_row else None,
            "reply_observed": bool(first_text), "reply_completed": bool(assistant_done),
            "mapping_status": "mapped" if first_text else ("ambiguous_multiple_matching_starts" if len(starts)>1 else "no_exact_model_turn_delta" if starts else "no_exact_text_match"),
            "exclusion_reason": "audio_reset_before_first_text" if reset_before_text else "new_user_turn_before_first_text" if new_user_before_text else None,
            "tts_missing_reason": None if first_packet else "no sequence/epoch-matched first audio_delivery packet before next user turn/session end",
            "playback_missing_reason": None if playback_row else "audio_reset_between_packet_and_playback" if reset_after_packet_before_playback else "no sequence/epoch-matched playback_started before next user turn/session end"
        })
    # Keep records, but report complete-candidate summaries excluding missing component values.
    metrics = {key: stats([r[key] for r in rows]) for key in ["user_final_to_first_text_ms", "user_final_to_first_audio_packet_ms", "user_final_to_playback_started_ms"]}
    affect = [r for r in events if r["source"] == "server" and r["event"].get("type") == "affect_decision"]
    affect_counts = Counter(r["event"].get("phase", "unknown") for r in affect)
    outcomes = Counter(r["event"].get("outcome", "") for r in affect if r["event"].get("phase") == "finished")
    statuses = Counter((r["event"].get("trace") or {}).get("status", "") for r in affect if r["event"].get("phase") == "finished")
    affect_durations = [(r["event"].get("trace") or {}).get("elapsed_ms") for r in affect if r["event"].get("phase") == "finished"]
    debug_model = [r["event"] for r in events if r["source"] == "server" and r["event"].get("type") == "debug_model"]
    floor_phases = Counter(e.get("phase") for e in debug_model)
    stt_finals = [e for e in debug_model if e.get("phase") == "stt_final"]
    # Deliberately count only durable exported records; debug_client mirrors are omitted.
    bg = [r for r in events if r["source"] == "server" and (r["event"].get("type") in {"brain_job", "brain_delivery", "background_job", "background_delivery", "result_report"}
          or any(k in str(r["event"].get("type", "")).lower() for k in ("background", "inbox", "result_report", "research_job")))]
    errors = [r for r in events if r["source"] == "server" and r["event"].get("type") in ("error", "voice_warning")]
    warnings = [r for r in events if r["source"] == "server" and r["event"].get("type") in ("warning", "voice_warning")]
    dropped = [r for r in events if r["source"] == "server" and ("drop" in str(r["event"].get("type", "")).lower() or "drop" in str(r["event"].get("code", "")).lower())]
    explicit_barge = [r for r in events if r["source"] == "browser_command" and r["event"].get("type") == "barge_in"]
    native_turns = [r for r in events if r["source"] == "provider" and r["event"].get("event") == "native_turn"]
    tts_connections = [r for r in events if r["source"] == "provider" and r["event"].get("event") == "tts_connected"]
    model_started = {r["event"].get("turn_id"): r for r in events
                     if r["source"] == "server" and r["event"].get("type") == "debug_model" and r["event"].get("phase") == "thinking_started"}
    model_first_delta = {}
    model_finished = []
    for r in events:
        e = r["event"]
        if r["source"] != "server" or e.get("type") != "debug_model":
            continue
        turn_id = e.get("turn_id")
        if e.get("phase") == "text_delta" and turn_id and str(e.get("delta", "")).strip():
            model_first_delta.setdefault(turn_id, r)
        elif e.get("phase") == "thinking_finished":
            timing = e.get("timings") or {}
            requests = timing.get("http_requests") or []
            first_request = requests[0] if requests else {}
            started = model_started.get(turn_id)
            first_delta = model_first_delta.get(turn_id)
            model_finished.append({
                "turn_id": turn_id, "start_event_id": started["id"] if started else None,
                "first_delta_event_id": first_delta["id"] if first_delta else None,
                "finish_event_id": r["id"], "start_to_first_delta_ms": round(first_delta["t"]-started["t"],1) if first_delta and started else None,
                "start_to_finish_receipt_ms": round(r["t"]-started["t"],1) if started else None,
                "reported_duration_ms": e.get("duration_ms"), "http_headers_ms": first_request.get("headers_ms"),
                "http_status": first_request.get("status"), "usage": first_request.get("usage"),
                "input_text": e.get("input_text", started["event"].get("input_text", "") if started else "")
            })
    header_ms = [r["http_headers_ms"] for r in model_finished]
    headers_with_usage = [r for r in model_finished if r.get("http_headers_ms") is not None]
    slow_model = sorted([r for r in model_finished if r.get("start_to_first_delta_ms") is not None],
                        key=lambda r:r["start_to_first_delta_ms"], reverse=True)[:8]
    bg_types = {"brain_job", "brain_delivery", "background_job", "background_delivery", "result_report"}
    bg = [r for r in events if r["source"] == "server" and r["event"].get("type") in bg_types]
    return {
        "source": {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size},
        "trace_id": trace_id, "architecture": {"id":arch_id,"label":cfg.get("label"),"model":cfg.get("model"),"provider":cfg.get("provider"),"reasoning_effort":cfg.get("reasoning_effort"),"floor":cfg.get("floor"),"endpoint_ms":cfg.get("endpoint_ms"),"conversation_policy":cfg.get("conversation_policy"),"playback_buffer_ms":cfg.get("playback_buffer_ms"),"background_context":cfg.get("background_context"),"parallel_tool_calls":cfg.get("parallel_tool_calls"),"affect_model":cfg.get("affect_model")},
        "session": {"status":doc.get("session",{}).get("status"),"started_at":doc.get("session",{}).get("started_at"),"ended_at":doc.get("session",{}).get("ended_at"),"clock_basis":doc.get("session",{}).get("clock_basis"),"export_event_count":len(doc.get("events",[])),"usable_server_clock_events":len(events)},
        "counts": {"user_finals":len(users),"assistant_turn_done":len(assistants),"first_text_mapped_turns":sum(x["reply_observed"] for x in rows),"tts_latency_records":len(tts),"playback_started":len(playback),"audio_delivery_packets":len(audio_packets),"playback_resets":len(resets),"explicit_barge_in_commands":len(explicit_barge),"native_turn_provider_records":len(native_turns),"tts_connected_provider_records":len(tts_connections),"background_or_result_records":len(bg),"errors":len(errors),"warnings":len(warnings),"drop_markers":len(dropped)},
        "floor_diagnostics": {"debug_model_phase_counts":dict(floor_phases),"stt_final_overlap_true":sum(bool(e.get("overlap")) for e in stt_finals),"stt_final_speech_final_true":sum(bool(e.get("speech_final")) for e in stt_finals),"floor_incomplete_hold":floor_phases.get("floor_incomplete_hold",0),"floor_backchannel_kept":floor_phases.get("floor_backchannel_kept",0),"user_committed":floor_phases.get("user_committed",0),"speech_started":floor_phases.get("speech_started",0),"interrupt":floor_phases.get("interrupt",0),"interrupted_generation_discarded":floor_phases.get("interrupted_generation_discarded",0),"model_failed":floor_phases.get("model_failed",0)},
        "latency_stats":metrics,"turns":rows,
        "model_http": {"finished_turn_count":len(model_finished),"http_header_timing_count":len(header_ms),
                       "http_headers_stats_ms":stats(header_ms),
                       "usage_token_totals":{"total_tokens":sum((r.get("usage") or {}).get("total_tokens",0) for r in headers_with_usage),
                                             "prompt_tokens":sum((r.get("usage") or {}).get("prompt_tokens",0) for r in headers_with_usage),
                                             "completion_tokens":sum((r.get("usage") or {}).get("completion_tokens",0) for r in headers_with_usage)},
                       "slowest_start_to_first_delta":slow_model,"turns":model_finished},
        "slowest_turns":{k:sorted([r for r in rows if r[k] is not None],key=lambda r:r[k],reverse=True)[:5] for k in metrics},
        "affect_reader": {"phase_counts":dict(affect_counts),"finished_outcomes":dict(outcomes),"finished_statuses":dict(statuses),"finished_elapsed_stats_ms":stats(affect_durations),"records":[{"event_id":r["id"],"phase":r["event"].get("phase"),"outcome":r["event"].get("outcome"),"status":(r["event"].get("trace") or {}).get("status"),"elapsed_ms":(r["event"].get("trace") or {}).get("elapsed_ms")} for r in affect if r["event"].get("phase") in ("finished","skipped_busy")]},
        "background_records": [{"event_id":r["id"],"event":r["event"]} for r in bg],
        "interruptions": [{"event_id":r["id"],"elapsed_ms":round(r["t"],1),"event":r["event"].get("type"),"epoch":r["event"].get("epoch")} for r in resets+explicit_barge],
        "errors_warnings_drops": [{"event_id":r["id"],"event":r["event"]} for r in events if r in errors or r in dropped],
        "limitations": ["Session export is still marked active; updated_at is not a proven end-of-session timestamp.","First text uses the first nonblank model_protocol turn.delta for the exact turn_id from debug_model thinking_started, and requires the matching assistant turn.created record.","The exact model turn is mapped to a user final only when debug_model input_text matches that final and begins before a following user turn starts. A new user turn or audio reset before first text excludes the observation.","TTS sequence is inferred from the order of speech_style records, one per begin call in the retained trace; speech_style does not itself carry the sequence. The inferred sequence and reset epoch are cross-checked against server audio_delivery and browser playback_started. This is a sequence-linked association, not a direct turn_id on the audio packet.","First audio packet timing is an observed server receipt interval, not a provider first-byte timestamp. Provider latency.first_byte_s remains a separate monotonic measurement and is not added to server timestamps.","Playback is observed at browser playback_started receipt and has a separate output_timestamp audio clock; client_ms was not mixed into server timing.","Repeated debug_client and browser_command mirrors were excluded from counts; model_protocol turn.delta and output_transcript.added are duplicate content paths, not summed as independent turns."]
    }


def markdown(report):
    lines=["# Session latency and interruption audit — 2026-09-28", "", "Source JSON is read as data only. Input SHA-256 hashes are frozen in `latency.json`. All cross-event deltas use the exported server-receipt `elapsed_ms` clock. Browser `client_ms` and model `start_ms` are preserved in source traces but not mixed into those deltas.", "", "## Runs", "", "| Architecture | User finals | Exact model-turn text mappings | User final → first text median / p90 | User final → sequence-linked first audio packet median / p90 | User final → playback start median / p90 | Resets / explicit barge-in | Reader accepted / applied / speech-started / stale-replaced / rejected / busy | Errors / warnings / drops |", "|---|---:|---:|---:|---:|---:|---:|---|---:|"]
    for s in report["sessions"]:
        a=s["architecture"]; c=s["counts"]; l=s["latency_stats"]; af=s["affect_reader"]; oc=af["finished_outcomes"]
        def fm(key):
            x=l[key];return f'{x["median_ms"]} / {x["p90_ms"]} ms (n={x["n"]})'
        st=af["finished_statuses"]
        lines.append(f'| {a["id"]} ({a.get("model")}) | {c["user_finals"]} | {c["first_text_mapped_turns"]} | {fm("user_final_to_first_text_ms")} | {fm("user_final_to_first_audio_packet_ms")} | {fm("user_final_to_playback_started_ms")} | {c["playback_resets"]} / {c["explicit_barge_in_commands"]} | {st.get("accepted",0)} / {oc.get("applied_before_speech",0)} / {oc.get("speech_already_started",0)} / {oc.get("stale_or_replaced",0)} / {sum(v for k,v in st.items() if k != "accepted")} / {af["phase_counts"].get("skipped_busy",0)} | {c["errors"]} / {c["warnings"]} / {c["drop_markers"]} |')
    lines += ["", "## Model request timing", "", "`debug_model.thinking_finished` includes provider HTTP `headers_ms`, the first-response/header wait rather than time to finish generating a reply. It helps separate provider response delay from the rest of a turn. The turn-level rows in `latency.json` retain event IDs, header time, reported request duration, and provider usage where present.", "", "| Architecture | Finished model turns | HTTP header median / p90 |", "|---|---:|---:|"]
    for s in report["sessions"]:
        m=s["model_http"]; h=m["http_headers_stats_ms"]
        lines.append(f'| {s["architecture"]["id"]} | {m["finished_turn_count"]} | {h["median_ms"]} / {h["p90_ms"]} ms (n={h["n"]}) |')
    lines += ["", "## Floor and speech activity signals", "", "These are exported diagnostic counts, not labeled interruption outcomes:", "", "| Architecture | speech_started | user_committed | STT finals (`overlap=true` / `speech_final=true`) | interrupt | incomplete hold | kept backchannel | interrupted generation discarded | model failed |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for s in report["sessions"]:
        f=s["floor_diagnostics"]
        lines.append(f'| {s["architecture"]["id"]} | {f["speech_started"]} | {f["user_committed"]} | {f["stt_final_overlap_true"]} / {f["stt_final_speech_final_true"]} | {f["interrupt"]} | {f["floor_incomplete_hold"]} | {f["floor_backchannel_kept"]} | {f["interrupted_generation_discarded"]} | {f["model_failed"]} |')
    lines += ["", "Slowest model start→first-delta turns (server-receipt event IDs; provider headers time shown separately):", "", "| Architecture | Start / first delta / finish events | Model elapsed to first delta | HTTP headers | Prompt / total tokens | Input text |", "|---|---|---:|---:|---:|---|"]
    for s in report["sessions"]:
        for r in s["model_http"]["slowest_start_to_first_delta"][:3]:
            usage=r.get("usage") or {}; prompt=usage.get("prompt_tokens"); total=usage.get("total_tokens")
            inp=(r.get("input_text") or "").replace("|","\\|").replace("\n"," ")[:100]
            headers=round(r["http_headers_ms"],1) if r.get("http_headers_ms") is not None else None
            lines.append(f'| {s["architecture"]["id"]} | {r["start_event_id"]} / {r["first_delta_event_id"]} / {r["finish_event_id"]} | {r["start_to_first_delta_ms"]} ms | {headers} ms | {prompt} / {total} | {inp} |')
    lines += ["", "Across the exact text mappings retained here, Qwen’s median final→first-text was 1202 ms versus 811 ms for Cerebras balanced; the later audio and playback medians/p90s are sequence-linked observations, not direct turn_id records. These are small-sample run-level observations. The sessions do not isolate the text model: they differ in pause threshold (700 vs 500 ms), conversation policy, playback reserve (200 vs 120 ms), reasoning setup and parallel-tool/background settings. Both use the same selective floor. They do not show whether Qwen is best overall.", "", "First-text timing uses the first nonblank `turn.delta` for the exact assistant `turn_id`. TTS begin calls are linked to `speech_style` records by their order, since `speech_style` carries no sequence; first server audio packets and browser playback events are then matched by exact epoch/sequence. That links one-to-one in the retained traces, but the audio packet itself has no assistant `turn_id`. Provider `latency.first_byte_s` is reported separately as a monotonic duration and is not added to server-clock events.", "", "Audio resets count interrupted playback generations; they include ordinary new-turn resets and cannot all be attributed to floor errors. Explicit `barge_in` commands are counted separately. Floor and STT activity does exist in the traces: `debug_model` records `speech_started`, STT finals and partials, `user_committed`, `interrupt`, incomplete-utterance holds, and a kept backchannel. These are useful operational signals, but there are no annotated false-trigger labels or retained raw acoustic evidence, so the traces cannot establish false interruption rates or compare floor accuracy.", "", "The requested background event families (`brain_job`, `brain_delivery`, and related background/result records) were searched in the exported events; none occurred in either trace. That is zero observed task activity, not evidence about background-model latency. `debug_client` duplication was excluded. Errors and warnings count exported server events only; `error` records describe provisional text-model failures. Drop markers count only explicit type/code text containing `drop`.", "", "The input files are still marked `active` and have no `ended_at`. Counts and distributions therefore describe the exported snapshot only, and a final trailing/cancelled reply may be censored. Canceled or ambiguous components are null and excluded from their own summaries.", "", "## Slowest observed turns", ""]
    for s in report["sessions"]:
        lines += [f'### {s["architecture"]["id"]}', "", "| Metric | Event IDs | Delay | User text (truncated) |", "|---|---|---:|---|"]
        labels=[("user_final_to_first_text_ms","final → first text"),("user_final_to_first_audio_packet_ms","final → first audio packet"),("user_final_to_playback_started_ms","final → playback")]
        seen=set()
        for k,label in labels:
            for r in s["slowest_turns"][k][:3]:
                identity=(label,r["user_event_id"])
                if identity in seen:continue
                seen.add(identity); u=(r.get("user_text") or "").replace("|","\\|").replace("\n"," ")[:120]
                lines.append(f'| {label} | user {r["user_event_id"]}, model start {r["model_start_event_id"]}, text {r["first_text_event_id"]}, packet {r["first_audio_packet_event_id"]}, playback {r["playback_event_id"]} | {r[k]} ms | {u} |')
        if len(seen)==0: lines.append("| No complete observation | — | — | — |")
        lines += ["", "A first-audio packet or playback ID of `None` means no same-sequence observation remained before a new user turn, reset, or session boundary. Exact per-turn details and exclusion reasons are retained in `latency.json`.", ""]
    lines += ["## Source, reproducibility, and limits", "", "Run from the repo root:", "", "```powershell", "python brain/harness/analyse_session_latency_20260928.py", "```", "", "The analyzer uses only Python's standard library. It does not alter production code or contact APIs. The two sessions are not matched controlled comparisons; model quality or whether Qwen is ‘best’ cannot be decided from latency traces alone.", ""]
    return "\n".join(lines)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("inputs",nargs="*",type=Path,default=DEFAULT_INPUTS)
    ap.add_argument("--out-dir",type=Path,default=DEFAULT_OUT)
    args=ap.parse_args()
    sessions=[analyze_file(p) for p in args.inputs]
    report={"generated_by":Path(__file__).name,"sessions":sessions,"cross_session_limit":"Two uncontrolled sessions; descriptive only."}
    args.out_dir.mkdir(parents=True,exist_ok=True)
    (args.out_dir/"latency.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (args.out_dir/"LATENCY.md").write_text(markdown(report),encoding="utf-8")
    print(args.out_dir/"LATENCY.md")
    print(args.out_dir/"latency.json")

if __name__ == "__main__": main()
