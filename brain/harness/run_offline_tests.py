"""Run local contract checks without API keys, model calls or hardware."""
import subprocess
import sys
from pathlib import Path

brain = Path(__file__).resolve().parents[1]
commands = [
    ["node", "--test", "harness/test_robot_tools.mjs"],
    *[[sys.executable, f"harness/{name}.py"] for name in
      ["test_grounding", "test_checks", "test_bench", "test_executive", "test_codex_client", "test_response_format", "test_ui_integration", "test_speech_http_idempotency", "test_streaming_stt", "test_stt_proxy", "test_service_lifecycle", "check_face_map"]],
    ["node", "harness/test_speech_player.mjs"],
    ["node", "harness/test_ui_speech_ownership.mjs"],
    ["node", "--test", "harness/test_talk_session.mjs"],
    ["node", "--test", "harness/test_talk_capture.mjs"],
    ["node", "harness/test_stt_stream.mjs"],
    ["node", "harness/test_talk_recognition.mjs"],
    ["node", "harness/check_face_runtime.cjs"],
    [sys.executable, "harness/elevenlabs_voice_check.py", "--selfcheck"],
    [sys.executable, "ui/server.py", "--selfcheck"],
]
for command in commands:
    print("Running " + " ".join(command), flush=True)
    result = subprocess.run(command, cwd=brain)
    if result.returncode:
        sys.exit(result.returncode)
print("All offline brain checks passed.")
