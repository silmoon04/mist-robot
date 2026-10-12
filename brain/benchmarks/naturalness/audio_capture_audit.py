"""Offline audit of finished browser captures. No model, provider, or browser calls.

python audio_capture_audit.py DIRECTORY [DIRECTORY ...] [--contact-sheet]
Each completed case gets audio_capture_audit/audit.json and decoded-mono.wav.
Reruns replace only this audit directory's known output files. Raw capture files
remain unchanged. RMS activity and pauses cannot establish prosody or naturalness.
Requires PyAV and numpy; contact sheets also require Pillow.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import wave

import numpy as np

TIMING_KIND = "software_output_estimate_not_acoustic"


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runs(mask):
    """Half-open index spans for true values."""
    edges = np.flatnonzero(np.diff(np.r_[False, np.asarray(mask, dtype=bool), False].astype(np.int8)))
    return list(zip(edges[::2].tolist(), edges[1::2].tolist()))


def waveform_metrics(samples, rate, threshold_dbfs=-45, frame_ms=10):
    values = np.asarray(samples, dtype=np.float64)
    if values.ndim != 1 or not len(values) or not np.all(np.isfinite(values)):
        raise ValueError("Audio must contain finite mono samples")
    if not finite(rate) or rate <= 0 or not finite(frame_ms) or frame_ms <= 0:
        raise ValueError("Invalid sample rate or RMS window")
    if not finite(threshold_dbfs) or not -120 <= threshold_dbfs <= 0:
        raise ValueError("RMS threshold must be between -120 and 0 dBFS")
    size = max(1, round(rate * frame_ms / 1000))
    starts = np.arange(0, len(values), size)
    lengths = np.minimum(size, len(values) - starts)
    energy = np.add.reduceat(values * values, starts) / lengths
    rms = np.sqrt(energy)
    activity = rms >= 10 ** (threshold_dbfs / 20)
    duration = len(values) * 1000 / rate
    spans = [{"start_ms": a * size * 1000 / rate,
              "end_ms": min(b * size, len(values)) * 1000 / rate}
             for a, b in runs(activity)]
    quiet = [{"start_ms": a * size * 1000 / rate,
              "end_ms": min(b * size, len(values)) * 1000 / rate,
              "duration_ms": (min(b * size, len(values)) - a * size) * 1000 / rate}
             for a, b in runs(~activity) if a > 0 and b < len(activity)]
    near_full = np.abs(values) >= .999
    near_runs = runs(near_full)
    overall_rms = math.sqrt(float(np.mean(values * values)))
    return {
        "scope": "Decoded digital output waveform; level-based activity, not speech recognition",
        "duration_ms": duration, "sample_rate": rate, "samples": len(values),
        "peak_amplitude": float(np.max(np.abs(values))),
        "rms_dbfs": 20 * math.log10(overall_rms) if overall_rms else None,
        "activity_threshold_dbfs": threshold_dbfs, "rms_window_ms": size * 1000 / rate,
        "non_silent_duration_ms": float(lengths[activity].sum()) * 1000 / rate,
        "first_non_silent_ms": spans[0]["start_ms"] if spans else None,
        "last_non_silent_ms": spans[-1]["end_ms"] if spans else None,
        "leading_quiet_ms": spans[0]["start_ms"] if spans else duration,
        "trailing_quiet_ms": duration - spans[-1]["end_ms"] if spans else duration,
        "activity_spans": spans,
        "internal_quiet_gaps": quiet,
        "internal_quiet_gap_count": len(quiet),
        "internal_quiet_total_ms": sum(g["duration_ms"] for g in quiet),
        "internal_quiet_over_300_ms": [g for g in quiet if g["duration_ms"] > 300],
        "internal_quiet_over_700_ms": [g for g in quiet if g["duration_ms"] > 700],
        "near_full_scale_sample_count": int(near_full.sum()),
        "near_full_scale_fraction": float(np.mean(near_full)),
        "over_full_scale_sample_count": int((np.abs(values) > 1).sum()),
        "longest_near_full_scale_run_ms": max((b - a for a, b in near_runs), default=0) * 1000 / rate,
        "clipping_interpretation": "Potential saturation indicator only; lossy codec overshoot and downmix can obscure clipping.",
    }


def decode_audio(path, output):
    """Decode original sample order; never invent silence for absent media time."""
    import av
    chunks, first_time, cursor, gaps, overlaps = [], None, 0, [], []
    source_peak, source_over, source_count = 0., 0, 0
    with av.open(str(path)) as container:
        if not container.streams.audio:
            raise ValueError("Capture has no audio stream")
        stream = container.streams.audio[0]
        rate = stream.codec_context.sample_rate
        if not rate:
            raise ValueError("Audio stream sample rate is missing")
        resampler = av.AudioResampler(format="fltp", layout=stream.codec_context.layout.name, rate=rate)
        codec = stream.codec_context.name
        missing_pts, media_end_ms, previous_media_end_ms = 0, None, None
        def append(frame):
            nonlocal cursor, first_time, missing_pts, media_end_ms, previous_media_end_ms
            # Average channels instead of a power-preserving downmix matrix:
            # duplicated stereo must not gain 3 dB and create false clipping.
            arr = frame.to_ndarray().mean(axis=0, dtype=np.float64).astype(np.float32)
            if frame.pts is None or frame.time_base is None:
                missing_pts += 1
            else:
                seconds = float(frame.pts * frame.time_base)
                if first_time is None:
                    first_time = seconds
                media_start_ms = seconds * 1000
                if previous_media_end_ms is not None:
                    difference = media_start_ms - previous_media_end_ms
                    if abs(difference) > 2:
                        row = {"media_start_ms": media_start_ms, "sample_offset_ms": cursor * 1000 / rate,
                               "duration_ms": abs(difference)}
                        (gaps if difference > 0 else overlaps).append(row)
                media_end_ms = media_start_ms + len(arr) * 1000 / rate
                previous_media_end_ms = media_end_ms
            chunks.append(arr)
            cursor += len(arr)
        for frame in container.decode(stream):
            original = frame.to_ndarray()
            if np.issubdtype(original.dtype, np.floating):
                source_peak = max(source_peak, float(np.max(np.abs(original))))
                source_over += int((np.abs(original) > 1).sum())
                source_count += original.size
            for mono in resampler.resample(frame):
                append(mono)
        for mono in resampler.resample(None):
            append(mono)
    if not chunks or not cursor:
        raise ValueError("Decoded audio is empty")
    samples = np.concatenate(chunks)
    # Preserve over-scale values in metrics; clamp only the PCM16 review export.
    pcm = np.rint(np.clip(samples, -1, 32767 / 32768) * 32768).astype("<i2")
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    return samples, rate, {"decoder": "PyAV", "version": av.__version__, "codec": codec,
        "decoded_first_pts_ms": None if first_time is None else first_time * 1000,
        "media_end_pts_ms": media_end_ms,
        "media_duration_ms": None if first_time is None or media_end_ms is None else media_end_ms-first_time*1000,
        "missing_pts_frames": missing_pts, "timestamp_gaps": gaps, "timestamp_overlaps": overlaps,
        "sample_timeline": "Contiguous decoded sample order; no samples inserted or removed for timestamp gaps or overlaps",
        "channel_mix": "Arithmetic channel average; no normalization or gain",
        "source_channel_peak_amplitude": source_peak if source_count else None,
        "source_channel_over_full_scale_samples": source_over if source_count else None,
        "pcm16_export": output.name, "pcm16_export_sha256": sha(output),
        "pcm16_export_note": "Mono downmix; values beyond PCM16 range are clamped only in this review copy."}


def recording_anchor(browser, kind="audio"):
    if browser.get("timing_kind") != TIMING_KIND:
        return None, "unknown_browser_clock_contract"
    if not finite(browser.get("performance_origin_ms")) or not finite(browser.get("performance_time_origin_ms")):
        return None, "missing_browser_performance_origin"
    records = [row for row in browser.get("recording", []) if row.get("kind") == kind and finite(row.get("start_ms"))]
    starts = [row for row in browser.get("events", []) if row.get("type") == "recording_started"
              and row.get("kind") == kind and finite(row.get("t_ms"))]
    if len(records) != 1 or len(starts) != 1:
        return None, "missing_or_ambiguous_recorder_start"
    if records[0].get("clock_id", "browser_performance") != starts[0].get("clock_id", "browser_performance"):
        return None, "recorder_clock_mismatch"
    if abs(records[0]["start_ms"] - starts[0]["t_ms"]) > 20:
        return None, "inconsistent_recorder_start"
    return records[0]["start_ms"], None


def align_browser(browser, waveform, decoded):
    start, reason = recording_anchor(browser)
    if decoded.get("missing_pts_frames") or decoded.get("decoded_first_pts_ms") is None:
        return {"status": "unavailable", "reason": "missing_media_pts", "events": []}
    if start is None:
        return {"status": "unavailable", "reason": reason, "events": []}
    recording = next(row for row in browser["recording"] if row.get("kind") == "audio")
    elapsed = recording.get("end_ms", 0) - start
    media_duration = decoded.get("media_duration_ms")
    if not finite(media_duration) or elapsed <= 0:
        return {"status": "unavailable", "reason": "missing_recorder_duration", "events": []}
    difference = elapsed - media_duration
    if abs(difference) > max(200, elapsed * .01):
        return {"status": "unavailable", "reason": "media_duration_does_not_cover_recorder_interval",
                "recorder_elapsed_ms": elapsed, "media_duration_ms": media_duration,
                "unaccounted_recording_time_ms": difference,
                "caution": "The stream may omit silence or start late; recorder start cannot locate samples without a calibration marker.", "events": []}
    if decoded.get("timestamp_gaps") or decoded.get("timestamp_overlaps"):
        return {"status": "unavailable", "reason": "discontinuous_media_sample_clock", "events": []}
    rows = []
    boundary = browser.get("observation_end_ms")
    source_kinds = {"input_started", "input_ended", "audio_reset", "playback_started", "playback_stopped", "playback_idle"}
    for event in browser.get("events", []):
        if event.get("type") not in source_kinds or not finite(event.get("t_ms")):
            continue
        if event.get("clock_id", "browser_performance") != "browser_performance":
            continue
        if finite(boundary) and event["t_ms"] >= boundary:
            continue
        offset = event["t_ms"] - start - decoded["decoded_first_pts_ms"]
        in_capture = 0 <= offset < waveform["duration_ms"]
        row = {"type": event["type"], "browser_t_ms": event["t_ms"], "recording_offset_ms": offset,
               "in_capture": in_capture, "epoch": event.get("epoch"), "step": event.get("step")}
        if in_capture:
            row["waveform_active_at_marker"] = any(s["start_ms"] <= offset < s["end_ms"] for s in waveform["activity_spans"])
            row["active_ms_in_next_250_ms"] = sum(max(0, min(s["end_ms"], offset + 250) - max(s["start_ms"], offset))
                                                   for s in waveform["activity_spans"])
        rows.append(row)
    return {"status": "software_estimate_uncalibrated", "recorder_start_browser_ms": start,
            "media_first_pts_ms": decoded["decoded_first_pts_ms"],
            "clock_reference": "Recorder metadata and recording_started event agree on browser performance timeline",
            "uncertainty": "Codec start and recorder scheduling delay have not been calibrated; do not treat as acoustic interruption latency.",
            "events": rows}


def packet_gaps(browser):
    groups = defaultdict(list)
    boundary = browser.get("observation_end_ms")
    for event in browser.get("events", []):
        if (event.get("type") == "audio" and finite(event.get("t_ms"))
                and (not finite(boundary) or event["t_ms"] < boundary)):
            groups[event.get("epoch", "unknown")].append(event)
    intervals = []
    for epoch, events in groups.items():
        events.sort(key=lambda row: row["t_ms"])
        for previous, current in zip(events, events[1:]):
            intervals.append({"epoch": epoch, "start_ms": previous["t_ms"], "end_ms": current["t_ms"],
                              "duration_ms": current["t_ms"] - previous["t_ms"],
                              "previous_sequence": previous.get("seq"), "next_sequence": current.get("seq")})
    return {"scope": "Browser packet interarrival within each epoch; not waveform silence or playback starvation",
            "packet_count": sum(map(len, groups.values())), "interval_count": len(intervals),
            "max_interarrival_ms": max((row["duration_ms"] for row in intervals), default=None),
            "over_300_ms": [row for row in intervals if row["duration_ms"] > 300],
            "over_700_ms": [row for row in intervals if row["duration_ms"] > 700],
            "caution": "Buffered playback can cover packet gaps; gaps between phrases can also be intentional."}


def contact_sheet(path, output, browser, count=12):
    import av
    from PIL import Image, ImageDraw
    first, last, decoded_frames = None, None, 0
    with av.open(str(path)) as container:
        for frame in container.decode(video=0):
            if frame.pts is None:
                continue
            stamp = float(frame.pts * frame.time_base) * 1000
            first = stamp if first is None else first
            last = stamp
            decoded_frames += 1
    if first is None:
        raise ValueError("No timestamped video frames")
    targets = np.linspace(first, last, count)
    tiles, picked, index = [], [], 0
    anchor, _ = recording_anchor(browser, "face_video")
    if anchor is not None:
        recording = next(row for row in browser["recording"] if row.get("kind") == "face_video")
        elapsed = recording.get("end_ms", 0) - anchor
        if elapsed <= 0 or abs(elapsed - (last-first)) > max(200, elapsed * .01):
            anchor = None
    with av.open(str(path)) as container:
        for frame in container.decode(video=0):
            if frame.pts is None:
                continue
            stamp = float(frame.pts * frame.time_base) * 1000
            while index < count and stamp >= targets[index]:
                picture = frame.to_image().convert("RGB")
                picture.thumbnail((320, 205))
                tile = Image.new("RGB", (336, 243), "#eeeeea")
                tile.paste(picture, ((336-picture.width)//2, 8))
                label = f"media {stamp/1000:.2f}s"
                if anchor is not None:
                    label += f" | browser ~{(anchor+stamp)/1000:.2f}s"
                ImageDraw.Draw(tile).text((8, 222), label, fill="#202020")
                tiles.append(tile)
                picked.append({"media_pts_ms": stamp, "browser_estimate_ms": None if anchor is None else anchor + stamp})
                index += 1
            if index >= count:
                break
    sheet = Image.new("RGB", (336 * 4, 243 * math.ceil(len(tiles)/4)), "#eeeeea")
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % 4) * 336, (index // 4) * 243))
    sheet.save(output)
    return {"file": output.name, "sha256": sha(output), "sampled_frames": picked,
            "decoded_video_frames": decoded_frames, "media_first_pts_ms": first, "media_last_pts_ms": last,
            "scope": "Frame inspection aid; no automated face quality or lip-sync judgment"}


def media_clock_audit(case_dir, browser, threshold_dbfs=-45):
    """Check each actual media stream before treating recorder start as its origin."""
    import av
    rows = []
    for filename, kind in (("browser-output.webm", "audio"), ("face-output.webm", "face_video")):
        path = case_dir / filename
        if not path.exists():
            continue
        records = [row for row in browser.get("recording", []) if row.get("kind") == kind]
        record = records[0] if len(records) == 1 else {}
        anchor, anchor_reason = recording_anchor(browser, kind)
        elapsed = record.get("end_ms", 0) - record.get("start_ms", 0)
        playback = next((e["t_ms"] for e in browser.get("events", []) if e.get("type") == "playback_started" and finite(e.get("t_ms"))), None)
        with av.open(str(path)) as container:
            streams = [(stream.index, stream.type) for stream in container.streams if stream.type in ("audio", "video")]
        for index, stream_kind in streams:
            first, last, end, first_active = None, None, None, None
            count, samples = 0, 0
            with av.open(str(path)) as container:
                for frame in container.decode(container.streams[index]):
                    if frame.pts is None or frame.time_base is None:
                        continue
                    stamp = float(frame.pts * frame.time_base) * 1000
                    first = stamp if first is None else first
                    last = stamp
                    duration = frame.samples * 1000 / frame.sample_rate if stream_kind == "audio" else 0
                    end = stamp + duration
                    count += 1
                    if stream_kind == "audio":
                        samples += frame.samples
                        if first_active is None:
                            values = frame.to_ndarray()
                            if np.issubdtype(values.dtype, np.floating):
                                mono = values.mean(axis=0, dtype=np.float64)
                                if np.sqrt(np.mean(mono * mono)) >= 10 ** (threshold_dbfs / 20):
                                    first_active = stamp
            expected_active = None if anchor is None or playback is None else playback - anchor
            delta = None if expected_active is None or first_active is None else first_active - expected_active
            clock_reasons = []
            if anchor is None:
                clock_reasons.append(anchor_reason)
            if end is None or elapsed <= 0 or abs(elapsed - end) > max(250, elapsed*.01):
                clock_reasons.append("media_end_differs_from_recorder_interval")
            if stream_kind == "audio" and delta is not None and abs(delta) > 150:
                clock_reasons.append("waveform_onset_differs_from_browser_playback")
            rows.append({"file": filename, "sha256": sha(path), "stream_index": index, "stream_kind": stream_kind,
                         "first_pts_ms": first, "last_pts_ms": last, "end_pts_ms": end, "decoded_frames": count,
                         "decoded_audio_samples": samples if stream_kind == "audio" else None,
                         "recorder_elapsed_ms": elapsed, "first_active_frame_pts_ms": first_active,
                         "expected_first_playback_offset_ms": expected_active if stream_kind == "audio" else None,
                         "activity_onset_difference_ms": delta,
                         "browser_clock_alignment": "unverified" if clock_reasons else "approximately_consistent",
                         "clock_cautions": clock_reasons})
    return {"streams": rows, "av_sync_status": "unverified",
            "default_auto_av_sync_claim": False,
            "caution": "A muxed file carries its own stream offsets, but that does not establish agreement with the browser clock or mouth phonemes. Do not combine standalone audio with face video using recorder start alone.",
            "onset_resolution": "RMS activity of decoded frames, typically up to 60 ms; playback_started is a browser estimate, not an acoustic sensor."}


def audit_case(case_dir, *, threshold_dbfs=-45, make_sheet=False):
    browser_path = case_dir / "browser.json"
    browser = json.loads(browser_path.read_text(encoding="utf-8"))
    if browser.get("status") not in ("complete", "completed", "failed", "error", "timeout"):
        return {"case_dir": str(case_dir), "status": "skipped_in_progress"}
    output = case_dir / "audio_capture_audit"
    output.mkdir(exist_ok=True)
    report = {"schema_version": 1, "case_id": browser.get("case_id"), "status": "audited",
              "created_utc": datetime.now(timezone.utc).isoformat(), "source_browser_sha256": sha(browser_path),
              "source_code_sha256": sha(Path(__file__)), "capture_status": browser.get("status"),
              "scope": "Offline digital waveform and media review; no human naturalness score",
              "failures": [], "cautions": [], "human_review": "unrated"}
    audio = case_dir / "browser-output.webm"
    try:
        before = audio.stat()
        report["source_audio_sha256"] = sha(audio)
        metadata_path = case_dir / "audio-recording.json"
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
        if metadata.get("sha256") and metadata["sha256"] != report["source_audio_sha256"]:
            raise ValueError("Capture hash differs from audio-recording.json")
        samples, rate, decoded = decode_audio(audio, output / "decoded-mono.wav")
        if before.st_size != audio.stat().st_size or before.st_mtime_ns != audio.stat().st_mtime_ns:
            raise ValueError("Capture changed during audit")
        waveform = waveform_metrics(samples, rate, threshold_dbfs)
        report.update(waveform=waveform, decoding=decoded,
                      alignment=align_browser(browser, waveform, decoded), packet_interarrival=packet_gaps(browser))
        report["media_clock_audit"] = media_clock_audit(case_dir, browser, threshold_dbfs)
        if waveform["near_full_scale_sample_count"]:
            report["cautions"].append("Near-full-scale samples detected; inspect clipping indicators and listen before judging distortion.")
        if not waveform["non_silent_duration_ms"]:
            report["cautions"].append("No output activity above the configured threshold; expected silence can be correct for this case.")
        if waveform["internal_quiet_over_300_ms"]:
            report["cautions"].append("Internal quiet gaps exceed 300 ms; review their context before calling them glitches.")
        if decoded["timestamp_gaps"] or decoded["timestamp_overlaps"]:
            report["cautions"].append("Media timestamps contain gaps or overlaps; PCM metrics use only decoded sample order. Missing media time is not measured silence.")
        if browser.get("capture_truncated"):
            report["cautions"].append("Browser capture was truncated; the response may be incomplete.")
        report["cautions"].append("RMS and peak measurements cannot assess pronunciation, emotion, prosody, usefulness, or naturalness.")
        if report["alignment"]["status"] != "software_estimate_uncalibrated":
            report["cautions"].append("No usable shared recorder clock reference; browser markers were not aligned to the waveform.")
    except Exception as error:
        report["status"] = "audit_failed"
        report["failures"].append({"stage": "audio", "type": type(error).__name__, "message": str(error)})
    if make_sheet and (case_dir / "face-output.webm").exists():
        try:
            report["video"] = contact_sheet(case_dir / "face-output.webm", output / "face-contact-sheet.jpg", browser)
        except Exception as error:
            report["cautions"].append("Video contact sheet unavailable: " + type(error).__name__ + ": " + str(error))
    (output / "audit.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    return {"case_dir": str(case_dir), "status": report["status"], "report": str(output / "audit.json"),
            "cautions": len(report["cautions"]), "failures": len(report["failures"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+", type=Path)
    parser.add_argument("--threshold-dbfs", type=float, default=-45)
    parser.add_argument("--contact-sheet", action="store_true")
    args = parser.parse_args()
    cases = set()
    for directory in args.directories:
        if (directory / "browser.json").is_file():
            cases.add(directory.resolve())
        else:
            cases.update(path.parent.resolve() for path in directory.glob("*/browser.json"))
    failures = 0
    for case_dir in sorted(cases):
        try:
            result = audit_case(case_dir, threshold_dbfs=args.threshold_dbfs, make_sheet=args.contact_sheet)
        except (OSError, ValueError) as error:
            result = {"case_dir": str(case_dir), "status": "audit_failed", "error_type": type(error).__name__}
        print(json.dumps(result), flush=True)
        failures += result["status"] == "audit_failed"
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
