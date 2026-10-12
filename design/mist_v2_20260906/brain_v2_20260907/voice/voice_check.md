# MIST voice check

Checked 2026-09-07T00:11:52.292405+00:00.

Existing voice: MIST (refined) (`24AMj4dc02cYAwoUnqzN`).

Word fidelity tests intelligibility. Spelling-derived mouth shapes are approximate; this does not measure voice likeness or perceptual lip sync.

| Clip | Characters | Audio seconds | TTS API seconds | Word score | Timing |
| --- | ---: | ---: | ---: | ---: | --- |
| [1](mist_refined_01.wav) | 56 | 3.1579 | 2.9295 | 0.9 | passed |
| [2](mist_refined_02.wav) | 65 | 3.6223 | 0.8668 | 1.0 | passed |

Clip 1: Hello. I'm MIST. My wheels are ready, and I'm listening.
Heard: hello i'm missed my wheels are ready and i'm listening
Alignment: `elevenlabs_character_timestamps`; 50 mouth events and 3 detected quiet intervals.

Clip 2: One moment, please. I can look left, pause, and look back at you.
Heard: one moment please i can look left pause and look back at you
Alignment: `elevenlabs_character_timestamps`; 57 mouth events and 3 detected quiet intervals.

No currency estimate. Character-cost is recorded only when returned by the provider.

```json
{
  "generated_clips": 2,
  "characters": 121,
  "audio_seconds": 6.7802,
  "tts_api_latency_s": 3.7963,
  "cost_usd": null,
  "provider_billed_characters": 60,
  "transcription_audio_seconds": 6.7802,
  "transcription_api_latency_s": 1.2053
}
```
