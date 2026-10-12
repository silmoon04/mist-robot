"""Speech audio and mouth cues, using only the Python standard library.

Event times are seconds from the beginning of the returned WAV. Character
timings come from ElevenLabs; mouth shapes are spelling approximations, not
provider phoneme labels. Deepgram timings are explicitly estimated.
"""
from __future__ import annotations

import base64
import binascii
import io
import json
import math
import os
import re
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from collections.abc import Mapping


DEFAULT_ELEVENLABS_VOICE = "24AMj4dc02cYAwoUnqzN"
DEFAULT_ELEVENLABS_LABEL = "MIST (refined)"
DEFAULT_ELEVENLABS_MODEL = "eleven_flash_v2_5"
ELEVENLABS_MODELS = (
    {"id": "eleven_flash_v2_5", "label": "Responsive"},
    {"id": "eleven_multilingual_v2", "label": "Quality"},
)
DEFAULT_DEEPGRAM_VOICE = "aura-2-cora-en"
MAX_TEXT_CHARACTERS = 1500
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
VISEMES = frozenset(("rest", "AA", "EH", "EE", "OH", "OO", "MBP", "FV", "LNT", "S"))


class SpeechError(Exception):
    """Safe to include in a local JSON response; contains no upstream body."""

    def __init__(self, code: str, message: str, http_status: int = 502):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _setting(env: Mapping[str, str], name: str, default: str = "") -> str:
    value = env.get(name) or os.environ.get(name) or default
    return str(value).strip().strip("\"'")


def speech_config(env: Mapping[str, str]) -> dict:
    voice_id = (_setting(env, "MIST_ELEVENLABS_VOICE_ID")
                or _setting(env, "ELEVENLABS_VOICE_ID", DEFAULT_ELEVENLABS_VOICE))
    eleven = bool(_setting(env, "ELEVENLABS_API_KEY") and voice_id)
    deepgram = bool(_setting(env, "DEEPGRAM_API_KEY"))
    return {
        "elevenlabs_available": eleven,
        "elevenlabs_voice_id": voice_id,
        "elevenlabs_voice_label": (DEFAULT_ELEVENLABS_LABEL if voice_id == DEFAULT_ELEVENLABS_VOICE
                                  else "Configured ElevenLabs voice"),
        "elevenlabs_model_id": _setting(env, "ELEVENLABS_MODEL_ID", DEFAULT_ELEVENLABS_MODEL),
        "elevenlabs_models": [dict(model) for model in ELEVENLABS_MODELS],
        "deepgram_available": deepgram,
        "default_provider": "elevenlabs" if eleven else ("deepgram" if deepgram else None),
        "max_text_characters": MAX_TEXT_CHARACTERS,
    }


