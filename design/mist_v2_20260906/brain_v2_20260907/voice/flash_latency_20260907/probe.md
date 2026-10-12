# Responsive voice latency check

Checked 2026-09-07T01:04:39.314822+00:00.

Existing voice: MIST (refined) (`24AMj4dc02cYAwoUnqzN`).

Phrase: One moment, please. I can look left, pause, and look back at you.

Two fresh urllib HTTPS requests using the same existing voice, phrase, PCM24k format and timestamp endpoint. Comparison uses one earlier Multilingual v2 request; it is not a randomized simultaneous benchmark.

| Request | Headers / first body byte | Complete API response | Local processing | Audio duration | Word score |
| --- | ---: | ---: | ---: | ---: | ---: |
| Saved Multilingual v2 | not measured | 0.8668 s | not measured | 3.6223 s | 1.00 |
| [Flash v2.5 #1](mist_flash_01.wav) | 0.9787 / 0.9787 s | 1.0278 s | 0.0098 s | 3.2508 s | 1.00 |
| [Flash v2.5 #2](mist_flash_02.wav) | 0.2969 / 0.2970 s | 0.3457 s | 0.0094 s | 3.3437 s | 1.00 |

The measurements support Flash as the Responsive default, with Multilingual v2 available as Quality. Both Flash clips preserved provider character alignment and passed mouth pause checks. Median API completion was 20.8% lower than the saved baseline. Two requests do not establish a stable latency distribution.

The first Flash request was slower than the saved baseline; the second was faster.

Word checks test intelligibility, not voice likeness. Headers do not separate TLS cost from provider generation. No playback or live UI interaction was performed. No currency estimate.

The transport remains urllib because the measurements do not isolate connection or TLS time.

Usage: 130 input characters, 6.5945 seconds of generated audio, and 32 provider-billed characters. No dollar cost was calculated.

Sources:

- [convert-with-timestamps](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps)
- [models](https://elevenlabs.io/docs/overview/models)
- [latency-optimization](https://elevenlabs.io/docs/eleven-api/guides/how-to/best-practices/latency-optimization)
