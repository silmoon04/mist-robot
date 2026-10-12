"""Display metadata stays separate from streamed speech and robot actions."""
import unittest
from response_format import ResponsePrefixFilter, strip_expression_prefix


class ResponseFormatTests(unittest.TestCase):
    def test_every_split_preserves_spoken_words_and_emits_one_expression(self):
        source = "[[face:happy]] Hello, Moon."
        for split in range(len(source) + 1):
            stream = ResponsePrefixFilter()
            first, face_a = stream.feed(source[:split])
            second, face_b = stream.feed(source[split:])
            self.assertEqual(first + second + stream.finish(), "Hello, Moon.")
            self.assertEqual([value for value in (face_a, face_b) if value], ["happy"])

    def test_plain_text_is_released_on_its_first_delta(self):
        stream = ResponsePrefixFilter()
        self.assertEqual(stream.feed("Hello"), ("Hello", None))
        self.assertEqual(stream.feed("."), (".", None))

    def test_leading_whitespace_does_not_leak_a_display_marker_to_speech(self):
        source = " \n[[face:happy]] Hello."
        for split in range(len(source) + 1):
            stream = ResponsePrefixFilter()
            first, expression_a = stream.feed(source[:split])
            second, expression_b = stream.feed(source[split:])
            self.assertEqual(first + second + stream.finish(), "Hello.")
            self.assertEqual([value for value in (expression_a, expression_b) if value], ["happy"])

    def test_unknown_action_like_metadata_never_produces_an_expression(self):
        for prefix in ("[[face:walk]]", "[[face:happy;drive(5)]]", "[[face:NEUTRAL]]"):
            self.assertEqual(strip_expression_prefix(prefix + " Stay here."), ("Stay here.", None))

    def test_incomplete_or_oversized_marker_is_not_spoken_and_buffer_stays_bounded(self):
        stream = ResponsePrefixFilter()
        self.assertEqual(stream.feed("[[face:"), ("", None))
        for _ in range(100):
            self.assertEqual(stream.feed("x" * 50), ("", None))
            self.assertLessEqual(len(stream.buffer), 64)
        self.assertEqual(stream.feed("]] Spoken words."), ("Spoken words.", None))
        self.assertEqual(strip_expression_prefix("[[face:hap"), ("", None))

    def test_marker_inside_spoken_text_is_not_an_instruction(self):
        text = "The marker [[face:happy]] is an example."
        self.assertEqual(strip_expression_prefix(text), (text, None))


if __name__ == "__main__":
    unittest.main()
