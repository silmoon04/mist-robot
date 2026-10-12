"""Check two short clips from the configured existing MIST voice.

Run with --selfcheck for offline checks only. A normal run generates WAVs and
uses an existing Deepgram key, when present, for an independent word check.
"""
from __future__ import annotations

import argparse
import base64
import difflib
import hashlib
import io
import json
import math
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

BRAIN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN_DIR))
from ui import voice

DEFAULT_OUTPUT = BRAIN_DIR.parent / "design" / "mist_v2_20260906" / "brain_v2_20260907" / "voice"
LINES = (
    "Hello. I'm MIST. My wheels are ready, and I'm listening.",
    "One moment, please. I can look left, pause, and look back at you.",
)


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    path = BRAIN_DIR.parent / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip("\"'")
    return env


def _words(text: str) -> list[str]:
    return re.sub(r"[^a-z0-9\s]", "", text.lower()).split()


def word_scores(expected: str, heard: str) -> dict:
    reference, hypothesis = _words(expected), _words(heard)
    previous = list(range(len(hypothesis) + 1))
    for i, left in enumerate(reference, 1):
        row = [i]
        for j, right in enumerate(hypothesis, 1):
            row.append(min(row[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = row
    distance = previous[-1]
    return {"word_similarity": round(difflib.SequenceMatcher(None, reference, hypothesis).ratio(), 4),
            "word_error_rate": round(distance / max(1, len(reference)), 4),
            "word_edits": distance, "reference_words": len(reference)}


def transcribe(audio: bytes, key: str) -> dict:
    req = urllib.request.Request(
        "https://api.deepgram.com/v1/listen?model=nova-3&smart_format=false&punctuate=false",
        data=audio, headers={"Authorization": f"Token {key}", "Content-Type": "audio/wav"}, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            payload = json.load(response)
        alternative = payload["results"]["channels"][0]["alternatives"][0]
        return {"status": "ok", "provider": "deepgram", "model": "nova-3",
                "transcript": alternative.get("transcript", ""),
                "confidence": alternative.get("confidence"),
                "words": [{key: word[key] for key in ("word", "start", "end", "confidence") if key in word}
                          for word in alternative.get("words", [])],
                "api_latency_s": round(time.perf_counter() - started, 4),
                "audio_seconds": payload.get("metadata", {}).get("duration")}
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()
        return {"status": "error", "error": f"Deepgram returned HTTP {status}"}
    except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError, TypeError):
        return {"status": "error", "error": "Deepgram transcription was unavailable or unreadable"}


def timing_check(result: dict) -> dict:
    events = result["events"]
    duration = result["duration_s"]
    errors = []
    if not events or events[-1]["viseme"] != "rest":
        errors.append("mouth does not finish at rest")
    previous = -1.0
    for event in events:
        if event["time"] < previous or not 0 <= event["time"] <= duration + 0.0001:
            errors.append("event lies outside ordered audio time")
        if event["viseme"] not in voice.VISEMES:
            errors.append("unknown mouth shape")
        previous = event["time"]
    for silence in result.get("silences", []):
        midway = (silence["start"] + silence["end"]) / 2
        active = next((event for event in reversed(events) if event["time"] <= midway), None)
        if active and active["viseme"] != "rest":
            errors.append("mouth is open in detected silence")
    return {"passed": not errors, "errors": sorted(set(errors)), "event_count": len(events),
            "silence_intervals": len(result.get("silences", [])),
            "has_provider_character_timing": result["alignment_source"] == "elevenlabs_character_timestamps"}


def write_report(report: dict, directory: Path) -> Path:
    path = directory / "voice_check.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# MIST voice check", "", f"Checked {report['checked_at']}.", "",
             f"Existing voice: {report['voice_label']} (`{report['voice_id']}`).",
             "", report["interpretation"], "",
             "| Clip | Characters | Audio seconds | TTS API seconds | Word score | Timing |",
             "| --- | ---: | ---: | ---: | ---: | --- |"]
    for sample in report["samples"]:
        if sample["status"] != "ok":
            lines.extend(("", f"Generation failed: {sample['error']}"))
            continue
        usage = sample["usage"]
        transcription = sample["transcription"]
        score = transcription.get("word_similarity", "not checked")
        outcome = "passed" if sample["timing_check"]["passed"] else "failed"
        lines.append(f"| [{sample['index']}]({sample['audio_file']}) | {usage['characters']} | "
                     f"{sample['duration_s']} | {usage['api_latency_s']} | {score} | {outcome} |")
    for sample in report["samples"]:
        if sample["status"] == "ok":
            lines.extend(("", f"Clip {sample['index']}: {sample['text']}",
                          f"Heard: {sample['transcription'].get('transcript', 'Transcription unavailable.')}",
                          f"Alignment: `{sample['alignment_source']}`; "
                          f"{sample['timing_check']['event_count']} mouth events and "
                          f"{sample['timing_check']['silence_intervals']} detected quiet intervals."))
    lines.extend(("", report["pricing"], "", "```json", json.dumps(report["totals"], indent=2), "```", ""))
    (directory / "voice_check.md").write_text("\n".join(lines), encoding="utf-8")
    return path


def selfcheck() -> int:
    sample_rate = 24000
    samples = [0 if i < 2400 or 9600 <= i < 14400 or i >= 21600
               else round(9000 * math.sin(2 * math.pi * 180 * i / sample_rate))
               for i in range(sample_rate)]
    pcm = struct.pack("<" + "h" * len(samples), *samples)
    payload = {"audio_base64": base64.b64encode(pcm).decode(), "normalized_alignment": {
        "characters": ["a", ".", "b"], "character_start_times_seconds": [0.1, 0.4, 0.6],
        "character_end_times_seconds": [0.4, 0.6, 0.9]}}
    observed = []

    class Response(io.BytesIO):
        headers = {"character-cost": "3"}

    def response(req, timeout):
        observed.append(req.full_url)
        return Response(json.dumps(payload).encode())

    env = {"ELEVENLABS_API_KEY": "offline-placeholder", "DEEPGRAM_API_KEY": "offline-placeholder"}
    with patch.object(urllib.request, "urlopen", response):
        clip = voice.generate_speech("a.b", "elevenlabs", None, env)
    assert timing_check(clip)["passed"], timing_check(clip)
    assert clip["duration_s"] == 1.0
    assert clip["usage"]["provider_billed_characters"] == 3
    assert "/with-timestamps?output_format=pcm_24000" in observed[0]
    assert clip["alignment_source"] == "elevenlabs_character_timestamps"
    wav = base64.b64decode(clip["audio_base64"])
    with patch.object(urllib.request, "urlopen", lambda *args, **kwargs: Response(wav)):
        fallback = voice.generate_speech("A brief pause. Back again.", "deepgram", None, env)
    assert timing_check(fallback)["passed"], timing_check(fallback)
    assert fallback["alignment_source"] == "text_estimate_audio_duration"
    assert word_scores("One two three", "one two three")["word_error_rate"] == 0
    assert word_scores("One two three", "one three")["word_edits"] == 1
    for failure in (OSError("fake-secret-value"), ValueError("Invalid header: fake-secret-value")):
        with patch.object(urllib.request, "urlopen", side_effect=failure):
            try:
                voice.generate_speech("Hi.", "elevenlabs", None, env)
                raise AssertionError("provider failure accepted")
            except voice.SpeechError as exc:
                assert "fake-secret-value" not in str(exc)
    with patch.object(urllib.request, "urlopen", side_effect=AssertionError("unexpected network")):
        for text, selected_voice in (("", None), ("x" * 1501, None), ("Hi.", "other-voice")):
            try:
                voice.generate_speech(text, "elevenlabs", selected_voice, env)
                raise AssertionError("invalid input accepted")
            except voice.SpeechError:
                pass
    print("SELFCHECK OK: WAV duration, provider timing, pause closure, fallback, word scores, safe errors, input limits")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selfcheck", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--lines", type=int, choices=(1, 2), default=2)
    parser.add_argument("--skip-transcription", action="store_true")
    args = parser.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    env = load_env()
    config = voice.speech_config(env)
    if not config["elevenlabs_available"]:
        print("ElevenLabs is not configured; no audio generated.")
        return 1
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "synthetic_audio": True,
              "voice_id": config["elevenlabs_voice_id"], "voice_label": config["elevenlabs_voice_label"],
              "provider": "elevenlabs", "samples": [],
              "limits": "Two short synthetic phrases maximum; existing voice only.",
              "interpretation": "Word fidelity tests intelligibility. Spelling-derived mouth shapes are approximate; this does not measure voice likeness or perceptual lip sync.",
              "pricing": "No currency estimate. Character-cost is recorded only when returned by the provider.",
              "references": ["https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps",
                             "https://elevenlabs.io/docs/api-reference/introduction",
                             "https://developers.deepgram.com/docs/pre-recorded-audio"]}
    for index, text in enumerate(LINES[:args.lines], 1):
        sample = {"index": index, "text": text}
        try:
            result = voice.generate_speech(text, "elevenlabs", config["elevenlabs_voice_id"], env)
        except voice.SpeechError as exc:
            sample.update({"status": "error", "error": str(exc), "error_code": exc.code})
            report["samples"].append(sample)
            break
        audio = base64.b64decode(result.pop("audio_base64"))
        name = f"mist_refined_{index:02}.wav"
        (args.output / name).write_bytes(audio)
        sample.update(result)
        sample.update({"status": "ok", "audio_file": name, "audio_sha256": hashlib.sha256(audio).hexdigest(),
                       "timing_check": timing_check(result)})
        key = env.get("DEEPGRAM_API_KEY")
        if key and not args.skip_transcription:
            transcription = transcribe(audio, key)
            if transcription["status"] == "ok":
                transcription.update(word_scores(text, transcription["transcript"]))
            sample["transcription"] = transcription
        else:
            sample["transcription"] = {"status": "skipped", "reason": "disabled or no existing Deepgram key"}
        report["samples"].append(sample)
        print(json.dumps({"sample": index, "voice_id": result["voice_id"], "usage": result["usage"],
                          "timing_passed": sample["timing_check"]["passed"],
                          "word_similarity": sample["transcription"].get("word_similarity")}))
    successful = [sample for sample in report["samples"] if sample["status"] == "ok"]
    report["totals"] = {"generated_clips": len(successful),
                        "characters": sum(sample["usage"]["characters"] for sample in successful),
                        "audio_seconds": round(sum(sample["duration_s"] for sample in successful), 4),
                        "tts_api_latency_s": round(sum(sample["usage"]["api_latency_s"] for sample in successful), 4),
                        "transcription_audio_seconds": round(sum(sample["transcription"].get("audio_seconds", 0) or 0
                                                                   for sample in successful), 4),
                        "transcription_api_latency_s": round(sum(sample["transcription"].get("api_latency_s", 0)
                                                                 for sample in successful), 4),
                        "cost_usd": None}
    if successful and all("provider_billed_characters" in sample["usage"] for sample in successful):
        report["totals"]["provider_billed_characters"] = sum(sample["usage"]["provider_billed_characters"] for sample in successful)
    report["passed"] = (len(successful) == args.lines and
                        all(sample["timing_check"]["passed"] and sample["timing_check"]["has_provider_character_timing"]
                            and (sample["transcription"]["status"] == "skipped" or
                                 sample["transcription"].get("word_similarity", 0) >= 0.9) for sample in successful))
    path = write_report(report, args.output)
    print(json.dumps({"report": str(path), "passed": report["passed"], "totals": report["totals"]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
