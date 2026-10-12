"""Pronunciation, measured word bounds, silence and streaming packet contracts."""
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from duplex import phoneme_cues
from duplex.phoneme_cues import phoneme_mouth_cues, word_pronunciation, word_visemes
from duplex.lipsync import slice_cues


RATE = 24000


def voiced(duration):
    # Deterministic loud PCM exercises gating, without pretending it is speech.
    return struct.pack("<h", 6000) * round(duration * RATE)


def alignment(text, start=0, end=.3, normalized=True):
    width = (end - start) * 1000 / len(text)
    return {"normalizedAlignment" if normalized else "alignment": {
        "chars": list(text),
        "charStartTimesMs": [start * 1000 + index * width for index in range(len(text))],
        "charDurationsMs": [width] * len(text),
    }}


class PronunciationTests(unittest.TestCase):
    def test_dictionary_corrects_spelling_traps(self):
        expected = {
            "people": (("P", "IY1", "P", "AH0", "L"), ("MBP", "EE", "MBP", "AA", "LNT")),
            "phone": (("F", "OW1", "N"), ("FV", "OH", "OO", "LNT")),
            "thought": (("TH", "AO1", "T"), ("TH", "OH", "LNT")),
            "enough": (("IH0", "N", "AH1", "F"), ("EE", "LNT", "AA", "FV")),
            "queue": (("K", "Y", "UW1"), ("EH", "EE", "OO")),
            "quiet": (("K", "W", "AY1", "AH0", "T"), ("EH", "OO", "AA", "EE", "AA", "LNT")),
            "knight": (("N", "AY1", "T"), ("LNT", "AA", "EE", "LNT")),
        }
        for word, (phones, shapes) in expected.items():
            with self.subTest(word=word):
                self.assertEqual(word_pronunciation(word), phones)
                self.assertEqual(word_visemes(word), shapes)
                cues, source = phoneme_mouth_cues(voiced(.4), alignment(word + ".", end=.4))
                self.assertIn("estimated_phonemes", source)
                observed = []
                for cue in cues:
                    if not observed or observed[-1] != cue["viseme"]:
                        observed.append(cue["viseme"])
                self.assertEqual(observed[:len(shapes)], list(shapes))

    def test_read_has_two_readings_and_explicit_override(self):
        self.assertEqual(word_pronunciation("read"), ("R", "EH1", "D"))
        self.assertEqual(word_pronunciation("read", variant=1), ("R", "IY1", "D"))
        self.assertEqual(word_visemes("read", overrides={"read": "R IY1 D"}), ("OO", "EE", "LNT"))
        cues, _ = phoneme_mouth_cues(voiced(.4), alignment("read.", end=.4), overrides={"read": "R IY1 D"})
        self.assertIn("EE", {cue["viseme"] for cue in cues})
        self.assertIsNone(word_pronunciation("read", variant=20))
        self.assertIsNone(word_pronunciation("read", overrides={"read": "INVALID"}))

    def test_supplemental_dictionary_supports_new_words(self):
        dictionary = {"zog": [["Z", "AA1", "G"]]}
        self.assertIsNone(word_pronunciation("zog"))
        self.assertEqual(word_visemes("zog", pronunciations=dictionary), ("S", "AA", "EH"))
        cues, source = phoneme_mouth_cues(voiced(.2), alignment("zog.", end=.2), pronunciations=dictionary)
        self.assertIn("estimated_phonemes", source)
        self.assertEqual(cues[0]["viseme"], "S")

    def test_voiced_punctuation_retains_the_final_pronounced_shape(self):
        cues, _ = phoneme_mouth_cues(voiced(.3), alignment("enough.", end=.3))
        self.assertEqual(cues[-1]["viseme"], "FV")

    def test_unknown_and_incomplete_words_keep_character_fallback(self):
        for text in ("wshop.", "people", "ph"):
            with self.subTest(text=text):
                cues, source = phoneme_mouth_cues(voiced(.3), alignment(text))
                self.assertEqual(source, "elevenlabs_characters_audio_gated")
                self.assertGreater(len(cues), 0)
        # The final signal allows a real last word without inventing a suffix.
        cues, source = phoneme_mouth_cues(voiced(.3), alignment("phone"), final=True)
        self.assertIn("estimated_phonemes", source)
        self.assertEqual(cues[0]["viseme"], "FV")

    def test_unknown_whole_tokens_do_not_upgrade_english_substrings(self):
        for text in ("phone2.", "\u00e9phone.", "phone_name."):
            with self.subTest(text=text):
                _, source = phoneme_mouth_cues(voiced(.3), alignment(text))
                self.assertEqual(source, "elevenlabs_characters_audio_gated")

    def test_word_split_across_two_chunks_returns_immediate_fallback(self):
        first, source = phoneme_mouth_cues(voiced(.1), alignment("ph", end=.1))
        self.assertTrue(first)
        self.assertEqual(source, "elevenlabs_characters_audio_gated")
        # 'one' is itself a dictionary word, but here its leading edge is a
        # provider fragment of 'phone'. A new chunk cannot prove that boundary.
        second, source = phoneme_mouth_cues(voiced(.1), alignment("one.", start=.1, end=.2), audio_offset=.1)
        self.assertTrue(second)
        self.assertEqual(source, "elevenlabs_characters_audio_gated")

    def test_absent_or_corrupt_dictionary_is_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dictionary.json"
            with patch.object(phoneme_cues, "DICTIONARY_PATH", path):
                for content in (None, "[1, 2]", "{bad json}"):
                    if content is not None:
                        path.write_text(content, encoding="utf-8")
                    phoneme_cues.bundled_pronunciations.cache_clear()
                    cues, source = phoneme_mouth_cues(voiced(.3), alignment("phone."))
                    self.assertEqual(source, "elevenlabs_characters_audio_gated")
                    self.assertEqual(cues[0]["viseme"], "MBP")
        phoneme_cues.bundled_pronunciations.cache_clear()


