"""Publish a local, allowlisted view of recorded software voice experiments."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import importlib.util
import json
import math
from pathlib import Path
import random
import re
import shutil
import zipfile


BATCHES = ("native_full", "native_rerun", "native_capture_fix", "cascade_smoke", "cascade_selective", "cascade_cancel_all", "cascade_luna", "cascade_endpoint700", "native_browser")
SMOKE_BATCHES = frozenset(("native_browser", "cascade_smoke"))
CONTINUOUS_CAPTURE_VERSION = "2026-09-24-continuous-recorder-v1"
CONTINUOUS_CAPTURE_VERSIONS = frozenset((CONTINUOUS_CAPTURE_VERSION, "2026-09-24-continuous-recorder-v2"))
CONFIG_FIELDS = ("backend", "model", "provider", "floor", "endpoint_ms", "background_model", "reasoning", "speech_backend", "voice_id")
TRACE_FIELDS = ("schema_version", "capture_version", "recording_clock", "media_alignment", "case_id", "status", "started_at", "ended_at", "duration_ms", "timing_kind", "events", "inputs", "errors", "recording", "environment", "video_capture", "observation_end_ms", "remaining", "metrics")


def read_json(path: Path, default=None):
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def clean(value):
    """Strip credential-like keys and bulky inline recordings from exported traces."""
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()
                if not any(word in key.lower() for word in ("token", "secret", "authorization", "api_key", "cookie", "pairing", "password", "session_id", "thread_id"))
                and key not in ("pcm", "pcm16", "base64", "png", "audio_base64", "sdp")}
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, str) and value.startswith("data:"):
        return "[inline media omitted]"
    return value


def transcript(events):
    turns, pending = [], {}
    for event in events:
        kind, role = event.get("type"), event.get("role", "assistant")
        if kind == "transcript_delta":
            if pending and role not in pending:
                for old_role, text in pending.items():
                    turns.append({"role": old_role, "text": text, "partial": True})
                pending = {}
            pending[role] = pending.get(role, "") + str(event.get("text", ""))
        elif kind == "transcript_done":
            text = str(event.get("text") or pending.get(role, ""))
            pending.pop(role, None)
            if text:
                turns.append({"role": role, "text": text, "partial": False})
    turns.extend({"role": role, "text": text, "partial": True} for role, text in pending.items() if text)
    return turns


def copy_file(source: Path, out: Path, relative: str):
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)
    return relative


def endpoint_display(batch: Path, config: dict):
    if config.get("backend") == "native":
        return {"label": "N/A", "source": "native provider controls endpointing"}
    if type(config.get("endpoint_ms")) is int:
        return {"label": str(config["endpoint_ms"]), "source": "recorded configuration"}
    frozen = batch / "sources/brain/benchmarks/naturalness/cascade_voice.py"
    if config.get("backend") == "cascade" and frozen.is_file():
        code = frozen.read_text(encoding="utf-8")
        if re.search(r'''["']endpointing["']\s*:\s*300\b''', code):
            return {"label": "300 (original default)", "source": "frozen adapter constant", "source_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest()}
    return {"label": "not recorded", "source": "unavailable"}


def media_validity(browser_path: Path, browser: dict):
    """Require matching recorded bytes and an explicit offline clock audit."""
    directory = browser_path.parent
    audit_path = directory / "audio_capture_audit/audit.json"
    if not audit_path.is_file():
        audit_path = directory / "audio_capture_audit.json"
    audit = read_json(audit_path, {})
    current = browser.get("capture_version") in CONTINUOUS_CAPTURE_VERSIONS
    reasons = []
    if not current:
        reasons.append("Recording omitted silent time; timing and AV sync not validated.")
    if audit.get("status") != "audited" or audit.get("failures"):
        reasons.append("A successful media-clock audit is not available.")
    if audit.get("source_browser_sha256") != hashlib.sha256(browser_path.read_bytes()).hexdigest():
        reasons.append("Media audit does not identify the current browser trace.")
    audio = directory / "browser-output.webm"
    audio_hash = hashlib.sha256(audio.read_bytes()).hexdigest() if audio.is_file() else None
    if not audio_hash or audit.get("source_audio_sha256") != audio_hash:
        reasons.append("Media audit does not identify the current output audio.")
    streams = audit.get("media_clock_audit", {}).get("streams", [])
    audio_streams = [row for row in streams if row.get("file") == "browser-output.webm" and row.get("stream_kind") == "audio"]
    audio_clock = bool(audio_streams) and all(row.get("sha256") == audio_hash and row.get("browser_clock_alignment") == "approximately_consistent" for row in audio_streams)
    if not audio_clock:
        reasons.append("Output audio timeline is not approximately consistent with the browser clock.")
    audio_ok = current and not reasons
    video = directory / "face-output.webm"
    video_hash = hashlib.sha256(video.read_bytes()).hexdigest() if video.is_file() else None
    video_streams = [row for row in streams if row.get("file") == "face-output.webm"]
    video_ok = audio_ok and bool(video_hash) and {row.get("stream_kind") for row in video_streams} == {"audio", "video"} and all(row.get("sha256") == video_hash and row.get("browser_clock_alignment") == "approximately_consistent" for row in video_streams)
    def reply_seek(rows, verified):
        if not verified:
            return None
        points = [row.get("first_active_frame_pts_ms") for row in rows if row.get("stream_kind") == "audio"]
        points = [point for point in points if type(point) in (int, float) and math.isfinite(point) and point >= 0]
        return max(0.0, min(points) / 1000 - 0.25) if points else None
    return {"capture_version": browser.get("capture_version", "legacy"), "continuous_recorder": current,
            "audio_timeline_validated": audio_ok, "video_stream_timelines_validated": bool(video_ok),
            "audio_reply_seek_s": reply_seek(audio_streams, audio_ok), "video_reply_seek_s": reply_seek(video_streams, video_ok),
            "mouth_phoneme_sync": "unverified", "av_sync": "unverified", "reasons": reasons,
            "audit_status": audit.get("status", "missing")}, audit


def fixture_pack(source: Path, out: Path):
    fixture_dir = source / ("fixtures_v2" if (source / "fixtures_v2/manifest.json").is_file() else "fixtures")
    manifest = read_json(fixture_dir / "manifest.json")
    if not manifest:
        return None, []
    files = {}
    for asset in manifest.get("assets", []):
        name = asset.get("file", "")
        if Path(name).name != name or not name.lower().endswith(".wav"):
            continue
        path = fixture_dir / "audio" / name
        if path.is_file():
            files[name] = path
    for fixture in manifest.get("fixtures", []):
        for step in fixture.get("steps", []):
            name = step.get("file", "")
            if Path(name).name == name and name.lower().endswith(".wav"):
                path = fixture_dir / "audio" / name
                if path.is_file():
                    files[name] = path
    archive = out / "voice-fixtures.zip"
    extension = manifest.get("extension", {})
    provenance = {"version": manifest.get("version"), "fixture_count": len(manifest.get("fixtures", [])),
                  "original_suite_audio_fixtures": extension.get("original_suite_audio_fixtures", len(manifest.get("fixtures", []))),
                  "supplemental_controls": extension.get("supplemental_controls", 0),
                  "manifest_sha256": hashlib.sha256((fixture_dir / "manifest.json").read_bytes()).hexdigest(),
                  "source_manifest": manifest.get("source_manifest"), "extension": extension}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as target:
        target.write(fixture_dir / "manifest.json", "manifest.json")
        info = zipfile.ZipInfo("provenance.json", date_time=(2000, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        target.writestr(info, json.dumps(provenance, ensure_ascii=True, indent=2))
        for name, path in sorted(files.items()):
            target.write(path, "audio/" + name)
    return {**provenance, "path": archive.name, "audio_files": len(files), "bytes": archive.stat().st_size,
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}, manifest.get("fixtures", [])


def build_report(source: Path, out: Path, metrics: dict | None = None, notes: dict | None = None):
    source, out = Path(source), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if metrics is None:
        analyzer_path = Path(__file__).with_name("e2e_metrics.py")
        if analyzer_path.is_file():
            spec = importlib.util.spec_from_file_location("mist_e2e_metrics", analyzer_path)
            analyzer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(analyzer)
            metrics = analyzer.build_report({name: source / name for name in BATCHES})
    report = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
              "scope": "Software audio replay and browser output, not phone acoustics or human conversation.",
              "human_ratings": "unrated", "cases": [], "batches": [], "controlled": [],
              "metrics": metrics, "notes": notes or {}}
    old_clock_audit = source / "media_clock_old_capture_audit.json"
    if old_clock_audit.is_file():
        report["old_recording_clock_audit"] = copy_file(old_clock_audit, out, "docs/media_clock_old_capture_audit.json")
    overlay_manifest = read_json(source / "fixtures_v2/manifest.json", {})
    overlays = {fixture["id"]: fixture for fixture in overlay_manifest.get("fixtures", [])}
    input_directory = source / ("fixtures_v2" if overlay_manifest else "fixtures") / "audio"
    input_manifest = overlay_manifest or read_json(source / "fixtures/manifest.json", {})
    allowed_inputs = {step["file"] for fixture in input_manifest.get("fixtures", []) for step in fixture.get("steps", [])
                      if step.get("file") and Path(step["file"]).name == step["file"] and step["file"].lower().endswith(".wav")}
    report["fixture_annotations"] = {"version": overlay_manifest.get("version"),
                                     "mode": "Retrospective validity annotations only; original fixtures and raw traces are unchanged."}
    report["documents"] = []
    for document, label in ((Path(__file__).with_name("E2E_RUNBOOK.md"), "Runbook"),
                            (source / "FIXTURE_VALIDITY_AUDIT_20260924.md", "Fixture validity audit")):
        if document.is_file():
            relative = copy_file(document, out, "docs/" + document.name)
            report["documents"].append({"label": label, "path": relative})
    for batch_name in BATCHES:
        batch = source / batch_name
        observed = 0
        for browser_path in sorted(batch.glob("*/browser.json")):
            browser = read_json(browser_path)
            fixture = read_json(browser_path.parent / "fixture.json", browser.get("fixture", {}))
            config = read_json(browser_path.parent / "configuration.json", {})
            case_id = browser.get("case_id", fixture.get("id", browser_path.parent.name))
            entry_id = hashlib.sha256((batch_name + "/" + browser_path.parent.name).encode()).hexdigest()[:16]
            relative = "cases/" + entry_id
            trace = clean({key: browser[key] for key in TRACE_FIELDS if key in browser})
            write_json(out / relative / "browser.json", trace)
            write_json(out / relative / "fixture.json", clean(fixture))
            public_config = {key: config[key] for key in CONFIG_FIELDS if key in config}
            write_json(out / relative / "configuration.json", public_config)
            events = browser.get("events", [])
            remaining = browser.get("remaining", {})
            truncation = bool(remaining.get("playback_active") or remaining.get("queue_ms", 0) > 0 or remaining.get("background_jobs"))
            entry = {"id": entry_id, "batch": batch_name, "case_id": case_id,
                     "batch_role": "initial instrument smoke" if batch_name in SMOKE_BATCHES else "main experiment",
                     "endpoint_display": endpoint_display(batch, config),
                     "title": fixture.get("title", case_id), "status": browser.get("status", "unknown"),
                     "config": public_config, "input": [{"type": step.get("type"), "text": step.get("text") or " ".join(str(x.get("text", "")) for x in step.get("segments", [])),
                                                       "trigger": step.get("trigger"), "delay_ms": step.get("delay_ms"), "role": step.get("role")}
                                                      for step in fixture.get("steps", [])],
                     "transcript": transcript(events), "errors": clean(browser.get("errors", [])),
                     "truncated_at_capture": truncation, "remaining": clean(remaining),
                     "event_counts": dict(Counter(e.get("type", "unknown") for e in events)),
                     "browser_metrics": clean(browser.get("metrics", {})),
                     "conditions_uncontrolled": fixture.get("conditions_uncontrolled", []),
                     "fixture_status": fixture.get("fixture_status", "unknown"),
                     "rubric": fixture.get("rubric", []), "trace": relative + "/browser.json",
                     "fixture": relative + "/fixture.json", "human_ratings": "unrated"}
            entry["media_review"], audit = media_validity(browser_path, browser)
            if audit:
                audit_link = relative + "/audio_capture_audit.json"
                write_json(out / audit_link, clean(audit))
                entry["media_review"]["audit"] = audit_link
            for rendered_step, source_step in zip(entry["input"], fixture.get("steps", [])):
                input_name = source_step.get("file")
                input_path = input_directory / input_name if input_name in allowed_inputs else None
                if input_path and input_path.is_file():
                    rendered_step["audio"] = copy_file(input_path, out, "inputs/" + input_name)
                    rendered_step["audio_sha256"] = hashlib.sha256(input_path.read_bytes()).hexdigest()
            if case_id in overlays:
                overlay = overlays[case_id]
                entry["conditions_uncontrolled"] = list(dict.fromkeys(fixture.get("conditions_uncontrolled", []) + overlay.get("conditions_uncontrolled", [])))
                entry["retrospective_annotation"] = {"version": overlay_manifest.get("version"),
                    "source": "fixtures_v2/manifest.json", "raw_evidence_modified": False,
                    "coverage_role": overlay.get("coverage_role", "original_suite_case")}
            matching = [capture for capture in (metrics or {}).get("groups", {}).get(batch_name, {}).get("captures", [])
                        if capture.get("capture_id") == browser_path.parent.name]
            if matching:
                entry["analysis"] = clean({key: matching[0][key] for key in ("first_response", "capture", "face", "issues", "file_issues") if key in matching[0]})
                entry["truncated_at_capture"] = matching[0].get("capture", {}).get("truncated", truncation)
            for name, key in (("browser-output.webm", "audio"), ("face-output.webm", "video")):
                path = browser_path.parent / name
                if path.is_file():
                    entry[key] = copy_file(path, out, relative + "/" + name)
            report["cases"].append(entry)
            observed += 1
        endpoint_labels = sorted({entry["endpoint_display"]["label"] for entry in report["cases"] if entry["batch"] == batch_name})
        if not endpoint_labels:
            endpoint_labels = [endpoint_display(batch, read_json(batch / "manifest.json", {}))["label"]]
        report["batches"].append({"batch": batch_name, "role": "initial instrument smoke" if batch_name in SMOKE_BATCHES else "main experiment", "endpoint_ms_display": ", ".join(endpoint_labels), "recorded_cases": observed, "state": "recordings present" if observed else "no browser results yet"})
    for name in ("fixtures_luna", "fixtures_cerebras", "memory_prefill_luna", "memory_prefill_cerebras"):
        summary = read_json(source / name / "summary.json")
        if summary:
            snapshot = clean(summary)
            write_json(out / "controlled" / (name + ".json"), snapshot)
            report["controlled"].append({"run": name, "sample_count": summary.get("sample_count"), "completed_samples": summary.get("completed_samples"),
                                        "status_counts": summary.get("status_counts", {}), "checks": summary.get("checks", {}),
                                        "outcomes": summary.get("outcomes", {}), "metrics": summary.get("metrics", {}),
                                        "config": summary.get("manifest", {}).get("config", {}),
                                        "memory_context": summary.get("manifest", {}).get("config", {}).get("memory_context", "unspecified"),
                                        "evidence_scope": "Controlled text fixtures; no audio timing or human naturalness rating.",
                                        "report": "controlled/" + name + ".json"})
    report["async_components"] = {label: read_json(source / name / "summary.json") for label, name in (("before", "async_components"), ("after", "async_components_fixed"))}
    report["research"] = []
    for path in sorted((source / "research").glob("*/review.json")):
        data = read_json(path)
        safe = clean({key: data[key] for key in ("worker", "requested_model", "focus", "status", "scope", "response", "proposal", "errors") if key in data})
        relative = "research/" + path.parent.name + ".json"
        write_json(out / relative, safe)
        report["research"].append({"worker": path.parent.name, "status": data.get("status"), "report": relative})
    report["fixture_pack"], report["fixtures"] = fixture_pack(source, out)
    # A separate page gives listeners no batch or model identities. Keep report.json away from blind reviewers.
    blind_cases = []
    for entry in report["cases"]:
        if not entry.get("audio") or entry["batch"] in SMOKE_BATCHES or not entry["media_review"]["audio_timeline_validated"]:
            continue
        verified_video = entry.get("video") if entry["media_review"]["video_stream_timelines_validated"] else None
        blind_cases.append({"clip_id": entry["id"], "audio": entry["audio"], "video": verified_video,
                            "audio_reply_seek_s": entry["media_review"]["audio_reply_seek_s"],
                            "video_reply_seek_s": entry["media_review"]["video_reply_seek_s"],
                            "audio_sha256": hashlib.sha256((out / entry["audio"]).read_bytes()).hexdigest(),
                            "video_sha256": hashlib.sha256((out / verified_video).read_bytes()).hexdigest() if verified_video else None,
                            "input": entry["input"], "conditions_uncontrolled": entry["conditions_uncontrolled"],
                            "truncated": entry["truncated_at_capture"], "errors": bool(entry["errors"])})
    random.Random(20260924).shuffle(blind_cases)
    report["listening_eligibility"] = {"eligible_clips": len(blind_cases),
        "excluded_from_blind": len(report["cases"]) - len(blind_cases),
        "rule": "Continuous recorder version, matching browser/audio hashes and an approximately consistent offline audio-clock audit; initial smoke excluded.",
        "mouth_phoneme_sync": "unverified", "av_sync": "unverified"}
    blind = {"version": 1, "clips": blind_cases}
    blind["pack_sha256"] = hashlib.sha256(json.dumps(blind, sort_keys=True).encode()).hexdigest()
    write_json(out / "report.json", report)
    (out / "index.html").write_text(render_report(report), encoding="utf-8")
    (out / "listen.html").write_text(BLIND_PAGE.replace("__DATA__", safe_json(blind)), encoding="utf-8")
    return {"output": str(out), "recorded_cases": len(report["cases"]), "listening_clips": len(blind_cases), "fixture_pack": report["fixture_pack"]}


def safe_json(value):
    return json.dumps(value, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def esc(value):
    return html.escape(str(value), quote=True)


STYLE = """<style>:root{font:15px/1.55 system-ui,sans-serif;color:#243a35;background:#f6f5f0}body{max-width:1200px;margin:auto;padding:24px}h1{font-size:23px}h2{font-size:19px;margin-top:32px}h3{font-size:16px;margin:0 0 10px}a{color:#126552}button,select,textarea{font:inherit;border:1px solid #bacac1;background:white;border-radius:6px;padding:7px}button{cursor:pointer}header,.bar{display:flex;gap:18px;align-items:center;flex-wrap:wrap}header{justify-content:space-between;border-bottom:1px solid #ccd6cf}table{width:100%;border-collapse:collapse;background:white;font-size:13px}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #e1e5df;padding:9px}article,.box{background:white;border:1px solid #d6ded7;border-radius:10px;padding:18px;margin:14px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.small{font-size:13px;color:#61756b}.flag{color:#994d22}.tag{background:#e4ebe3;padding:2px 7px;border-radius:4px;font-size:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.5 monospace;max-height:360px;overflow:auto}video{width:100%;max-height:300px;background:#102022;border-radius:8px}audio{width:100%}p{overflow-wrap:anywhere}.turn{border-left:2px solid #bccdc2;padding-left:12px;white-space:pre-wrap}summary{cursor:pointer}textarea{width:100%;min-height:70px}.rating{display:flex;justify-content:space-between;gap:15px;margin:10px 0}.empty{color:#65776d} @media(max-width:760px){body{padding:14px}.grid{grid-template-columns:1fr}table{display:block;overflow:auto}}</style>"""

REPLY_PLAYBACK_JS = '''function playReply(media,start,button){
 if(!media||!Number.isFinite(start)||start<0)return;
 const original=button.textContent;button.disabled=true;
 const fail=()=>{button.disabled=false;button.textContent='Use the player controls';media.removeEventListener('loadedmetadata',ready)};
 const ready=()=>{media.removeEventListener('error',fail);button.disabled=false;button.textContent=original;
  try{media.currentTime=Number.isFinite(media.duration)?Math.min(start,Math.max(0,media.duration-.05)):start;media.play().catch(fail)}catch(_){fail()}};
 if(media.readyState>=1)ready();else{media.addEventListener('loadedmetadata',ready,{once:true});media.addEventListener('error',fail,{once:true});media.load()}
}
document.addEventListener('play',event=>{for(const media of document.querySelectorAll('audio,video'))if(media!==event.target)media.pause()},true);'''


def render_report(report):
    eligibility = report.get("listening_eligibility", {})
    main_trials = sum(entry.get("batch") not in SMOKE_BATCHES for entry in report.get("cases", []))
    h = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>MIST voice tests</title>', STYLE,
         '<header><h1>Voice tests</h1><div class="bar"><a href="#recordings">Recordings</a><a href="listen.html">Blind listening</a><a href="report.json">Data</a></div></header>',
         '<p><strong>' + esc(len(report.get("fixtures", []))) + ' inputs · ' + esc(main_trials) + ' main trials · ' + esc(eligibility.get("eligible_clips", 0)) + ' audited listening clips</strong></p>',
         '<p class="small">Synthetic software replay. Human quality remains unrated.</p>']
    download_links = []
    if report.get("fixture_pack"):
        pack = report["fixture_pack"]
        download_links.append(f'<a href="{esc(pack["path"])}">Input pack ({pack["bytes"]/1024/1024:.1f} MB)</a>')
    download_links.extend(f'<a download href="{esc(row["path"])}">{esc(row["label"])}</a>' for row in report.get("documents", []))
    if download_links:
        h.append('<p>' + ' · '.join(download_links) + '</p>')
    h.append('<details class="box"><summary>How to read these results</summary>')
    h.append('<p class="small">Synthetic input, recorded browser speech and the production face renderer. Software timestamps do not measure what reaches your ears on a phone. Listening scores saved in your browser become review evidence only when a person downloads and reviews them.</p>')
    h.append('<p class="small">Coverage is limited to the recorded cases below. Synthetic replay does not establish phone echo control or whether history contains only the words actually heard. Reruns are kept separate from the original failures.</p>')
    h.append('<p class="flag">Older recordings omitted silent time. Their pacing and AV sync are not validated. Browser event timestamps remain separate latency evidence. Blind listening only includes continuous recordings whose media-clock audit matches the captured files.</p>')
    h.append('<p class="small">Matching media clocks still do not establish mouth-to-phoneme synchronization. Capture can end while speech or a background job remains active; those clips are marked incomplete. Open blind listening before reading model identities.</p>')
    h.append('<p class="small">Response timing is measured from the end of a single user input. Seeded or overlapping output is excluded. Endpoint ms is a recognition setting, not measured response latency. Different case mixes are descriptive, not a matched model comparison. Small samples do not give stable tail estimates.</p>')
    h.append('<p class="small">Initial instrument smoke runs are excluded from the main timing table and blind listening. Their recordings and raw analysis remain below. Uncontrolled-condition notes include the later fixture validity audit; they do not change original traces.</p>')
    if report.get("old_recording_clock_audit"):
        h.append('<p><a href="' + esc(report["old_recording_clock_audit"]) + '">Original recording-clock audit</a></p>')
    if report.get("fixture_pack"):
        pack = report["fixture_pack"]
        h.append(f'<p class="small">Input pack version {esc(pack.get("version"))}: {pack["original_suite_audio_fixtures"]} original scenarios + {pack["supplemental_controls"]} supplemental controls · {pack["audio_files"]} WAV files.</p>')
        h.append('<p class="small">The supplemental controls do not increase suite coverage. Original WAV bytes are retained; the pack includes manifest provenance.</p>')
    h.append('</details>')
    if report.get("notes"):
        h.append('<details class="box"><summary>Findings</summary>')
        for label, value in report["notes"].items():
            h.append('<details><summary>' + esc(label.replace('_',' ')) + '</summary>')
            if isinstance(value, str):
                h.append('<p>' + esc(value) + '</p>')
            elif isinstance(value, list) and all(isinstance(item,str) for item in value):
                h.append('<ul>' + ''.join('<li>'+esc(item)+'</li>' for item in value) + '</ul>')
            else:
                h.append('<pre>' + esc(json.dumps(value,indent=2)) + '</pre>')
            h.append('</details>')
        h.append('</details>')
    h.append('<h2>Recorded batches</h2><table><tr><th>Batch</th><th>Role</th><th>Endpoint ms</th><th>Cases recorded</th><th>State</th></tr>')
    for batch in report["batches"]:
        h.append(f'<tr><td>{esc(batch["batch"])}</td><td>{esc(batch["role"])}</td><td>{esc(batch["endpoint_ms_display"])}</td><td>{batch["recorded_cases"]}</td><td>{esc(batch["state"])}</td></tr>')
    h.append('</table>')
    if report.get("metrics"):
        h.append('<h2>Response timing</h2><p class="small">Milliseconds after input ends. Single unseeded turns only; initial smoke excluded.</p><table><tr><th>Batch</th><th>Endpoint ms</th><th>First text median</th><th>Audio received median</th><th>Playback median</th><th>Playback n / captures</th><th>Truncated</th><th>Errors</th></tr>')
        for label, group in report["metrics"].get("groups", {}).items():
            if label in SMOKE_BATCHES:
                continue
            summary = group.get("summary", {})
            latency = summary.get("latency_ms", {})
            def median(key):
                value = latency.get(key, {}).get("median")
                return str(round(value, 1)) if isinstance(value, (int, float)) else "unmeasured"
            playback = latency.get("first_playback_ms", {})
            endpoint = next((batch["endpoint_ms_display"] for batch in report["batches"] if batch["batch"] == label), "not recorded")
            h.append(f'<tr><td>{esc(label)}</td><td>{esc(endpoint)}</td><td>{median("assistant_first_text_ms")}</td><td>{median("first_audio_received_ms")}</td><td>{median("first_playback_ms")}</td><td>{playback.get("count",0)} / {summary.get("capture_count",0)}</td><td>{summary.get("truncated_captures",0)}</td><td>{summary.get("captures_with_errors",0)}</td></tr>')
        h.append('</table>')
        h.append('<details class="box"><summary>Timing analysis and denominators</summary><pre>' + esc(json.dumps(report["metrics"], indent=2)) + '</pre></details>')
    h.append('<h2 id="recordings">Recordings</h2><p class="small">Play reply skips initial silence. Full files and playback controls are retained.</p>')
    for entry in report["cases"]:
        h.append(f'<article id="{entry["id"]}"><h3>{esc(entry["title"])} <span class="tag">{esc(entry["batch"])}</span></h3>')
        if entry["batch"] in SMOKE_BATCHES:
            h.append('<p class="small">Initial instrument smoke. Retained for measurement history.</p>')
        media_review = entry["media_review"]
        if not media_review["continuous_recorder"]:
            h.append('<p class="flag">Recording omitted silent time; timing and AV sync not validated.</p>')
        elif not media_review["audio_timeline_validated"]:
            h.append('<p class="flag">Continuous recording awaits a matching successful media-clock audit. Excluded from blind pacing review.</p>')
        else:
            h.append('<p class="small">Audio timeline approximately agrees with the browser clock. AV and mouth-to-phoneme synchronization remain unverified.</p>')
        if media_review.get("audit"):
            h.append('<p class="small"><a href="' + esc(media_review["audit"]) + '">Audio capture audit</a></p>')
        h.append('<p class="small">' + esc(json.dumps(entry["config"], sort_keys=True)) + '</p>')
        h.append('<p class="small">Recognition endpoint (ms): ' + esc(entry["endpoint_display"]["label"]) + ' · ' + esc(entry["endpoint_display"]["source"]) + '</p>')
        if entry["truncated_at_capture"]:
            h.append('<p class="flag">Capture ended while work remained. Do not judge this as a complete answer.</p>')
        if entry["errors"]:
            h.append('<p class="flag">Errors recorded</p><pre>' + esc(json.dumps(entry["errors"], indent=2)) + '</pre>')
        if entry["conditions_uncontrolled"]:
            h.append('<p class="flag">Uncontrolled: ' + esc(entry["conditions_uncontrolled"]) + '</p>')
        h.append('<div class="grid"><div><strong>Input</strong>')
        for step in entry["input"]:
            h.append(f'<p>{esc(step["text"] or step["type"])} <span class="small">({esc(step["trigger"])} + {esc(step["delay_ms"])} ms)</span></p>')
            if step.get("audio"):
                h.append(f'<audio aria-label="Synthetic user input" controls preload="none" src="{esc(step["audio"])}"></audio>')
        if entry.get("audio"):
            h.append('<p class="small">Recorded robot output</p>')
            audio_id = "reply-audio-" + entry["id"]
            h.append(f'<audio id="{audio_id}" controls preload="none" src="{esc(entry["audio"])}"></audio>')
            if media_review.get("audio_reply_seek_s") is not None:
                h.append(f'<button class="play-reply" data-media="{audio_id}" data-start="{media_review["audio_reply_seek_s"]}">Play reply</button><p class="small">Starts just before speech; full recording retained. Judge pacing within the reply, not reaction timing.</p>')
        else:
            h.append('<p class="empty">No audio file captured.</p>')
        h.append('</div><div>')
        if entry.get("video"):
            h.append('<p class="small">Face recording with its own audio. Do not align it to the standalone output file.</p>')
            video_id = "reply-video-" + entry["id"]
            h.append(f'<video id="{video_id}" controls preload="none" src="{esc(entry["video"])}"></video>')
            if media_review.get("video_reply_seek_s") is not None:
                h.append(f'<button class="play-reply" data-media="{video_id}" data-start="{media_review["video_reply_seek_s"]}">Play reply</button><p class="small">Starts just before speech; full recording retained.</p>')
        else:
            h.append('<p class="empty">No face recording captured.</p>')
        h.append('</div></div><details><summary>Transcript, timing and events</summary>')
        for turn in entry["transcript"]:
            h.append('<p class="turn"><strong>' + esc(turn["role"]) + (' · partial' if turn["partial"] else '') + '</strong><br>' + esc(turn["text"]) + '</p>')
        if not entry["transcript"]:
            h.append('<p class="empty">No transcript events recorded.</p>')
        h.append('<pre>' + esc(json.dumps({"status": entry["status"], "analysis": entry.get("analysis"), "raw_browser_metrics": entry["browser_metrics"], "event_counts": entry["event_counts"], "remaining": entry["remaining"]}, indent=2)) + '</pre>')
        h.append(f'<a href="{esc(entry["trace"])}">Sanitized browser trace</a> · <a href="{esc(entry["fixture"])}">Fixture</a></details></article>')
    h.append('<h2>Controlled checks</h2><p class="small">These are text and component checks, separate from the audio recordings. Production memory prefill tests provide context before a reply. Earlier tool-only memory ablations tested whether a model called the memory tool; their outcomes are not equivalent. Completed means the run returned, not that a human judged it natural.</p><table><tr><th>Run</th><th>Completed / selected</th><th>Memory context</th><th>Status counts</th></tr>')
    for row in report["controlled"]:
        h.append(f'<tr><td><a href="{esc(row["report"])}">{esc(row["run"])}</a></td><td>{esc(row["completed_samples"])} / {esc(row["sample_count"])}</td><td>{esc(row["memory_context"])}</td><td>{esc(json.dumps(row["status_counts"]))}</td></tr>')
    h.append('</table><div class="box"><strong>Background cancellation</strong>')
    for label, summary in report["async_components"].items():
        if summary:
            h.append(f'<p>{esc(label)}: {esc(summary.get("passed_cases"))} / {esc(summary.get("total_cases"))} component cases passed.</p>')
            if summary.get("failed_checks"):
                h.append('<pre>' + esc(json.dumps(summary["failed_checks"], indent=2)) + '</pre>')
    h.append('<p class="small">Controlled transports exercise the production background-job component. These counts do not establish speech quality or live tool latency.</p></div>')
    if report["research"]:
        h.append('<h2>Research reviews</h2><p class="small">Model-generated analysis and proposals, not human listener scores.</p><ul>')
        for row in report["research"]:
            h.append(f'<li><a href="{esc(row["report"])}">{esc(row["worker"])}</a> · {esc(row["status"])}</li>')
        h.append('</ul>')
    h.append('<details class="box"><summary>Fixture coverage and uncontrolled conditions</summary><table><tr><th>Fixture</th><th>Status</th><th>Uncontrolled conditions</th></tr>')
    for fixture in report["fixtures"]:
        h.append(f'<tr><td>{esc(fixture.get("title",fixture.get("id")))}</td><td>{esc(fixture.get("fixture_status","unknown"))}</td><td>{esc(fixture.get("conditions_uncontrolled",[]))}</td></tr>')
    h.append('</table></details><p class="small">Generated ' + esc(report["generated_at"]) + '</p><script>' + REPLY_PLAYBACK_JS + 'for(const button of document.querySelectorAll(".play-reply"))button.onclick=()=>playReply(document.getElementById(button.dataset.media),Number(button.dataset.start),button);</script></html>')
    return "\n".join(h)


