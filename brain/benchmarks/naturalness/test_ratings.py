import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("naturalness_ratings", Path(__file__).with_name("ratings.py"))
ratings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ratings)


class RatingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.key = {"pack_sha256": "pack", "pairs": [
            {"pair_id": "p1", "case_id": "case1", "repeat": 0, "mapping": {"A": "candidate", "B": "baseline"}},
            {"pair_id": "p2", "case_id": "case2", "repeat": 0, "mapping": {"A": "baseline", "B": "candidate"}}]}
        self.row = {"pair_id": "p1", "view_mode": "text-only", "preference": "A", "note": "Turn 2 felt abrupt", "options": {
            "A": {"view_mode": "text-only", "ratings": {"usefulness": "5", "emotional_fit": "unassessable"}},
            "B": {"view_mode": "text-only", "ratings": {"usefulness": "2"}}}}

    def file(self, rows=None, name="one.json", pack="pack"):
        path = self.root / name
        path.write_text(json.dumps({"pack_sha256": pack, "reviews": [self.row] if rows is None else rows}))
        return path

    def test_reversed_mapping_and_missing(self):
        result = ratings.aggregate_reviews(self.key, [self.file()])
        self.assertEqual(result["preferences"]["candidate"], 1)
        self.assertEqual(result["dimensions"]["usefulness"]["candidate_minus_baseline_mean"], 3)
        self.assertEqual(result["sources"][0]["missing_pairs"], ["p2"])
        self.assertEqual(result["observations"][0]["note"], "Turn 2 felt abrupt")
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_unassessable_not_zero(self):
        result = ratings.aggregate_reviews(self.key, [self.file()])
        self.assertIsNone(result["dimensions"]["emotional_fit"]["candidate_minus_baseline_mean"])
        self.assertEqual(result["dimensions"]["emotional_fit"]["paired_observations"], 0)

    def test_wrong_pack_and_unknown_pair(self):
        with self.assertRaisesRegex(ValueError, "different review pack"):
            ratings.aggregate_reviews(self.key, [self.file(pack="other")])
        self.row["pair_id"] = "unknown"
        with self.assertRaisesRegex(ValueError, "Unknown review pair"):
            ratings.aggregate_reviews(self.key, [self.file()])

    def test_duplicate_export_or_pair_rejected(self):
        path = self.file()
        with self.assertRaisesRegex(ValueError, "Duplicate ratings export"):
            ratings.aggregate_reviews(self.key, [path, self.file(name="copy.json")])
        with self.assertRaisesRegex(ValueError, "Duplicate pair review"):
            ratings.aggregate_reviews(self.key, [self.file(rows=[self.row, self.row])])

    def test_unsupported_media_ratings_rejected(self):
        for dimension in ("voice_quality", "speech_timing", "expressions"):
            self.row["options"]["A"]["ratings"] = {dimension: "4"}
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                ratings.aggregate_reviews(self.key, [self.file()])
        self.row["options"]["A"]["view_mode"] = "text-and-audio"
        with self.assertRaisesRegex(ValueError, "evidence mode"):
            ratings.aggregate_reviews(self.key, [self.file()])

    def test_verified_conversation_audio_permits_timing(self):
        self.key["pairs"][0]["evidence_modes"] = {
            "A": {"view_mode": "text-and-audio", "conversation_audio": True},
            "B": {"view_mode": "text-only", "conversation_audio": False}}
        self.row["view_mode"] = "audio-available"
        self.row["options"]["A"] = {"view_mode": "text-and-audio", "ratings": {"speech_timing": "4"}}
        result = ratings.aggregate_reviews(self.key, [self.file()])
        self.assertEqual(result["observations"][0]["ratings"]["candidate"]["speech_timing"], 4)
        self.assertEqual(result["dimensions"]["speech_timing"]["paired_observations"], 0)

    def test_preferences_and_two_sources(self):
        other = copy.deepcopy(self.row)
        other.update(pair_id="p2", preference="B")
        result = ratings.aggregate_reviews(self.key, [self.file(), self.file(rows=[other], name="two.json")])
        self.assertEqual(result["preferences"]["candidate"], 2)
        self.assertEqual(result["rater_source_files"], 2)
        self.assertEqual(result["dimensions"]["usefulness"]["candidate_minus_baseline_mean"], 0)

    def test_invalid_scores_rejected(self):
        for value in (True, 0, 6, "nan", 2.5):
            self.row["options"]["A"]["ratings"]["usefulness"] = value
            with self.assertRaisesRegex(ValueError, "Rating must"):
                ratings.aggregate_reviews(self.key, [self.file()])


if __name__ == "__main__":
    unittest.main()
