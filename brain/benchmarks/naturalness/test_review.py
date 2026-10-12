import copy
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("naturalness_review", Path(__file__).with_name("review.py"))
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.left = {"manifest": {"suite_sha256": "hash", "adapter": "adapter", "run_id": "private-left", "config": {"model": "private-model"}},
                     "samples": [{"case_id": "case", "repeat": 0, "status": "completed", "turns": [{"user": "hello", "text": "Hi", "tools": []}]}]}
        self.right = copy.deepcopy(self.left)
        self.right["manifest"]["run_id"] = "private-right"
        self.right["samples"][0]["turns"][0]["text"] = "Hello there"

    def pack(self):
        result = review.build_review(self.left, self.right, self.root / "pack")
        html = Path(result["review_path"]).read_text(encoding="utf-8")
        payload = json.loads(re.search(r'<script id="pack" type="application/json">(.*?)</script>', html, re.S).group(1))
        return result, html, payload

    def test_blinded_and_deterministic(self):
        result, html, payload = self.pack()
        for secret in ("private-left", "private-right", "private-model", "suite_sha256", "case_id", "answer_key.json"):
            self.assertNotIn(secret, html)
        again = review.build_review(self.left, self.right, self.root / "again")
        self.assertEqual(result["pack_sha256"], again["pack_sha256"])
        self.assertEqual(html, Path(again["review_path"]).read_text(encoding="utf-8"))
        key = json.loads(Path(result["answer_key_path"]).read_text())
        self.assertEqual(set(key["pairs"][0]["mapping"].values()), {"baseline", "candidate"})
        self.assertEqual(payload["pairs"][0]["view_mode"], "text-only")

    def test_hostile_transcript_is_data(self):
        attack = '</script><script>alert("bad")</script>&<img src=x>'
        self.left["samples"][0]["turns"][0]["text"] = attack
        _, html, payload = self.pack()
        self.assertNotIn(attack, html)
        self.assertIn(attack, [o["turns"][0]["text"] for o in payload["pairs"][0]["options"].values()])
        self.assertNotIn("innerHTML", html)

    def test_mismatched_adapter_or_suite_rejected(self):
        for field in ("adapter", "suite_sha256"):
            other = copy.deepcopy(self.right)
            other["manifest"][field] = "different"
            with self.assertRaisesRegex(ValueError, field):
                review.build_review(self.left, other, self.root / "bad")

    def test_duplicate_and_missing_pairs_rejected(self):
        other = copy.deepcopy(self.right)
        other["samples"].append(other["samples"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            review.build_review(self.left, other, self.root / "bad")
        self.right["samples"][0]["repeat"] = 1
        with self.assertRaisesRegex(ValueError, "exactly"):
            self.pack()

    def test_audio_copied_without_source_name(self):
        source = self.root / "private-model-audio.wav"
        source.write_bytes(b"RIFFtest")
        self.left["samples"][0]["audio_path"] = str(source)
        result, html, payload = self.pack()
        self.assertNotIn(source.name, html)
        option = next(o for o in payload["pairs"][0]["options"].values() if "audio" in o)
        self.assertEqual((self.root / "pack" / option["audio"]).read_bytes(), b"RIFFtest")
        self.assertEqual(result["audio_files"], 1)
        self.assertEqual(option["view_mode"], "text-and-audio")

    def test_remote_or_missing_audio_rejected(self):
        for path in ("https://example.com/voice.wav", str(self.root / "absent.wav")):
            self.left["samples"][0]["audio_path"] = path
            with self.assertRaisesRegex(ValueError, "local audio"):
                self.pack()

    def test_inputs_not_mutated(self):
        original = copy.deepcopy(self.left)
        self.pack()
        self.assertEqual(self.left, original)

    def test_incomplete_or_unsupported_samples_rejected(self):
        for status in (None, "unsupported", "failed", "partial"):
            self.left["samples"][0]["status"] = status
            with self.assertRaisesRegex(ValueError, "not completed"):
                self.pack()

    def test_partial_turns_and_empty_transcript_rejected(self):
        sample = self.left["samples"][0]
        sample.update(expected_turns=2, completed_turns=1)
        with self.assertRaisesRegex(ValueError, "turn counts"):
            self.pack()
        sample["completed_turns"] = 2
        sample["turns"] = []
        with self.assertRaisesRegex(ValueError, "no completed conversation"):
            self.pack()

    def test_explicit_full_conversation_audio_only_allowed(self):
        source = self.root / "conversation.wav"
        source.write_bytes(b"RIFFtest")
        self.left["samples"][0].update(turns=[], audio_path=str(source), audio_only=True, audio_scope="conversation")
        result, _, _ = self.pack()
        self.assertEqual(result["audio_files"], 1)

    def test_same_partial_subset_cannot_look_like_a_complete_planned_review(self):
        for run in (self.left, self.right):
            run["manifest"].update(selected_case_ids=["case", "missing"], repeats=2)
            run["samples"][0]["repeat"] = 1
        with self.assertRaisesRegex(ValueError, "Baseline planned coverage.*expected=4.*missing=3"):
            self.pack()
        self.assertFalse((self.root / "pack").exists())

    def test_candidate_missing_plan_is_identified_before_matching_present_pairs(self):
        for run in (self.left, self.right):
            run["manifest"].update(selected_case_ids=["case"], repeats=1)
            run["samples"][0]["repeat"] = 1
        self.right["manifest"]["repeats"] = 2
        with self.assertRaisesRegex(ValueError, "Candidate planned coverage.*missing=1"):
            self.pack()

    def test_planned_complete_run_is_allowed(self):
        for run in (self.left, self.right):
            run["manifest"].update(selected_case_ids=["case"], repeats=1)
            run["samples"][0].update(repeat=1, expected_turns=1, completed_turns=1)
        self.assertEqual(self.pack()[0]["pairs"], 1)

    def test_declared_complete_counts_cannot_hide_missing_transcript_turns(self):
        self.left["samples"][0].update(expected_turns=2, completed_turns=2)
        with self.assertRaisesRegex(ValueError, "turn counts do not match"):
            self.pack()

    def test_existing_review_or_key_never_overwritten(self):
        result, _, _ = self.pack()
        before = Path(result["answer_key_path"]).read_bytes()
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.pack()
        self.assertEqual(Path(result["answer_key_path"]).read_bytes(), before)
        separate = self.root / "key-only"
        separate.mkdir()
        (separate / "answer_key.json").write_text("existing evidence")
        with self.assertRaisesRegex(ValueError, "already exists"):
            review.build_review(self.left, self.right, separate)
        self.assertFalse((separate / "review.html").exists())


if __name__ == "__main__":
    unittest.main()
