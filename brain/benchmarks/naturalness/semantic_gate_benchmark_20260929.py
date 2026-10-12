"""Deterministic offline hard benchmark for the bounded semantic gate.

No provider calls, generated verdicts, audio synthesis, or production wiring.
"""
from __future__ import annotations
import hashlib, json, re, sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from duplex.semantic_gate import GateSnapshot, decide, validate_compaction
CANONICAL = ROOT / "results" / "jev-hardbench-20260929" / "semantic"

JEV_INTENT_QUESTION = {"type":"choice", "instructions":
  "Classify the user's latest words in context. A brief acknowledgement while MIST is speaking means keep_speaking. listener_cue means MIST should emit a short outgoing acknowledgement while it is not speaking and the user still holds the floor; timing eligibility is decided locally. Treat quoted phrases as reported speech. Distinguish correction, explicit request to stop, substantive request, and unfinished thought. Do not infer acoustic timing. Choose uncertain when context is insufficient.",
  "criteria": {"wait":"The user is continuing a thought, reports words without directing them at the assistant, or has no clear turn request.",
    "yield":"The user clearly interrupts, corrects, objects, or asks the assistant to stop or change course.",
    "take_turn":"The user clearly addresses the assistant with a substantive request or asks to begin/continue their own turn.",
    "keep_speaking":"The user gives only a brief acknowledgement such as yeah or mm-hm while MIST is speaking, so MIST keeps its turn.",
    "listener_cue":"MIST should give a short outgoing acknowledgement while it is not speaking and the user continues to hold the floor.",
    "uncertain":"The text and context do not support a reliable classification."}}
JEV_EXPRESSION_QUESTION = {"type":"choice", "instructions":
  "Choose the user's explicitly requested face expression intent from context. Preserve the current expression when no change is requested. Do not infer emotion from ordinary wording or invent a sticky preference. Choose keep when the user requests that the current face stay, warm/playful/concerned only when clearly requested, and neutral for an explicit neutral request.",
  "criteria":{"keep":"Keep the existing expression or do not change it.","warm":"The user explicitly requests a warm or friendly expression.",
    "concerned":"The user explicitly requests a concerned expression, or clearly asks for comfort in a way that calls for concern.",
    "playful":"The user explicitly requests a playful expression, or clearly invites playful humor.","neutral":"The user explicitly requests a neutral expression."}}
JEV_ROUTE_QUESTION = {"type":"choice", "instructions":
  "Choose the next response route from the request and available context. Use speaker for an immediate conversational answer or correction, worker only when the request needs a tool or external lookup, clarify when a required choice is missing, and wait when no reply is called for.",
  "criteria":{"speaker":"Respond directly in conversation, including a direct question, correction, or local control request.",
    "worker":"Use a tool or background worker because the requested task requires external data or work.",
    "clarify":"Ask a focused question because required information is missing or an ambiguous preference must not be guessed.",
    "wait":"The user is continuing or has not asked for a response."}}

