"""Package three existing synthetic MIST WAVs and honest, audio-gated cue demos."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import statistics
import struct
import subprocess
import sys
import time
import wave


HERE = Path(__file__).resolve().parent
PACK = HERE.parent
BRAIN = HERE.parents[2]
REPO = BRAIN.parent
sys.path.insert(0, str(BRAIN))
from duplex.phoneme_cues import WORD, bundled_pronunciations, phoneme_mouth_cues


VOICE_ID = "24AMj4dc02cYAwoUnqzN"
LIVE = BRAIN / "results/dual-model-harness-20260924/live-smoke/probe-20260924T164458Z-9061ff"
QUALITY = BRAIN / "results/brain-quality-20260929/voice-after"
VISEMES = {"rest", "AA", "EH", "EE", "OH", "OO", "MBP", "FV", "LNT", "TH", "S"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_pcm(path):
    with wave.open(str(path), "rb") as audio:
        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getcomptype()) == (1, 2, 24000, "NONE")
        frames = audio.getnframes()
        return audio.readframes(frames), frames / 24000


def relative(path):
    return path.relative_to(REPO).as_posix()


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def recover_provider_onsets(trace, sequence, pcm_bytes):
    """Retain padding bounds, actual caption growth and clipped-onset flags.

    Raw character durations were not retained. A complete word is bounded by its
    first letter's onset and the following separator's onset. No reply-script
    character is inserted. Packet payload length ambiguity stays in the record.
    """
    packets = [row for row in trace["events"] if row["event"].get("type") == "audio_delivery"
               and row["event"].get("seq") == sequence]
    candidates = []
    for row in packets:
        event = row["event"]
        assert event["sample_rate"] == 24000
        assert event["caption_source"] == "elevenlabs_normalized_alignment"
        encoded = event["encoded_bytes"]
        assert isinstance(encoded, int) and encoded > 0 and encoded % 4 == 0
        candidates.append([size for padding in range(3) if (size := encoded // 4 * 3 - padding) % 2 == 0])
    maxima = [max(values) for values in candidates]
    capacities = [max(values) - min(values) for values in candidates]
    excess = sum(maxima) - pcm_bytes
    assert 0 <= excess <= sum(capacities) and excess % 2 == 0
    prefix_bytes = capacity_before = 0
    prefix = ""
    onsets = []
    for index, row in enumerate(packets):
        capacity_after = sum(capacities[index:])
        lower_bytes = prefix_bytes - min(excess, capacity_before)
        upper_bytes = prefix_bytes - max(0, excess - capacity_after)
        event = row["event"]
        for cue in event["caption_cues"]:
            text, local = cue["text"], cue["time"]
            assert isinstance(text, str) and math.isfinite(local) and local >= 0
            assert text.startswith(prefix), "Provider caption text changed; do not repair it from the reply"
            if text == prefix:
                continue
            lower = lower_bytes / 48000 + local
            upper = upper_bytes / 48000 + local
            censored = local == 0
            if censored and onsets:
                lower = onsets[-1]["onsetLower"]
            for char in text[len(prefix):]:
                onsets.append({"char": char, "time": (lower_bytes + upper_bytes) / 96000 + local,
                               "onsetLower": lower, "onsetUpper": upper,
                               "clippedAtPacketStart": censored, "eventId": row["id"]})
            prefix = text
        prefix_bytes += maxima[index]
        capacity_before += capacities[index]
    assert onsets and all(a["time"] <= b["time"] for a, b in zip(onsets, onsets[1:]))
    words = []
    excluded = set()
    for token in WORD.finditer(prefix):
        complete_end = token.end() < len(onsets)
        first = onsets[token.start()]
        separator = onsets[token.end()] if complete_end else None
        eligible = bool(separator and not first["clippedAtPacketStart"]
                        and not separator["clippedAtPacketStart"] and separator["time"] > first["time"])
        if not eligible:
            excluded.add(token.group().casefold().replace("\u2019", "'"))
        words.append({"word": token.group(), "start": first["time"],
                      "end": separator["time"] if separator else None,
                      "startBounds": [first["onsetLower"], first["onsetUpper"]],
                      "endBounds": [separator["onsetLower"], separator["onsetUpper"]] if separator else None,
                      "unclippedBoundaries": eligible})
    # This conservative spelling-wide filter also rejects other occurrences of
    # a word with a clipped boundary. It never upgrades an uncertain occurrence.
    dictionary = {word: variants for word, variants in bundled_pronunciations().items() if word not in excluded}
    times = [row["time"] * 1000 for row in onsets]
    durations = [max(0, (onsets[index + 1]["time"] - row["time"]) * 1000)
                 if index + 1 < len(onsets) else 0 for index, row in enumerate(onsets)]
    message = {"normalizedAlignment": {"chars": [row["char"] for row in onsets],
               "charStartTimesMs": times, "charDurationsMs": durations}}
    return message, dictionary, {"text": prefix, "captionSource": "elevenlabs_normalized_alignment",
        "method": "Provider caption growth onsets; word end is the following separator onset.",
        "originalCharacterDurationsRetained": False, "packetCount": len(packets),
        "paddingAmbiguityBytes": excess, "maximumCumulativeOffsetUncertaintySeconds": excess / 48000,
        "captionTimeRoundingSeconds": .0000005, "excludedWordsWithClippedBoundaries": sorted(excluded),
        "words": words, "characterOnsets": onsets}


def validate_clip(clip, destination, pcm):
    cues = clip["cues"]
    assert cues and cues[0]["time"] == 0
    assert all(a["time"] < b["time"] for a, b in zip(cues, cues[1:]))
    assert all(math.isfinite(cue["time"]) and 0 <= cue["time"] < clip["duration"]
               and cue["viseme"] in VISEMES and math.isfinite(cue["amount"])
               and 0 <= cue["amount"] <= 1 for cue in cues)
    assert sha256(destination) == clip["nativeSha256"]
    assert hashlib.sha256(pcm).hexdigest() == clip["pcmSha256"]
    assert all(cue["amount"] == 0 for cue in cues if cue["viseme"] == "rest")
    shapes = dict(sorted(Counter(cue["viseme"] for cue in cues).items()))
    return {"id": clip["id"], "nativeCopyIdentical": True, "durationSeconds": clip["duration"],
            "cueCount": len(cues), "visemeCounts": shapes, "strictlyIncreasingFiniteCues": True,
            "amountsInRange": True, "restCuesClosed": True, "syntheticOnly": True,
            "alignmentSource": clip["alignmentSource"]}


def main():
    trace_path = LIVE / "public-trace.json"
    summary_path = LIVE / "probe-summary.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8-sig"))
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    assert trace["session"]["config"]["voice_id"] == VOICE_ID
    assert summary["input_mode"] == "typed_websocket"
    clips, checks, recovered = [], [], {}
    specs = (("mist-hinge", "A hinge", 0, 1), ("mist-second-attempt", "A second attempt", 2, 3))
    for clip_id, title, sequence, turn_number in specs:
        source = LIVE / f"turn-{turn_number}.wav"
        raw, duration = read_pcm(source)
        turn = next(turn for turn in summary["turns"] if turn["number"] == turn_number)
        assert turn["audio_bytes"] == len(raw)
        assert turn["audio_sha256"] == hashlib.sha256(raw).hexdigest()
        message, dictionary, evidence = recover_provider_onsets(trace, sequence, len(raw))
        assert " ".join(evidence["text"].split()) == " ".join(turn["assistant_text"].split())
        cues, cue_source = phoneme_mouth_cues(raw, message, pronunciations=dictionary)
        assert "estimated_phonemes" in cue_source
        destination = PACK / "site/audio" / f"{clip_id}-native.wav"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        clip = {"id": clip_id, "title": title, "text": evidence["text"].strip(),
            "audio": f"audio/{destination.name}", "cues": cues, "duration": duration,
            "alignmentSource": "recovered_provider_caption_word_bounds_estimated_phonemes_audio_gated",
            "cueImplementationSource": cue_source,
            "limitations": ["Provider caption growth supplies word bounds; original character durations were not retained.",
                "Positions inside words are pronunciation-based animation estimates, not measured phoneme timestamps.",
                "Redacted base64 padding leaves bounded packet-offset uncertainty; interval bounds are recorded in speech/recovered-caption-onsets.json.",
                "Clipped word boundaries and unknown dictionary words keep the character fallback. Audio energy closes the mouth in silence.",
                "No human hearing or perceptual lip-sync rating is inferred."],
            "timeUncertaintySeconds": evidence["maximumCumulativeOffsetUncertaintySeconds"] + .0000005,
            "voice": {"name": "MIST (refined)", "provider": "ElevenLabs", "voiceId": VOICE_ID,
                      "model": "eleven_flash_v2_5", "synthetic": True},
            "sourceWav": relative(source), "sourceTrace": relative(trace_path),
            "sourceTraceSha256": sha256(trace_path), "nativeSha256": sha256(source),
            "pcmSha256": hashlib.sha256(raw).hexdigest()}
        clips.append(clip)
        checks.append(validate_clip(clip, destination, raw))
        recovered[clip_id] = evidence
    results_path = QUALITY / "results.json"
    results = json.loads(results_path.read_text(encoding="utf-8-sig"))
    assert results["voice_id"] == VOICE_ID
    sample = next(sample for sample in results["samples"] if sample["blind_id"] == "clip-05-6aa2d2")
    assert sample["status"] == "ok" and sample["provider_final"] and not sample["warning_codes"]
    source = QUALITY / "audio" / sample["wav_file"]
    raw, duration = read_pcm(source)
    cues, cue_source = phoneme_mouth_cues(raw, {})
    destination = PACK / "site/audio/mist-patience-native.wav"
    shutil.copyfile(source, destination)
    clip = {"id": "mist-patience", "title": "Thanks for waiting (energy fallback)", "text": sample["text"],
        "audio": f"audio/{destination.name}", "cues": cues, "duration": duration,
        "alignmentSource": cue_source,
        "limitations": ["This benchmark saved alignment coverage counts but discarded exact character and caption timing.",
            "Cues follow measured PCM energy only. AA is a generic open shape; no word or phoneme timing is inferred.",
            "No human hearing or perceptual lip-sync rating is inferred."],
        "voice": {"name": "MIST (refined)", "provider": "ElevenLabs", "voiceId": VOICE_ID,
                  "model": sample["model"], "synthetic": True},
        "sourceWav": relative(source), "sourceMetadata": relative(results_path),
        "sourceMetadataSha256": sha256(results_path), "nativeSha256": sha256(source),
        "pcmSha256": hashlib.sha256(raw).hexdigest()}
    clips.append(clip)
    checks.append(validate_clip(clip, destination, raw))
    write_json(HERE / "recovered-caption-onsets.json", {"version": 1, "clips": recovered})
    write_json(PACK / "site/speech-clips.json", {"version": 1, "clips": clips})
    unit = subprocess.run([sys.executable, str(BRAIN / "harness/test_geraldine_phoneme_cues.py")],
                          cwd=REPO, capture_output=True, text=True)
    (HERE / "test-geraldine-phoneme-cues.txt").write_text(unit.stdout + unit.stderr, encoding="utf-8")
    if unit.returncode:
        raise RuntimeError("Pronunciation cue tests failed; see speech/test-geraldine-phoneme-cues.txt")
    synthetic = struct.pack("<h", 6000) * 2400
    timing_message = {"alignment": {"chars": list("phone."),
        "charStartTimesMs": [0, 15, 30, 45, 60, 75], "charDurationsMs": [15, 15, 15, 15, 15, 15]}}
    bundled_pronunciations.cache_clear()
    began = time.perf_counter()
    phoneme_mouth_cues(synthetic, timing_message)
    cold_ms = (time.perf_counter() - began) * 1000
    timings = []
    for _ in range(40):
        began = time.perf_counter()
        phoneme_mouth_cues(synthetic, timing_message)
        timings.append((time.perf_counter() - began) * 1000)
    qa = {"version": 1, "syntheticFixturesOnly": True, "newPaidApiCalls": 0,
        "unchangedRuntimeIntegration": True, "clipCount": len(clips), "fixtureChecks": checks,
        "tests": {"command": "python brain/harness/test_geraldine_phoneme_cues.py", "exitCode": unit.returncode,
                  "output": "speech/test-geraldine-phoneme-cues.txt"},
        "timing": {"method": "40 local calls on a 100 ms PCM chunk with provider-format alignment; wall-clock performance, no network.",
                   "dictionaryLoadAndFirstChunkMs": cold_ms, "warmMedianChunkMs": statistics.median(timings),
                   "warmMaximumChunkMs": max(timings), "wholeUtteranceWait": False},
        "limitations": ["Timing measurements are local to this run and exclude synthesis/network latency.",
                        "Pronunciation duration weights estimate animation inside measured or recovered word bounds.",
                        "Audio silence gating uses 20 ms RMS windows and cannot prove perceptual sync quality."],
        "dictionary": {"file": "speech/cmudict-subset.json", "sha256": sha256(HERE / "cmudict-subset.json"),
                       "license": "speech/CMUDICT-LICENSE.txt", "wordCount": len(bundled_pronunciations())}}
    write_json(PACK / "qa/speech-cues.json", qa)
    print(json.dumps({"clips": [{"id": clip["id"], "duration": clip["duration"],
                                 "source": clip["alignmentSource"], "cues": len(clip["cues"])} for clip in clips],
                      "warmMedianChunkMs": qa["timing"]["warmMedianChunkMs"], "testsPassed": True}))


if __name__ == "__main__":
    main()
