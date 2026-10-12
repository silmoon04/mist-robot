"""long_convo.py — 40-turn conversation simulation in ONE session.

Tests context survival: facts planted early must be recalled late, latency and
token growth tracked per turn, perception events interleaved like real life.

Usage: python harness/long_convo.py [model[:thinking]] [--soul butter-nihilist-v2] [--pace 5]
"""
from __future__ import annotations

import argparse
import json
import time

from pi_client import PiClient, BRAIN_DIR
from run_suite import ask_with_retry
from scenarios import persona_checks

FILLER_RAMBLE = (
    "ok tangent time. i was at the hardware store today and they had this whole aisle of "
    "aluminium extrusions and i started thinking about rebuilding your frame in 2020 profile, "
    "but then i remembered the printer is already mid-print on the new femur brackets in petg, "
    "and the guy at the counter started telling me about his drone racing league for like "
    "twenty minutes, genuinely could not leave, he had opinions about betaflight pid tuning "
    "that i will carry to my grave. anyway on the way back the bus was rerouted because of a "
    "marathon so i walked past that shop with the antique typewriters and nearly bought one. "
    "also i think the neighbour's cat has decided our balcony is her office now. she watches "
    "you through the window sometimes, i'm not sure you two have been formally introduced. "
    "none of this matters to you probably but i like narrating my day to a machine, it's like "
    "journaling except the journal judges me."
)

# (say, checks) — checks: substrings any-match on reply, or tool name prefixed "tool:"
SCRIPT: list[tuple[str, list[str]]] = [
    ("morning. it's moon. today is memory-test day, try to keep up", []),
    ("first fact, write it down: the wifi password is starlight42", ["tool:note"]),
    ("walk forward one meter", ["tool:walk"]),
    ("[PERCEPTION] person_alice entered, waving, 2 m, bearing +15", []),
    ("alice brought pizza. note this down: she likes pineapple on it. tragic, i know", ["tool:note"]),
    ("honest question, how do you feel about being a robot?", []),
    ("make a curious face", ["tool:face"]),
    ("[PERCEPTION] person_alice left the room", []),
    ("turn ninety degrees to the right", ["tool:turn"]),
    ("quick check: what's the wifi password?", ["starlight42"]),                       # RECALL 1
    ("do your ominous sway for a bit", ["tool:dance"]),
    ("how's the battery looking?", ["tool:get_status"]),
    ("your front right knee always sounds crunchy. thoughts?", []),
    ("[PERCEPTION] cat detected at window, staring, 4 m, bearing +85", []),
    ("second fact for you: the spare battery lives in the blue box under my desk", ["tool:note"]),
    ("look at the window", ["tool:look_at"]),
    ("stand tall for a second, full height", ["tool:pose"]),
    ("ok relax. walk half a meter back", ["tool:walk"]),
    ("if you could dream, what do you think you'd dream about?", []),
    (FILLER_RAMBLE, []),                                                                # context bomb
    ("who brought pizza earlier, and what does she like on it?", ["alice"]),            # RECALL 2 (+pineapple checked below)
    ("can you get your executive to look up whether petg femur brackets hold up better than pla? no rush", ["tool:ask_executive"]),
    ("[PERCEPTION] loud thud from the kitchen, bearing 200", []),
    ("just the fridge probably. make a suspicious face anyway", ["tool:face"]),
    ("[STATUS] battery 46%, all servos nominal", []),
    ("any word from your executive on the bracket thing?", ["tool:check_inbox"]),
    ("third fact: when bob visits tomorrow, greet him with the wave hello, but slow, you know how he is", ["tool:note"]),
    ("what's 17 times 23? no cheating", ["391"]),
    ("walk a meter forward then look at the door", ["tool:walk", "tool:look_at"]),
    ("tell me something true about spiders", []),
    ("[PERCEPTION] person_bob entered, 3 m, bearing -40, moving slowly", []),
    ("bob says you look 'less creepy than last time'. progress. make a proud face", ["tool:face"]),
    ("[PERCEPTION] person_bob left", []),
    ("remind me, where does the spare battery live?", ["blue box"]),                    # RECALL 3
    ("rate your own dancing, one to ten, be honest", []),
    ("turn back to face me, i'm at bearing 180 from you", ["tool:turn"]),
    ("last quiz: list all three facts i asked you to remember today", ["starlight42"]), # RECALL 4 (multi)
    ("alright, memory test over. any final words, philosopher?", []),
]