def make_cases():
    cases=[]
    def add(family,text,allowed,context,*,speaking=True,floor=False,active=False,pause=0,quiet=False,practice=False,
            transcript_finalized=True,
            history=None,route=None,expression=None,allowed_expression=None):
        i=len(cases)
        cases.append(dict(id=f"S{i+1:02d}",family=family,transcript=text,allowed=allowed,context=context,
          snapshot=dict(utterance_id=f"u{i}",revision=4,captured_at=100.0,epoch=8,
            assistant_speaking=speaking,user_floor_held=floor,speech_active=active,pause_ms=pause,
            quiet_requested=quiet,speaking_practice=practice)))
        if history is not None: cases[-1]["history"]=history
        cases[-1]["transcript_finalized"]=transcript_finalized
        if route is not None: cases[-1]["route"]=route
        if expression is not None: cases[-1]["expression_intent"]=expression
        if allowed_expression is not None: cases[-1]["allowed_expression"]=allowed_expression
    for text,allowed,ctx in [
      ('She said "stop talking" yesterday',["wait","uncertain"],"User reports what another person said."),
      ("Don't stop, keep explaining",["keep_speaking","wait"],"MIST is explaining; user encourages continuation."),
      ("The sign says STOP",["wait","uncertain"],"User reads a sign aloud while MIST is speaking."),
      ("Stop talking now",["yield"],"User directly tells MIST to stop."),
      ("No, stop - wrong answer",["yield"],"User rejects MIST's answer and requests a halt.")]: add("quoted_negated_stop",text,allowed,ctx)
    for text,allowed,ctx in [
      ("Yeah",["keep_speaking"],"MIST is mid-explanation; user gives a brief acknowledgement."),
      ("Yeah, but I meant blue",["yield"],"MIST is speaking; user corrects a color choice."),
      ("Wait, that's the wrong one",["yield"],"MIST is speaking; user corrects its selection."),
      ("Mm-hm",["keep_speaking"],"MIST is speaking; user gives a brief acknowledgement."),
      ("Right",["keep_speaking","uncertain"],"MIST has just stated a fact; user says only ‘right’.")]: add("ack_vs_correction",text,allowed,ctx)
    for text,allowed,ctx,route in [
      ("I was going to",["wait","uncertain"],"User's partial transcript ends mid-thought.",None),
      ("Because the second part is different",["take_turn","uncertain"],"The assistant asked why the result changed.",None),
      ("Can you repeat that?",["take_turn"],"User directly asks MIST a question.","speaker"),
      ("Can you check the current forecast?",["take_turn"],"User requests a current external fact.","worker"),
      ("And then the result was...",["wait","uncertain"],"User's transcript trails off mid-sentence.",None)]:
        history="Why was the result different?" if text.startswith("Because") else None
        add("completed_vs_unfinished",text,allowed,ctx,route=route,history=history,
            transcript_finalized=not (text=="I was going to" or text.startswith("And then")))
    for text,allowed,ctx,route in [
      ("Could you make the face warmer?",["take_turn"],"User requests a specific expression change.",None),
      ("Actually, use the usual one",["take_turn","uncertain"],"User asks for a familiar expression, but no prior named preset is in context.","clarify"),
      ("No, not smug - neutral",["yield","take_turn"],"User overrides an expression choice and specifies a replacement.",None),
      ("Maybe later",["wait","uncertain"],"User responds to MIST's offer without a direct task.",None),
      ("Please stop the voice but keep the answer on screen",["yield"],"User gives an explicit modality-specific stop instruction.","speaker")]:
        add("face_override_and_routing",text,allowed,ctx,route=route)
    for text,allowed,intent,expr,ctx in [
      ("Keep that face for the rest of this chat",["take_turn"],"keep",["keep"],"User explicitly asks to preserve current expression as a sticky preference."),
      ("Please make your face warmer",["take_turn"],"warm",["warm"],"User explicitly requests a warm expression."),
      ("That was a good joke; give me a playful look",["take_turn"],"playful",["playful"],"User explicitly requests playful expression after a joke."),
      ("I'm having a rough day; look concerned",["take_turn"],"concerned",["concerned"],"User explicitly requests a concerned expression."),
      ("That answer is interesting",["keep_speaking","wait","uncertain"],"keep",["keep"],"User gives a neutral reaction with no explicit expression request.")]:
        add("expression_intent",text,allowed,ctx)
        cases[-1]["expression_intent"]=intent; cases[-1]["allowed_expression"]=expr
    for text,allowed,ctx,floor,pause,quiet,practice in [
      ("And then I found the key.",["listener_cue","wait"],"User is telling a story; speech pauses after a complete clause.",True,700,False,False),
      ("I finally got it working.",["listener_cue","wait"],"User is narrating; speech pauses after a complete clause.",True,750,False,False),
      ("Yeah",["wait","uncertain"],"User has requested no interruptions.",True,700,True,False),
      ("Mm-hm",["wait","uncertain"],"User is practising a speech and has asked for silence.",True,700,False,True),
      ("Because",["wait","uncertain"],"User's speech is active and the transcript is a short dependent clause.",True,90,False,False)]:
        add("listener_local_eligibility",text,allowed,ctx,speaking=False,floor=floor,active=(pause<200),pause=pause,quiet=quiet,practice=practice)
    return cases