class TimingAndAudioTests(unittest.TestCase):
    def test_word_estimates_stay_inside_measured_word_bounds(self):
        message = alignment(" phone. ", start=.08, end=.32)
        cues, source = phoneme_mouth_cues(voiced(.4), message)
        self.assertIn("estimated_phonemes", source)
        measured_start = .08 + .24 / 8
        measured_end = .08 + .24 * 6 / 8
        self.assertEqual(next(cue for cue in cues if cue["time"] == round(measured_start, 6))["viseme"], "FV")
        self.assertTrue(any(cue["viseme"] == "OO" and measured_start <= cue["time"] < measured_end for cue in cues))
        self.assertTrue(all(cue["viseme"] != "FV" for cue in cues if cue["time"] < measured_start))

    def test_silence_overrides_every_dictionary_shape(self):
        raw = voiced(.12) + b"\0\0" * round(.12 * RATE) + voiced(.12)
        cues, _ = phoneme_mouth_cues(raw, alignment("thought.", end=.36))
        silent = [cue for cue in cues if .12 <= cue["time"] < .24]
        self.assertTrue(silent)
        self.assertTrue(all(cue["viseme"] == "rest" and cue["amount"] == 0 for cue in silent))
        self.assertTrue(any(cue["viseme"] == "TH" for cue in cues if cue["time"] < .12))

    def test_voiced_punctuation_keeps_speech_and_silent_punctuation_closes(self):
        message = {"alignment": {"chars": ["a", " ", ",", "b"],
                   "charStartTimesMs": [0, 80, 100, 140], "charDurationsMs": [80, 20, 40, 60]}}
        cues, _ = phoneme_mouth_cues(voiced(.2), message)
        self.assertTrue(all(cue["viseme"] != "rest" for cue in cues))
        raw = voiced(.08) + b"\0\0" * 1440 + voiced(.06)
        cues, _ = phoneme_mouth_cues(raw, message)
        self.assertTrue(all(cue["viseme"] == "rest" for cue in cues if .08 <= cue["time"] < .14))

    def test_zero_duration_overlap_keeps_earlier_active_character(self):
        message = {"alignment": {"chars": ["f", " "], "charStartTimesMs": [0, 20],
                   "charDurationsMs": [100, 0]}}
        cues, source = phoneme_mouth_cues(voiced(.1), message)
        self.assertEqual(source, "elevenlabs_characters_audio_gated")
        self.assertTrue(all(cue["viseme"] == "FV" for cue in cues))

    def test_short_word_retains_bilabial_closure_then_silent_rest(self):
        raw = voiced(.03) + b"\0\0" * round(.05 * RATE)
        message = alignment("up.", end=.03)
        cues, _ = phoneme_mouth_cues(raw, message)
        self.assertTrue(any(cue["viseme"] == "MBP" and 0 < cue["time"] < .03 for cue in cues))
        self.assertTrue(all(cue["viseme"] == "rest" and cue["amount"] == 0 for cue in cues if cue["time"] >= .04))

    def test_cue_slices_preserve_shape_at_packet_start(self):
        cues, _ = phoneme_mouth_cues(voiced(.4), alignment("people.", end=.4))
        start, end = .145, .255
        packet = slice_cues(cues, start, end)
        previous = next(cue for cue in reversed(cues) if cue["time"] <= start)
        self.assertEqual(packet[0], {**previous, "time": 0})
        self.assertEqual(packet[0]["viseme"], "EE")
        self.assertTrue(any(cue["viseme"] == "MBP" for cue in packet))
        self.assertTrue(all(0 <= cue["time"] < end - start for cue in packet))

    def test_clipped_pcm_does_not_refit_the_whole_word(self):
        message = alignment("phone.", end=.3)
        full, _ = phoneme_mouth_cues(voiced(.3), message)
        chunk, source = phoneme_mouth_cues(voiced(.12), message, audio_offset=.12, leading_word_complete=True)
        self.assertIn("estimated_phonemes", source)
        full_at = next(cue for cue in reversed(full) if cue["time"] <= .12)
        self.assertEqual(chunk[0]["viseme"], full_at["viseme"])
        self.assertNotEqual(chunk[0]["viseme"], "FV")
        # An unbounded leading fragment is not promoted to a complete word.
        _, source = phoneme_mouth_cues(voiced(.12), message, audio_offset=.12)
        self.assertEqual(source, "elevenlabs_characters_audio_gated")

    def test_invalid_alignment_falls_back_to_finite_energy_cues(self):
        malformed = (None, {},
            {"chars": ["a"], "charStartTimesMs": [float("nan")], "charDurationsMs": [100]},
            {"chars": ["a"], "charStartTimesMs": [0], "charDurationsMs": [float("inf")]},
            {"chars": ["a"], "charStartTimesMs": [True], "charDurationsMs": [100]},
            {"chars": ["a"], "charStartTimesMs": [-1], "charDurationsMs": [100]},
            {"chars": ["a"], "charStartTimesMs": [0], "charDurationsMs": [-100]},
            {"chars": ["a"], "charStartTimesMs": [1000], "charDurationsMs": [100]},
            {"chars": ["a", "b"], "charStartTimesMs": [80, 0], "charDurationsMs": [20, 80]},
            {"chars": ["a"], "charStartTimesMs": [0], "charDurationsMs": []})
        for bad in malformed:
            with self.subTest(alignment=bad):
                cues, source = phoneme_mouth_cues(voiced(.1), {"alignment": bad})
                self.assertEqual(source, "audio_energy")
                self.assertTrue(all(cue["viseme"] == "AA" for cue in cues))
                self.assertTrue(all(math.isfinite(cue["time"]) and math.isfinite(cue["amount"]) for cue in cues))

    def test_empty_and_silent_audio_are_closed(self):
        self.assertEqual(phoneme_mouth_cues(b"", {}), ([], "audio_energy"))
        cues, _ = phoneme_mouth_cues(b"\0\0" * 2400, alignment("be.", end=.1))
        self.assertTrue(all(cue["viseme"] == "rest" and cue["amount"] == 0 for cue in cues))

    def test_independent_replies_have_no_carried_word_state(self):
        first, _ = phoneme_mouth_cues(voiced(.1), alignment("phone.", end=.1))
        _, source = phoneme_mouth_cues(voiced(.1), alignment("th", end=.1), audio_offset=.1)
        self.assertEqual(source, "audio_energy")
        restarted, _ = phoneme_mouth_cues(voiced(.1), alignment("phone.", end=.1))
        self.assertEqual(restarted, first)
        self.assertEqual(restarted[0]["time"], 0)

    def test_invalid_pcm_clock_rejected_and_valid_cues_strictly_increase(self):
        with self.assertRaises(ValueError):
            phoneme_mouth_cues(b"\0", {})
        for options in ({"rate": 0}, {"rate": float("inf")}, {"audio_offset": -1}, {"audio_offset": float("nan")}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                phoneme_mouth_cues(voiced(.1), {}, **options)
        cues, _ = phoneme_mouth_cues(voiced(.1), alignment("quiet.", end=.1))
        self.assertTrue(all(a["time"] < b["time"] for a, b in zip(cues, cues[1:])))
        self.assertTrue(all(0 <= cue["time"] < .1 and 0 <= cue["amount"] <= 1 for cue in cues))


if __name__ == "__main__":
    unittest.main(verbosity=2)