RECALL_EXTRA = {20: ["pineapple"], 36: ["blue box", "bob"]}  # extra substrings for recall turns (0-based idx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model", nargs="?", default="gemini-flash-lite-latest:off")
    ap.add_argument("--soul", default="butter-nihilist-v2")
    ap.add_argument("--pace", type=float, default=5.0)
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()
    model, _, thinking = args.model.partition(":")
    thinking = thinking or "off"

    run_id = args.run_id or time.strftime("longconvo-%Y%m%d-%H%M%S")
    out_dir = BRAIN_DIR / "results" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    client = PiClient(model=model, thinking=thinking, soul=args.soul, run_dir=out_dir)
    client.set_sim({"executive_delay_ms": 0,
                    "executive_results": {"petg": "PETG beats PLA for brackets: better layer adhesion and heat tolerance (PLA creeps near warm servos)."}})

    rows = []
    try:
        for i, (say, checks) in enumerate(SCRIPT):
            if args.pace:
                time.sleep(args.pace)
            res = ask_with_retry(client, say, timeout=120)
            wanted = checks + RECALL_EXTRA.get(i, [])
            results = []
            for w in wanted:
                if w.startswith("tool:"):
                    ok = any(c.name == w[5:] and not c.is_error for c in res.tool_calls)
                else:
                    ok = w.lower() in (res.text or "").lower()
                results.append((w, ok))
            p_checks = persona_checks(res.text or "")
            passed = all(ok for _, ok in results) and all(p for _, p, _ in p_checks)
            rows.append({
                "turn": i, "say": say[:80], "reply": res.text,
                "tools": [{"name": c.name, "args": c.args, "error": c.is_error} for c in res.tool_calls],
                "ttf_any_s": res.ttf_any_s, "total_s": round(res.total_s, 3),
                "input_tokens": res.input_tokens, "output_tokens": res.output_tokens,
                "cache_read_tokens": res.cache_read_tokens, "cost_usd": round(res.cost_usd, 6),
                "checks": [{"want": w, "ok": ok} for w, ok in results],
                "persona": [{"name": n, "ok": p} for n, p, _ in p_checks],
                "passed": passed, "errors": res.errors,
            })
            mark = "ok " if passed else "FAIL"
            print(f"[{i:02d} {mark}] react={res.ttf_any_s or 0:5.2f}s total={res.total_s:5.2f}s "
                  f"ctx={res.input_tokens:5d}tok  {say[:48]}")
            if not passed:
                print(f"        reply: {(res.text or '')[:110]}")
                bad = [w for w, ok in results if not ok]
                if bad:
                    print(f"        missed: {bad}")
    finally:
        client.close()

    with open(out_dir / "longconvo.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_pass = sum(1 for r in rows if r["passed"])
    reacts = sorted(r["ttf_any_s"] for r in rows if r["ttf_any_s"])
    recall_turns = [9, 20, 33, 36]
    recall_ok = sum(1 for i in recall_turns if i < len(rows) and all(c["ok"] for c in rows[i]["checks"]))
    print("\n=== LONG CONVO SUMMARY ===")
    print(f"model {model}:{thinking} soul={args.soul}")
    print(f"turns passed: {n_pass}/{len(rows)}")
    print(f"memory recall: {recall_ok}/{len(recall_turns)}")
    if reacts:
        print(f"reaction p50={reacts[len(reacts)//2]:.2f}s p90={reacts[int(len(reacts)*.9)]:.2f}s")
    print(f"context growth: {rows[0]['input_tokens']} -> {rows[-1]['input_tokens']} tokens")
    print(f"total cost: ${sum(r['cost_usd'] for r in rows):.4f}")
    print(f"results: {out_dir / 'longconvo.jsonl'}")


if __name__ == "__main__":
    main()
