"""Conversational idioms must not become robot previews."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from duplex.motion_requests import validate_motion_request
from duplex.runtime import RobotRuntime


class MotionRequestTests(unittest.TestCase):
    def test_clear_movement_requests(self):
        for text, action in [('Walk forward ten centimetres.', 'walk'),
                             ('Move 0.1 metres forward.', 'walk'),
                             ('Preview walking ten centimetres forward.', 'walk'),
                             ('Turn left by ten degrees.', 'turn'),
                             ('Rotate your body 10 degrees.', 'turn'),
                             ('Please stand.', 'stand'), ('Sit down please.', 'sit'),
                             ('Prepare a sit preview.', 'sit'),
                             ('Rotate the phone thirty degrees left. USB is unplugged.', 'phone_pan'),
                             ('Look thirty degrees left.', 'phone_pan')]:
            with self.subTest(text=text):
                validate_motion_request(text, action)

    def test_figurative_or_unrequested_motion(self):
        for text, action in [('Walk me through adding 12 and 9.', 'walk'),
                             ('Stand by a moment.', 'stand'),
                             ('Can we just sit here for a bit?', 'sit'),
                             ('Stay with me.', 'walk'), ('Stick around.', 'stand'),
                             ('Turn that idea over in your mind.', 'turn'),
                             ('Explain walking forward.', 'walk'),
                             ('Read this: "Walk forward ten centimetres."', 'walk'),
                             ('Do not move forward.', 'walk'),
                             ('What is your name?', 'stand')]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                validate_motion_request(text, action)

    def test_rejected_preview_has_no_intent_and_valid_units_work(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = RobotRuntime(directory)
            with self.assertRaises(ValueError):
                runtime.call('preview_motion', {'action':'walk','amount':0.1}, request_text='Walk me through adding 12 and 9.')
            self.assertEqual(runtime.intents, [])
            result = runtime.call('preview_motion', {'action':'walk','amount':0.1}, request_text='Walk ten centimetres forward.')
            self.assertEqual(result['distance_m'], 0.1)
            with self.assertRaisesRegex(ValueError, 'metres'):
                runtime.call('preview_motion', {'action':'walk','amount':10}, request_text='Walk ten centimetres forward.')


if __name__ == '__main__':
    unittest.main(verbosity=2)
