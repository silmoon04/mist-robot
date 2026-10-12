"""debug_timeline.py — dump the raw RPC event timeline for one prompt.

Usage: python harness/debug_timeline.py [model[:thinking]] ["prompt"]
"""
import json
import sys
import time

from pi_client import PiClient, BRAIN_DIR

spec = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.5-flash:off"
prompt = sys.argv[2] if len(sys.argv) > 2 else "hey, walk forward two meters"
model, _, thinking = spec.partition(":")
thinking = thinking or "off"

t_spawn = time.monotonic()
c = PiClient(model=model, thinking=thinking, keep_events=True,
             run_dir=BRAIN_DIR / "results" / "debug")
# state check
c._send({"id": "st", "type": "get_state"})
res = c.ask(prompt, timeout=120)
print(f"spawn->done: {time.monotonic() - t_spawn:.2f}s  ask total: {res.total_s:.2f}s")
print(f"ttft={res.ttft_s} ttf_tool={res.ttf_tool_s}")
print(f"text: {res.text!r}")
print(f"tools: {[(t.name, t.args, round(t.t_offset_s, 2), t.is_error) for t in res.tool_calls]}")
print(f"tokens in/out/cache: {res.input_tokens}/{res.output_tokens}/{res.cache_read_tokens} cost=${res.cost_usd:.5f}")
print(f"errors: {res.errors}")
print("--- event timeline ---")
t_prev = None
for ev in res.events_raw:
    et = ev.get("type")
    line = et
    if et == "response":
        line += f" cmd={ev.get('command')} ok={ev.get('success')}"
        if ev.get("command") == "get_state":
            d = ev.get("data", {})
            line += f" model={d.get('model', {}).get('id')} thinking={d.get('thinkingLevel')}"
    elif et == "message_update":
        d = ev.get("assistantMessageEvent", {})
        line += f" {d.get('type')}"
        if d.get("type") in ("text_delta", "thinking_delta"):
            line += f" {d.get('delta', '')[:40]!r}"
    elif et.startswith("tool_execution"):
        line += f" {ev.get('toolName')}"
    elif et == "message_end":
        m = ev.get("message", {})
        line += f" role={m.get('role')} stop={m.get('stopReason')} usage={m.get('usage', {}).get('input')}/{m.get('usage', {}).get('output')}"
    print(line)
c.close()