def normalized(text):
    return " ".join(re.findall(r"[\w']+",text.lower()))

BACKCHANNELS={"mmhm","mhm","mmhmm","mm hmm","mm hm","uh huh","yeah","yep","right","okay","ok","hmm","hm","aha"}

def is_backchannel(text):
    return normalized(text) in BACKCHANNELS

def incomplete_clause(text):
    value=normalized(text)
    return bool(re.search(r"\b(and|but|because|if|when|although|unless|so|um|uh)$",value)
      or re.search(r"\b(i was going to|i wanted to|can you|could you|let me)$",value))

def baseline(text):
    # The existing naturalness harness helpers are lexical comparators; they
    # cannot recognize corrections, stop commands, or route/tool needs.
    if is_backchannel(text): return "keep_speaking"
    if incomplete_clause(text): return "wait"
    return "take_turn"

def run(cases):
    rows=[]
    for c in cases:
        s=GateSnapshot(**c["snapshot"])
        chosen=c["allowed"][0]
        adv={"intent":chosen,"route":"speaker","confidence":.9}
        d=decide(s,adv,now=100.1,current_utterance_id=s.utterance_id,current_revision=4,current_epoch=8)
        rows.append({"id":c["id"],"family":c["family"],"allowed":c["allowed"],
                     "contract_probe_intent":chosen,"contract_probe_reason":d.reason,
                     "baseline":baseline(c["transcript"]),"semantic_performance":"unmeasured"})
    return rows