def _request(url: str, body: bytes, headers: dict, provider: str) -> tuple[bytes, dict, dict]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            headers_at = time.perf_counter()
            first = response.read(1)
            first_byte_at = time.perf_counter()
            raw = first + response.read(MAX_RESPONSE_BYTES + 1 - len(first))
            body_at = time.perf_counter()
            response_headers = {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()
        raise SpeechError("provider_http_error", f"{provider} returned HTTP {status}") from None
    except (urllib.error.URLError, OSError, TimeoutError):
        raise SpeechError("provider_unreachable", f"{provider} could not be reached") from None
    except ValueError:
        raise SpeechError("invalid_provider_configuration", f"{provider} configuration is invalid", 503) from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise SpeechError("response_too_large", f"{provider} returned too much audio")
    return raw, response_headers, {
        "api_latency_s": round(body_at - started, 4),
        "api_headers_s": round(headers_at - started, 4),
        "api_first_byte_s": round(first_byte_at - started, 4),
        "api_body_s": round(body_at - headers_at, 4),
    }


def _wav_from_pcm(pcm: bytes, sample_rate: int = 24000) -> bytes:
    if not pcm or len(pcm) % 2:
        raise SpeechError("invalid_audio", "Speech provider returned invalid PCM audio")
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return output.getvalue()


def _audio_info(audio: bytes) -> tuple[float, list[tuple[float, float]]]:
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            frames, rate = wav.getnframes(), wav.getframerate()
            if not frames or not rate or wav.getsampwidth() != 2 or wav.getnchannels() != 1:
                raise ValueError("expected mono PCM16")
            samples = [sample[0] for sample in struct.iter_unpack("<h", wav.readframes(frames))]
    except (wave.Error, EOFError, ValueError, struct.error):
        raise SpeechError("invalid_audio", "Speech provider returned an unreadable WAV") from None
    duration = len(samples) / rate
    if not duration:
        raise SpeechError("invalid_audio", "Speech provider returned empty audio")
    window = max(1, round(rate * 0.02))
    levels = [math.sqrt(sum(value * value for value in samples[i:i + window]) /
                        len(samples[i:i + window])) for i in range(0, len(samples), window)]
    threshold = max(45.0, max(levels, default=0) * 0.025)
    silences = []
    start = None
    for i, level in enumerate(levels + [threshold + 1]):
        if level < threshold and start is None:
            start = i * window / rate
        elif level >= threshold and start is not None:
            end = min(duration, i * window / rate)
            if end - start >= 0.10 or (start == 0 or end == duration) and end - start >= 0.04:
                silences.append((round(start, 4), round(end, 4)))
            start = None
    return duration, silences


def _viseme(character: str, following: str = "") -> str:
    if not character:
        return "rest"
    pair = (character + following).lower()
    if pair[:2] in ("ee", "ea", "ie", "ey"):
        return "EE"
    if pair[:2] in ("oo", "ou", "ow", "ue"):
        return "OO"
    if pair[:2] in ("sh", "ch"):
        return "S"
    if pair[:2] in ("th", "dh"):
        return "LNT"
    char = character.lower()
    for letters, shape in (("a", "AA"), ("e", "EH"), ("iy", "EE"), ("o", "OH"),
                           ("uwqr", "OO"), ("mbp", "MBP"), ("fv", "FV"),
                           ("lntd", "LNT"), ("szcxjg", "S"), ("hk", "EH")):
        if char in letters:
            return shape
    return "EH" if character.isalnum() else "rest"


def _alignment_spans(alignment: dict | None, duration: float) -> list[tuple[str, float, float]]:
    if not isinstance(alignment, dict):
        return []
    characters = alignment.get("characters")
    starts = alignment.get("character_start_times_seconds")
    ends = alignment.get("character_end_times_seconds")
    if not all(isinstance(values, list) for values in (characters, starts, ends)):
        return []
    if not len(characters) == len(starts) == len(ends):
        return []
    spans = []
    previous = 0.0
    for char, start, end in zip(characters, starts, ends):
        if not isinstance(char, str) or not isinstance(start, (float, int)) or not isinstance(end, (float, int)):
            return []
        if not math.isfinite(start) or not math.isfinite(end) or start < previous or end < start:
            return []
        spans.append((char, min(duration, max(0.0, start)), min(duration, max(0.0, end))))
        previous = start
    return spans


def _estimated_spans(text: str, duration: float) -> list[tuple[str, float, float]]:
    weights = [2.5 if char in ".!?;:" else (1.1 if char.isspace() else 1.0) for char in text]
    lead = min(0.08, duration * 0.04)
    unit = max(0.0, duration - 2 * lead) / max(sum(weights), 1)
    spans = []
    cursor = lead
    for char, weight in zip(text, weights):
        end = min(duration, cursor + weight * unit)
        spans.append((char, cursor, end))
        cursor = end
    return spans


def _mouth_events(spans: list, duration: float, silences: list) -> list[dict]:
    candidates = [(0.0, "rest")]
    previous_end = 0.0
    consumed = -1
    for index, (char, start, end) in enumerate(spans):
        if start - previous_end >= 0.06:
            candidates.append((previous_end, "rest"))
        previous_end = max(previous_end, end)
        if index == consumed:
            continue
        following = spans[index + 1][0] if index + 1 < len(spans) else ""
        shape = _viseme(char, following)
        if (char + following).lower() in ("ee", "ea", "ie", "ey", "oo", "ou", "ow", "ue", "sh", "ch", "th", "dh"):
            consumed = index + 1
        candidates.append((start, shape))
    candidates.extend(((previous_end, "rest"), (duration, "rest")))
    candidates = [(at, shape) for at, shape in candidates
                  if not any(start <= at < end for start, end in silences)]
    for start, end in silences:
        candidates.append((start, "rest"))
        active = next(((char, at, stop) for char, at, stop in spans if at <= end < stop), None)
        if active:
            candidates.append((end, _viseme(active[0])))
    events = []
    for at, shape in sorted(candidates, key=lambda item: item[0]):
        event = {"time": round(min(duration, max(0.0, at)), 4), "viseme": shape,
                 "amount": 0.0 if shape == "rest" else (0.35 if shape == "MBP" else 0.8)}
        if events and event["time"] == events[-1]["time"]:
            events[-1] = event
        elif not events or event["viseme"] != events[-1]["viseme"] or at == duration:
            events.append(event)
    return events


def generate_speech(text: str, provider: str | None, voice: str | None,
                    env: Mapping[str, str], model: str | None = None) -> dict:
    """Generate one clip. An explicit model overrides the configured speech model.

    Provider failures are returned to the caller without retrying.
    """
    started = time.perf_counter()
    if not isinstance(text, str) or not text.strip():
        raise SpeechError("empty_text", "Speech text is required", 400)
    text = text.strip()
    if len(text) > MAX_TEXT_CHARACTERS:
        raise SpeechError("text_too_long", f"Speech text is limited to {MAX_TEXT_CHARACTERS} characters", 413)
    config = speech_config(env)
    provider = provider or config["default_provider"]
    if provider == "auto":
        provider = config["default_provider"]
    if provider not in ("elevenlabs", "deepgram"):
        raise SpeechError("provider_unavailable", "Select a configured speech provider", 503)
    alignment = None
    if provider == "elevenlabs":
        key = _setting(env, "ELEVENLABS_API_KEY")
        if not key:
            raise SpeechError("missing_api_key", "ElevenLabs is not configured", 503)
        voice_id = config["elevenlabs_voice_id"]
        if voice and voice != voice_id:
            raise SpeechError("voice_not_configured", "Choose the configured ElevenLabs voice", 400)
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", voice_id):
            raise SpeechError("invalid_voice", "Configured ElevenLabs voice ID is invalid", 503)
        requested_model = model
        model = model or config["elevenlabs_model_id"]
        if model not in tuple(item["id"] for item in ELEVENLABS_MODELS):
            raise SpeechError("invalid_model", "Choose the Responsive or Quality speech model",
                              400 if requested_model is not None else 503)
        url = "https://api.elevenlabs.io/v1/text-to-speech/" + urllib.parse.quote(voice_id, safe="") + "/with-timestamps?output_format=pcm_24000"
        raw, headers, timings = _request(url, json.dumps({"text": text, "model_id": model}).encode("utf-8"),
                                        {"xi-api-key": key, "Content-Type": "application/json"}, provider)
        try:
            payload = json.loads(raw)
            pcm = base64.b64decode(payload["audio_base64"], validate=True)
            alignment = payload.get("normalized_alignment") or payload.get("alignment")
        except (ValueError, KeyError, TypeError, binascii.Error, AttributeError):
            raise SpeechError("invalid_response", "ElevenLabs returned an unreadable speech response") from None
        audio = _wav_from_pcm(pcm)
    else:
        key = _setting(env, "DEEPGRAM_API_KEY")
        if not key:
            raise SpeechError("missing_api_key", "Deepgram is not configured", 503)
        voice_id = voice or DEFAULT_DEEPGRAM_VOICE
        if not isinstance(voice_id, str) or not re.fullmatch(r"aura-(?:2-)?[a-z]+-en", voice_id):
            raise SpeechError("invalid_voice", "Choose a Deepgram English Aura voice", 400)
        model = voice_id
        url = "https://api.deepgram.com/v1/speak?" + urllib.parse.urlencode({
            "model": voice_id, "encoding": "linear16", "container": "wav", "sample_rate": 24000})
        audio, headers, timings = _request(url, json.dumps({"text": text}).encode("utf-8"),
                                          {"Authorization": f"Token {key}", "Content-Type": "application/json"}, provider)
    duration, silences = _audio_info(audio)
    spans = _alignment_spans(alignment, duration)
    source = "elevenlabs_character_timestamps" if spans else "text_estimate_audio_duration"
    if not spans:
        spans = _estimated_spans(text, duration)
    usage = {"characters": len(text), "audio_seconds": round(duration, 4),
             **timings, "audio_bytes": len(audio), "cost_usd": None}
    character_cost = headers.get("character-cost", "")
    if str(character_cost).isdigit():
        usage["provider_billed_characters"] = int(character_cost)
    result = {
        "audio_base64": base64.b64encode(audio).decode("ascii"),
        "mime_type": "audio/wav", "duration_s": round(duration, 4),
        "events": _mouth_events(spans, duration, silences),
        "alignment_source": source, "viseme_method": "spelling_shapes_with_audio_silence_gate",
        "silences": [{"start": start, "end": end} for start, end in silences],
        "provider": provider, "voice_id": voice_id, "model_id": model,
        "usage": usage,
    }
    usage["generation_total_s"] = round(time.perf_counter() - started, 4)
    usage["local_processing_s"] = round(max(0, usage["generation_total_s"] - usage["api_latency_s"]), 4)
    return result
