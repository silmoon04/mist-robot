"""Generate the R5 preview examples and run their offline checks."""
import hashlib
import io
import platform
import unittest

import r5_preview as r5
import test_r5_preview


def main():
    profile = r5.build_profile()
    request = r5.neutral_request(profile)
    r5.write_json(r5.HERE / "r5_profile.json", profile)
    r5.write_json(r5.HERE / "neutral_request.json", request)
    r5.write_json(r5.HERE / "neutral_preview.json", r5.preview(request, profile))
    pan = {"schema_version": 1, "action": "phone_pan",
           "args": {"angle_rad": 0.5, "usb_connected": False}}
    r5.write_json(r5.HERE / "pan_request.json", pan)
    r5.write_json(r5.HERE / "pan_preview.json", r5.preview(pan, profile))
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromModule(test_r5_preview)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (r5.HERE / "validation_results.txt").write_text(stream.getvalue(), encoding="utf-8")
    sources = ("r5_preview.py", "test_r5_preview.py", "run_checks.py", "r5_profile.json",
               "neutral_request.json", "neutral_preview.json", "pan_request.json", "pan_preview.json")
    report = {"passed": result.wasSuccessful(), "tests_run": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors),
              "python_version": platform.python_version(),
              "design_revision": profile["design_revision"],
              "link_dimensions_mm": profile["link_dimensions_mm"],
              "manifest_sha256": profile["manifest_sha256"],
              "file_sha256": {name: hashlib.sha256((r5.HERE / name).read_bytes()).hexdigest()
                              for name in sources},
              "scope": "Local JSON contract validation and command-line refusal only",
              "hardware_accessed": False, "network_used": False,
              "brain_app_started": False, "provider_calls": 0,
              "physical_calibration_or_gait_validated": False}
    r5.write_json(r5.HERE / "validation_results.json", report)
    print(stream.getvalue())
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
