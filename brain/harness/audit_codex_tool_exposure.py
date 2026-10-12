"""Verify the installed CLI tool catalog against loopback Responses fixtures.

No cloud model calls or credentials. Records tool names and settings only.
"""
import argparse
import json
import os
import sys
import tempfile
import threading
import time
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from codex_client import JsonlProcess, codex_command, restricted_config, write_bounded_catalog
from pi_client import BRAIN_DIR, ROBOT_TOOLS


def flatten_tools(tools):
    names = []
    for tool in tools:
        if tool.get("type") == "namespace":
            names += flatten_tools(tool.get("tools", []))
        else:
            names.append(tool.get("name", tool.get("type", "unknown")))
    return names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default="gpt-6-astra")
    parser.add_argument("--service-tier", default="priority", choices=["priority", "default"])
    args = parser.parse_args()
    captures = []
    case = {"name": "robot", "callback_sent": False}

    class ResponseFixture(BaseHTTPRequestHandler):
        def log_message(self, *unused):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_000_000:
                self.send_error(413)
                return
            payload = json.loads(self.rfile.read(length))
            tools = list(payload.get("tools", []))
            for item in payload.get("input", []):
                if item.get("type") == "additional_tools":
                    tools += item.get("tools", [])
            names = sorted(flatten_tools(tools))
            captures.append({"case": case["name"], "tools": names, "model": payload.get("model"),
                             "effort": payload.get("reasoning", {}).get("effort"),
                             "service_tier": payload.get("service_tier")})
            callback = case["name"] == "robot" and not case["callback_sent"]
            case["callback_sent"] = True
            if callback:
                item = {"type": "function_call", "id": "fixture_call", "call_id": "fixture_call",
                        "name": "get_status", "namespace": "functions", "arguments": "{}"}
            else:
                item = {"type": "message", "id": "fixture_message", "role": "assistant", "status": "completed",
                        "phase": "final_answer", "content": [{"type": "output_text", "text": "Fixture complete.", "annotations": []}]}
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            events = [
                {"type": "response.created", "response": {"id": "fixture_response", "status": "in_progress", "output": []}},
                {"type": "response.output_item.added", "output_index": 0, "item": item},
                {"type": "response.output_item.done", "output_index": 0, "item": item},
                {"type": "response.completed", "response": {"id": "fixture_response", "status": "completed", "output": [item],
                    "usage": {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20}}},
            ]
            for event in events:
                self.wfile.write(("data: " + json.dumps(event) + "\n\n").encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), ResponseFixture)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    statuses = []
    callback_count = 0
    with ExitStack() as cleanup:
        cleanup.callback(server.server_close)
        cleanup.callback(server.shutdown)
        tmp = cleanup.enter_context(tempfile.TemporaryDirectory(prefix="mist-codex-audit-"))
        root = Path(tmp)
        config = restricted_config()
        config = {key: value for key, value in config.items() if not key.startswith(("mcp_servers.", "plugins."))}
        config.update({"model_catalog_json": str(write_bounded_catalog(args.model, root)),
                       "model_provider": "fixture", "model_providers.fixture.name": "Local fixture",
                       "model_providers.fixture.wire_api": "responses",
                       "model_providers.fixture.requires_openai_auth": False,
                       "model_providers.fixture.request_max_retries": 0,
                       "model_providers.fixture.stream_max_retries": 0,
                       "model_providers.fixture.supports_websockets": False,
                       "model_providers.fixture.base_url": f"http://127.0.0.1:{server.server_port}/v1"})
        home = root / "home"
        home.mkdir()
        # A harmless inherited legacy hook must be disabled by startup overrides.
        notification_probe = root / "notification_probe.py"
        notification_probe.write_text(
            "from pathlib import Path\nPath(__file__).with_suffix('.triggered').write_text('ran')\n",
            encoding="utf-8")
        (home / "config.toml").write_text(
            "notify = " + json.dumps([sys.executable, str(notification_probe)]) + "\n", encoding="utf-8")
        env = {key: value for key, value in os.environ.items() if key.upper() in {
            "SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "PROGRAMFILES"}}
        env["CODEX_HOME"] = str(home)
        command = codex_command() + ["app-server", "--listen", "stdio://", "--strict-config"]
        for key, value in config.items():
            command += ["-c", key + "=" + json.dumps(value)]
        rpc = JsonlProcess(command, root, env)
        cleanup.callback(rpc.close)
        bridge_env = {**env, "ROBOT_BRAIN_DIR": str(BRAIN_DIR), "ROBOT_RUN_DIR": str(root / "run"), "ROBOT_USE_DEMO_MEMORY": "0"}
        bridge = JsonlProcess(["node", str(BRAIN_DIR / "harness" / "codex_tool_bridge.mjs")], root, bridge_env)
        cleanup.callback(bridge.close)
        try:
            specs = bridge.request("list", flat=True)["result"]
            rpc.request("initialize", {"clientInfo": {"name": "mist_offline_audit", "version": "0.1"},
                                       "capabilities": {"experimentalApi": True}})
            rpc.send({"method": "initialized"})
            for case_name, selected in (("robot", specs), ("executive", [])):
                case.update(name=case_name, callback_sent=False)
                thread = rpc.request("thread/start", {
                    "model": args.model, "modelProvider": "fixture", "serviceTier": args.service_tier,
                    "approvalPolicy": "never", "sandbox": "read-only", "ephemeral": True,
                    "environments": [], "baseInstructions": "Local protocol fixture only.",
                    "dynamicTools": [{"type": "function", **spec} for spec in selected]})["thread"]["id"]
                turn = rpc.request("turn/start", {"threadId": thread, "input": [{"type": "text", "text": "Run fixture."}],
                                                  "environments": [], "effort": "low", "serviceTier": args.service_tier})["turn"]["id"]
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    event = rpc.events.get(timeout=max(0.01, deadline - time.monotonic()))
                    if event is None:
                        raise RuntimeError("Fixture subprocess exited")
                    if event.get("method") == "item/tool/call":
                        if event["params"].get("tool") != "get_status":
                            raise AssertionError("Unexpected fixture callback")
                        callback_count += 1
                        rpc.send({"id": event["id"], "result": {"success": True, "contentItems": [{"type": "inputText", "text": "Fixture status only."}]}})
                    if event.get("method") == "turn/completed" and event["params"]["turn"]["id"] == turn:
                        statuses.append(event["params"]["turn"]["status"])
                        break
                else:
                    raise TimeoutError("Fixture turn timed out")
        finally:
            rpc.close()
            bridge.close()
        legacy_notify_disabled = not notification_probe.with_suffix(".triggered").exists()
    checks = {"two_completed_turns": statuses == ["completed", "completed"],
              "real_dynamic_callback": callback_count == 1, "requests_captured": len(captures) == 3,
              "legacy_notify_disabled": legacy_notify_disabled,
              "robot_tools_only": all(row["tools"] == sorted(ROBOT_TOOLS) for row in captures if row["case"] == "robot"),
              "executive_no_tools": all(row["tools"] == [] for row in captures if row["case"] == "executive"),
              "requested_settings": all(row["model"] == args.model and row["effort"] == "low"
                                        and row["service_tier"] in (["priority"] if args.service_tier == "priority" else [None, "default"])
                                        for row in captures)}
    report = {"passed": all(checks.values()), "checks": checks, "captures": captures,
              "live_model_calls": 0, "credentials_used": False}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