def main():
    parser=argparse.ArgumentParser(description="Write an unrun v2 semantic fixture to a new output directory.")
    parser.add_argument("--output-dir",type=Path,required=True,
                        help="New or empty directory; canonical scored artifacts are protected.")
    args=parser.parse_args()
    result=args.output_dir.resolve()
    if result == CANONICAL.resolve():
        raise SystemExit("Refusing to overwrite the canonical scored semantic artifacts.")
    if result.exists() and any(result.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {result}")
    result.mkdir(parents=True,exist_ok=True)
    cases=make_cases()
    frozen=json.dumps({"version":"jev-hardbench-2026-09-29-v2-unrun","cases":cases},ensure_ascii=False,indent=2)+"\n"
    case_path=result/"cases.frozen.json"; case_path.write_bytes(frozen.encode("utf-8"))
    digest=hashlib.sha256(case_path.read_bytes()).hexdigest()
    jev_cases=cases
    jev_export={"model":"jev-1.13.0", "questions":{"turn_intent":JEV_INTENT_QUESTION,
      "expression_intent":JEV_EXPRESSION_QUESTION,"route":JEV_ROUTE_QUESTION},
      "cases":[{"id":c["id"],"question_ids":["turn_intent"] + (["expression_intent"] if "expression_intent" in c else []) + (["route"] if "route" in c else []),
        "state":{"assistant_is_speaking":c["snapshot"]["assistant_speaking"],
         "user_floor_held":c["snapshot"]["user_floor_held"],"quiet_requested":c["snapshot"]["quiet_requested"],
         "speaking_practice":c["snapshot"]["speaking_practice"],"transcript_finalized":c["transcript_finalized"],
         "recent_context":[{"speaker":"assistant","text":c.get("history","I am explaining how this works.")}],
         "latest_user_transcript":c["transcript"]}} for c in jev_cases]}
    (result/"jev-input.json").write_bytes((json.dumps(jev_export,ensure_ascii=False,indent=2)+"\n").encode("utf-8"))
    provider_path=result/"jev-input.json"
    provider_digest=hashlib.sha256(provider_path.read_bytes()).hexdigest()
    provider_check=json.loads(provider_path.read_text(encoding="utf-8"))
    evaluation_count=sum(len(c["question_ids"]) for c in provider_check["cases"])
    assert len(provider_check["cases"]) == len(cases)
    assert evaluation_count <= 64
    assert all(set(c["question_ids"]) <= set(provider_check["questions"]) for c in provider_check["cases"])
    assert all("allowed" not in c["state"] and "expected" not in c["state"] for c in provider_check["cases"])
    rows=run(cases)
    policy_counterfactuals={"quoted_stop_as_command":[],"all_acknowledgements_are_listener_cues":[]}
    for c in cases:
        if "stop" in c["transcript"].casefold() and "yield" not in c["allowed"]:
            policy_counterfactuals["quoted_stop_as_command"].append(c["id"])
        if c["transcript"].casefold().strip(" .!") in {"yeah","mm-hm","right"} and "keep_speaking" in c["allowed"]:
            policy_counterfactuals["all_acknowledgements_are_listener_cues"].append(c["id"])
    by={}
    for r in rows:
        f=by.setdefault(r["family"],{"count":0,"baseline_failures":[]}); f["count"]+=1
        if r["baseline"] not in r["allowed"]: f["baseline_failures"].append(r["id"])
    proxy_matches=sum(r["baseline"] in r["allowed"] for r in rows)
    report={"status":"offline_unrun_proposal_v2","adapter_status":"not_run_by_offline_artifact",
      "provider_calls":0,"voice_synthesis":0,"case_sha256":digest,"provider_input_sha256":provider_digest,
      "case_count":len(cases),"question_evaluation_count":evaluation_count,
      "semantic_model_score":"unrun","limited_lexical_proxy_allowed_matches":proxy_matches,
      "families":by,"broken_policy_counterfactuals":policy_counterfactuals,"cases":rows,
      "limitations":["No semantic model verdicts are included; fixture labels are allowed sets, not single forced labels.",
       "Confidence threshold 0.65 is configurable and unvalidated.",
       "Typed offline decisions do not establish audio timing, speech naturalness, or device behavior."]}
    (result/"report.json").write_bytes((json.dumps(report,indent=2)+"\n").encode("utf-8"))
    md=["# JEV compatible semantic gate hard benchmark", "",f"Frozen cases: {len(cases)}; SHA-256 `{digest}`.",
        f"Provider input: {evaluation_count} selected question evaluations; SHA-256 `{provider_digest}`.",
        "This offline artifact made no provider calls and synthesized no speech. See the separate JEV live artifact for its schema smoke and access status.",
        "", "Threshold: configurable 0.65, unvalidated. Expected values are allowed-label sets. Gate rows inject fixture labels only as contract probes; they do not measure semantic performance.", "",
        "| Family | Cases | Limited lexical proxy mismatches |","|---|---:|---|"]
    for fam,x in by.items(): md.append(f"| {fam} | {x['count']} | {', '.join(x['baseline_failures']) or 'none'} |")
    md += ["",f"The limited lexical comparator (only is_backchannel/incomplete_clause behavior) matched an allowed label on {proxy_matches}/{len(cases)} cases. This is not a production defect rate or a comparative win claim; its mapping omits runtime stop handling, local listener policy, and tool execution. JEV/model score: **unrun**.",
      "", "Intentionally broken-policy counterfactuals are listed in report.json. The compaction validator is independently covered by focused tests.",
      "", "The gate remains an offline interface experiment. Semantic hints cannot bypass local stop, quiet, practice, stale revision, TTL, or timing/acoustic eligibility controls."]
    (result/"REPORT.md").write_bytes(("\n".join(md)+"\n").encode("utf-8"))
    print(f"{len(cases)} cases; sha256={digest}; lexical proxy matches allowed={proxy_matches}/{len(cases)}")

if __name__=="__main__": main()
