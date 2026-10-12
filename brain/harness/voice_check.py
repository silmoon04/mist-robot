"""voice_check.py — Deepgram TTS -> STT round trip for HEX-1 replies.

Generates speech for a few in-persona lines with Deepgram Aura-2 TTS, then
transcribes the audio back with Nova-3 STT and scores word-level fidelity.
This validates the output voice path (and gives you .wav files to audition).

Usage: python harness/voice_check.py [--voice aura-2-orion-en] [--lines N]
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import urllib.request
from pathlib import Path

from pi_client import load_env, BRAIN_DIR

TTS_URL = "https://api.deepgram.com/v1/speak?model={voice}&encoding=linear16&container=wav&sample_rate=24000"
STT_URL = "https://api.deepgram.com/v1/listen?model=nova-3&smart_format=false&punctuate=false"

DEFAULT_LINES = [
    "Walking. Thrilling. Two meters closer to the heat death of the universe.",
    "My femur servo is at sixty one degrees. I am told this is fine. I have notes.",
    "Alice. You again. I have prepared a sway of mild menace in your honor.",
]


def norm(s: str) -> list[str]:
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).split()


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def tts(text: str, voice: str, key: str) -> bytes:
    req = urllib.request.Request(
        TTS_URL.format(voice=voice),
        data=json.dumps({"text": text}).encode(),
        headers={"Authorization": f"Token {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def stt(audio: bytes, key: str) -> str:
    req = urllib.request.Request(
        STT_URL,
        data=audio,
        headers={"Authorization": f"Token {key}", "Content-Type": "audio/wav"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    return payload["results"]["channels"][0]["alternatives"][0]["transcript"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="aura-2-orion-en")
    ap.add_argument("--lines", type=int, default=2, help="how many sample lines to round-trip")
    ap.add_argument("--from-results", default=None,
                    help="path to a results.jsonl — use real model replies instead of canned lines")
    args = ap.parse_args()

    key = load_env().get("DEEPGRAM_API_KEY")
    if not key:
        raise SystemExit("DEEPGRAM_API_KEY not found in .env")

    lines = DEFAULT_LINES
    if args.from_results:
        lines = []
        for line in open(args.from_results, encoding="utf-8"):
            r = json.loads(line)
            t = (r.get("reply") or "").strip()
            if 6 <= len(t.split()) <= 40:
                lines.append(t)
        lines = lines[:: max(1, len(lines) // 6)]  # spread through the file
    lines = lines[: args.lines]

    out_dir = BRAIN_DIR / "voice"
    out_dir.mkdir(exist_ok=True)
    print(f"voice={args.voice}, {len(lines)} line(s)\n")
    scores = []
    for i, text in enumerate(lines):
        audio = tts(text, args.voice, key)
        wav = out_dir / f"sample_{i}.wav"
        wav.write_bytes(audio)
        heard = stt(audio, key)
        score = similarity(text, heard)
        scores.append(score)
        print(f"[{i}] fidelity={score:.2f}  ({len(audio) / 1024:.0f} KB -> {wav.name})")
        print(f"    said : {text}")
        print(f"    heard: {heard}\n")
    print(f"mean fidelity: {sum(scores) / len(scores):.2f} (>=0.90 means the TTS is clean)")


if __name__ == "__main__":
    main()
