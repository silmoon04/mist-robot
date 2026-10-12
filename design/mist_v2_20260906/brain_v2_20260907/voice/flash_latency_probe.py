"""Two authorized voice-only probes against the saved same-phrase baseline.

The budget marker prevents a second invocation from spending more TTS requests.
This script does not contact the running UI or start an LLM request.
"""
from __future__ import annotations

import base64
import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parents[3] / "brain"
sys.path.insert(0, str(BRAIN))
from ui.voice import generate_speech, SpeechError
from harness.elevenlabs_voice_check import load_env, timing_check, transcribe, word_scores

OUTPUT = HERE / "flash_latency_20260907"
REFERENCES = [
    "https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps",
    "https://elevenlabs.io/docs/overview/models",
    "https://elevenlabs.io/docs/eleven-api/guides/how-to/best-practices/latency-optimization",
]


def write_summary(report):
    successful = [probe for probe in report["probes"] if probe["status"] == "ok"]
    rows = ["# Responsive voice latency check", "", f"Checked {report['checked_at']}.", "",
            f"Existing voice: {report['voice_label']} (`{report['voice_id']}`).", "",
            f"Phrase: {report['text']}", "", report["method"], "",
            "| Request | Headers / first body byte | Complete API response | Local processing | Audio duration | Word score |",
            "| --- | ---: | ---: | ---: | ---: | ---: |"]
    baseline = report["baseline"]
    rows.append(f"| Saved Multilingual v2 | not measured | {baseline['usage']['api_latency_s']:.4f} s | not measured | "
                f"{baseline['duration_s']:.4f} s | {baseline['transcription']['word_similarity']:.2f} |")
    for probe in report["probes"]:
        if probe["status"] != "ok":
            continue
        usage = probe["usage"]
        rows.append(f"| [Flash v2.5 #{probe['index']}]({probe['audio_file']}) | {usage['api_headers_s']:.4f} / "
                    f"{usage['api_first_byte_s']:.4f} s | {usage['api_latency_s']:.4f} s | "
                    f"{usage['local_processing_s']:.4f} s | {probe['duration_s']:.4f} s | "
                    f"{probe['transcription'].get('word_similarity', 0):.2f} |")
    comparison = report.get("comparison", {})
    checks_passed = (len(successful) == 2 and all(probe["timing_check"]["passed"] and
                     probe["timing_check"]["has_provider_character_timing"] and
                     probe["transcription"].get("word_similarity", 0) >= 0.9 for probe in successful))
    if checks_passed and comparison.get("api_latency_reduction_percent", 0) > 0:
        rows.extend(("", "The measurements support Flash as the Responsive default, with Multilingual v2 available as Quality. "
                     "Both Flash clips preserved provider character alignment and passed mouth pause checks. "
                     f"Median API completion was {comparison['api_latency_reduction_percent']}% lower than the saved baseline. "
                     "Two requests do not establish a stable latency distribution."))
        if successful[0]["usage"]["api_latency_s"] > baseline["usage"]["api_latency_s"]:
            rows.extend(("", "The first Flash request was slower than the saved baseline; the second was faster."))
    else:
        rows.extend(("", "This probe does not establish a faster intelligible default."))
    rows.extend(("", report["limits"], "",
                 "The transport remains urllib because the measurements do not isolate connection or TLS time.", ""))
    if comparison:
        rows.extend((f"Usage: {comparison['input_characters']} input characters, {comparison['audio_seconds']} seconds "
                     f"of generated audio, and {comparison['provider_billed_characters']} provider-billed characters. "
                     "No dollar cost was calculated.", ""))
    rows.extend(("Sources:", ""))
    rows.extend(f"- [{url.rsplit('/', 1)[-1]}]({url})" for url in REFERENCES)
    (OUTPUT / "probe.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main():
    baseline = json.loads((HERE / "voice_check.json").read_text(encoding="utf-8"))["samples"][1]
    OUTPUT.mkdir(exist_ok=True)
    marker = OUTPUT / "request_budget.json"
    if marker.exists():
        raise SystemExit("Probe budget is already reserved. Read the saved artifacts; do not generate more clips.")
    marker.write_text(json.dumps({"reserved_tts_requests": 2, "model_id": "eleven_flash_v2_5",
                                 "voice_id": baseline["voice_id"], "text": baseline["text"]}) + "\n", encoding="utf-8")
    env = load_env()
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "voice_id": baseline["voice_id"],
              "voice_label": "MIST (refined)", "text": baseline["text"], "synthetic_audio": True,
              "baseline": {key: baseline[key] for key in ("model_id", "duration_s", "usage", "transcription", "audio_file", "audio_sha256")},
              "probes": [], "references": REFERENCES,
              "method": "Two fresh urllib HTTPS requests using the same existing voice, phrase, PCM24k format and timestamp endpoint. Comparison uses one earlier Multilingual v2 request; it is not a randomized simultaneous benchmark.",
              "timing_definitions": {"api_headers_s": "Request start to response headers, including connection and provider work.",
                                     "api_first_byte_s": "Request start to first response-body byte, not playback onset or model inference time.",
                                     "api_body_s": "Response headers to complete JSON body.",
                                     "api_latency_s": "Request start to complete JSON body.",
                                     "generation_total_s": "Function entry through audio decoding, mouth cue generation and output encoding."},
              "limits": "Word checks test intelligibility, not voice likeness. Headers do not separate TLS cost from provider generation. No playback or live UI interaction was performed. No currency estimate."}
    for index in (1, 2):
        try:
            clip = generate_speech(baseline["text"], "elevenlabs", baseline["voice_id"], env, model="eleven_flash_v2_5")
        except SpeechError as error:
            report["probes"].append({"index": index, "status": "error", "error": str(error), "code": error.code})
            break
        audio = base64.b64decode(clip.pop("audio_base64"))
        path = OUTPUT / f"mist_flash_{index:02}.wav"
        path.write_bytes(audio)
        record = {"index": index, "status": "ok", **clip, "audio_file": path.name,
                  "audio_sha256": hashlib.sha256(audio).hexdigest(), "timing_check": timing_check(clip)}
        if env.get("DEEPGRAM_API_KEY"):
            result = transcribe(audio, env["DEEPGRAM_API_KEY"])
            if result["status"] == "ok":
                result.update(word_scores(baseline["text"], result["transcript"]))
            record["transcription"] = result
        else:
            record["transcription"] = {"status": "skipped"}
        report["probes"].append(record)
        (OUTPUT / "probe.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"probe": index, "usage": clip["usage"], "timing_check": record["timing_check"],
                          "word_similarity": record["transcription"].get("word_similarity"),
                          "transcript": record["transcription"].get("transcript")}))
    successful = [probe for probe in report["probes"] if probe["status"] == "ok"]
    if successful:
        median = statistics.median(probe["usage"]["api_latency_s"] for probe in successful)
        baseline_s = baseline["usage"]["api_latency_s"]
        report["comparison"] = {"baseline_api_latency_s": baseline_s, "flash_median_api_latency_s": round(median, 4),
                                "api_latency_reduction_percent": round((1 - median / baseline_s) * 100, 1),
                                "input_characters": sum(probe["usage"]["characters"] for probe in successful),
                                "audio_seconds": round(sum(probe["duration_s"] for probe in successful), 4),
                                "provider_billed_characters": sum(probe["usage"].get("provider_billed_characters", 0) for probe in successful),
                                "cost_usd": None}
    (OUTPUT / "probe.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_summary(report)
    print(json.dumps({"report": str(OUTPUT / "probe.json"), "comparison": report.get("comparison")}))


if __name__ == "__main__":
    main()