BLIND_PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>MIST listening</title>''' + STYLE + '''
<header><h1>Listening</h1><button id="download">Download ratings</button></header>
<p>Listen before reading model results. Clips use synthetic user input. Rate what the recording supports; missing evidence stays unrated.</p>
<p class="small">Only continuous recordings with a matching media-clock audit appear here. Rate pacing within the reply, not reaction timing. AV and mouth-to-phoneme synchronization remain unverified. Phone acoustics and real user comfort still need human sessions.</p>
<div class="bar"><button id="previous">Previous</button><span id="position"></span><button id="next">Next</button><span id="saved" class="small"></span></div>
<div id="clip" class="box"></div><div id="ratings" class="box"></div>
<label>Moment worth changing (timestamp and reason)<textarea id="note"></textarea></label>
<p class="small">1 poor · 2 weak · 3 acceptable · 4 good · 5 excellent. No rating is assumed.</p>
<script id="data" type="application/json">__DATA__</script><script>
'use strict';const data=JSON.parse(document.getElementById('data').textContent),key='mist-e2e-listen-'+data.pack_sha256;const $=id=>document.getElementById(id);let index=0,answers={};try{answers=JSON.parse(localStorage.getItem(key)||'{}')}catch(_){}
function element(tag,text){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e}function save(){try{localStorage.setItem(key,JSON.stringify(answers));$('saved').textContent='Saved in browser'}catch(_){$('saved').textContent='Download to save'}}
function current(){const clip=data.clips[index];return answers[clip.clip_id]||(answers[clip.clip_id]={clip_id:clip.clip_id,ratings:{},note:''})}
function show(){if(!data.clips.length){$('clip').textContent='No recordings have passed the continuous media-clock checks yet. Older captures remain in the main report, with timing warnings.';for(const id of ['previous','next','download','note'])$(id).disabled=true;$('position').textContent='0 clips';return}const clip=data.clips[index],state=current();$('position').textContent=(index+1)+' / '+data.clips.length;$('previous').disabled=index===0;$('next').disabled=index===data.clips.length-1;$('clip').replaceChildren();
if(clip.truncated||clip.errors)$('clip').append(element('p','Capture incomplete or errors recorded. Only rate the part you can hear.'));
if(clip.conditions_uncontrolled&&clip.conditions_uncontrolled.length){const notes=element('details');notes.append(element('summary','Limits of this fixture'));for(const text of clip.conditions_uncontrolled)notes.append(element('p',text));$('clip').append(notes)}
for(const item of clip.input)$('clip').append(element('p',item.text||item.type));const audio=element('audio');audio.controls=true;audio.preload='none';audio.src=clip.audio;$('clip').append(audio);
function replyButton(media,start,parent){if(typeof start!=='number'||!Number.isFinite(start))return;const button=element('button','Play reply');button.onclick=()=>playReply(media,start,button);const hint=element('p','Starts just before speech; full recording retained.');hint.className='small';parent.append(button,hint)}replyButton(audio,clip.audio_reply_seek_s,$('clip'));
if(clip.video){const details=element('details'),video=element('video');details.append(element('summary','Face recording with its own audio'));video.controls=true;video.preload='none';video.src=clip.video;details.append(element('p','AV and mouth-to-phoneme synchronization remain unverified.'),video);replyButton(video,clip.video_reply_seek_s,details);$('clip').append(details)}
$('ratings').replaceChildren();for(const [id,label] of [['warmth','Warmth'],['timing','Pacing and pauses'],['emotional_fit','Emotional fit'],['reading','Natural speech rather than reading'],['no_irritation','Easy to listen to, without irritation']]){const row=element('label');row.className='rating';row.append(element('span',label));const select=element('select');for(const [v,t]of[['','Unrated'],['1','1 · Poor'],['2','2 · Weak'],['3','3 · Acceptable'],['4','4 · Good'],['5','5 · Excellent'],['unassessable','Cannot assess']]){const opt=element('option',t);opt.value=v;select.append(opt)}select.value=state.ratings[id]||'';select.onchange=()=>{state.ratings[id]=select.value;save()};row.append(select);$('ratings').append(row)}$('note').value=state.note;}
$('previous').onclick=()=>{if(index>0){index--;show()}};$('next').onclick=()=>{if(index<data.clips.length-1){index++;show()}};$('note').oninput=()=>{current().note=$('note').value;save()};$('download').onclick=()=>{const payload={schema_version:1,pack_sha256:data.pack_sha256,exported_at:new Date().toISOString(),ratings:Object.values(answers)};const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));const a=element('a');a.href=url;a.download='mist-listening-ratings.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};show();
</script><script>''' + REPLY_PLAYBACK_JS + '''</script></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("brain/results/e2e_20260924"))
    parser.add_argument("--output", type=Path, default=Path("brain/results/naturalness_20260923/e2e"))
    parser.add_argument("--metrics", type=Path)
    parser.add_argument("--notes", type=Path)
    args = parser.parse_args()
    metrics = read_json(args.metrics) if args.metrics else read_json(args.source / "metrics.json")
    notes = read_json(args.notes) if args.notes else read_json(args.source / "findings.json")
    print(json.dumps(build_report(args.source, args.output, metrics, notes)))


if __name__ == "__main__":
    main()
