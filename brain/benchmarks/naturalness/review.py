"""Build a blinded, offline comparison page from two compatible benchmark runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import shutil


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _samples(run: dict, label: str = "Run") -> dict:
    result = {}
    for sample in run.get("samples", []):
        key = (sample["case_id"], sample["repeat"])
        if key in result:
            raise ValueError(f"Duplicate sample key: {key}")
        if sample.get("status") != "completed":
            raise ValueError(f"Sample {key!r} is not completed: {sample.get('status')!r}")
        if "expected_turns" in sample or "completed_turns" in sample:
            expected, completed = sample.get("expected_turns"), sample.get("completed_turns")
            if type(expected) is not int or type(completed) is not int or expected < 0 or completed != expected:
                raise ValueError(f"Sample {key!r} has incomplete or invalid turn counts")
        audio_only = sample.get("audio_only") is True and sample.get("audio_scope") == "conversation" and bool(sample.get("audio_path"))
        if not isinstance(sample.get("turns", []), list) or (not sample.get("turns") and not audio_only):
            raise ValueError(f"Sample {key!r} has no completed conversation turns")
        if "completed_turns" in sample and not audio_only and len(sample["turns"]) != sample["completed_turns"]:
            raise ValueError(f"Sample {key!r} turn counts do not match its recorded turns")
        result[key] = sample
    manifest = run.get("manifest", {})
    if "selected_case_ids" in manifest or "repeats" in manifest:
        ids, repeats = manifest.get("selected_case_ids"), manifest.get("repeats")
        if (not isinstance(ids, list) or not ids
                or any(not isinstance(cid, str) or not cid for cid in ids)
                or len(set(ids)) != len(ids) or type(repeats) is not int or repeats < 1):
            raise ValueError(f"{label} has an invalid planned sample manifest")
        planned = {(cid, repeat) for cid in ids for repeat in range(1, repeats + 1)}
        missing, extra = planned - result.keys(), result.keys() - planned
        if missing or extra:
            raise ValueError(
                f"{label} planned coverage is incomplete: expected={len(planned)}, "
                f"recorded={len(result)}, missing={len(missing)}, unexpected={len(extra)}; "
                f"missing_pairs={sorted(missing)!r}; unexpected_pairs={sorted(extra)!r}"
            )
    if not result:
        raise ValueError("Run contains no samples")
    return result


def build_review(baseline: dict, candidate: dict, out: Path, seed: int = 20260923) -> dict:
    """Write review.html, optional local audio, and a separate private answer key.

    The HTML contains only blind responses. Keep answer_key.json with the experiment
    owner; share review.html and its media folder with reviewers. audio_path is an
    explicit local file path relative to the caller's working directory or absolute.
    """
    for field in ("suite_sha256", "adapter"):
        left = baseline.get("manifest", {}).get(field)
        right = candidate.get("manifest", {}).get(field)
        if not left or left != right:
            raise ValueError(f"Cannot compare runs with missing or different {field}")
    samples = [_samples(baseline, "Baseline"), _samples(candidate, "Candidate")]
    if samples[0].keys() != samples[1].keys():
        left_only = sorted(samples[0].keys() - samples[1].keys(), key=str)
        right_only = sorted(samples[1].keys() - samples[0].keys(), key=str)
        raise ValueError("Runs must contain exactly the same (case_id, repeat) pairs; "
                         f"baseline-only={left_only!r}; candidate-only={right_only!r}")
    out = Path(out)
    if any((out / name).exists() for name in ("review.html", "answer_key.json")):
        raise ValueError("Review output already exists; choose a new directory to preserve review evidence")
    rng = random.Random(seed)
    public = {"schema_version": 1, "pairs": []}
    private = {"schema_version": 1, "seed": seed,
               "runs": {"baseline": baseline["manifest"], "candidate": candidate["manifest"]},
               "pairs": []}
    media = []
    keys = sorted(samples[0], key=lambda item: (str(item[0]), str(item[1])))
    rng.shuffle(keys)
    for index, key in enumerate(keys):
        pair_id = f"pair-{index + 1:04d}"
        order = [0, 1]
        rng.shuffle(order)
        options = {}
        mapping = {}
        for label, source in zip(("A", "B"), order):
            sample = samples[source][key]
            option = {"turns": [
                {"user": str(turn.get("user", "")), "text": str(turn.get("text", "")),
                 "tools": turn.get("tools", [])} for turn in sample.get("turns", [])],
                "view_mode": "text-only"}
            if sample.get("audio_path"):
                audio = Path(sample["audio_path"])
                if audio.suffix.lower() not in (".wav", ".mp3", ".ogg", ".m4a", ".webm", ".flac") or not audio.is_file():
                    raise ValueError("audio_path must reference an existing local audio file")
                name = f"media/{pair_id}-{label}{audio.suffix.lower()}"
                audio_hash = hashlib.sha256(audio.read_bytes()).hexdigest()
                option.update(audio=name, audio_sha256=audio_hash, view_mode="text-and-audio",
                              conversation_audio=sample.get("audio_scope") == "conversation")
                media.append((audio, out / name))
            options[label] = option
            mapping[label] = "baseline" if source == 0 else "candidate"
        view_mode = "text-only" if all(x["view_mode"] == "text-only" for x in options.values()) else "audio-available"
        public["pairs"].append({"pair_id": pair_id, "view_mode": view_mode, "options": options})
        private["pairs"].append({"pair_id": pair_id, "case_id": key[0], "repeat": key[1], "mapping": mapping,
                                 "evidence_modes": {label: {
                                     "view_mode": value["view_mode"],
                                     "conversation_audio": value.get("conversation_audio", False)}
                                     for label, value in options.items()}})
    pack_hash = hashlib.sha256(_json(public).encode()).hexdigest()
    public["pack_sha256"] = pack_hash
    private["pack_sha256"] = pack_hash
    # Escape HTML delimiters even in script data; render all supplied text with textContent.
    data = _json(public).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    out.mkdir(parents=True, exist_ok=True)
    if any(target.exists() for _, target in media):
        raise ValueError("Review media already exists; choose a new output directory")
    for source, target in media:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
    with (out / "review.html").open("x", encoding="utf-8") as target:
        target.write(_PAGE.replace("__PACK_DATA__", data))
    with (out / "answer_key.json").open("x", encoding="utf-8") as target:
        target.write(json.dumps(private, indent=2, ensure_ascii=True) + "\n")
    return {"review_path": str(out / "review.html"), "answer_key_path": str(out / "answer_key.json"),
            "pack_sha256": pack_hash, "pairs": len(keys), "audio_files": len(media),
            "pairing": {"baseline_samples": len(samples[0]), "candidate_samples": len(samples[1]),
                        "matched_pairs": len(keys), "unpaired": []}}


_PAGE = r'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MIST review</title>
<style>
:root{font:16px/1.5 system-ui,sans-serif;color:#20312f;background:#f5f4ef}*{box-sizing:border-box}
body{max-width:1160px;margin:auto;padding:24px}header,nav,.controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
header{justify-content:space-between;border-bottom:1px solid #cbd4cf;padding-bottom:16px}h1{font-size:20px;margin:0}h2{font-size:19px}
button,select,textarea{font:inherit;border:1px solid #bbc7c1;border-radius:7px;background:#fff;color:inherit;padding:7px 11px}
button{cursor:pointer}button:disabled{opacity:.4;cursor:default}button:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #19826d}
nav{margin:20px 0;justify-content:space-between}.columns{display:grid;grid-template-columns:1fr 1fr;gap:18px}
article{background:#fff;border:1px solid #d6ded7;border-radius:12px;padding:20px}.muted{color:#596b64;font-size:14px}
.turn{border-bottom:1px solid #e6eae5;padding:12px 0}.turn p{margin:4px 0;white-space:pre-wrap;overflow-wrap:anywhere}
.role{font-size:12px;font-weight:650;color:#60716a}.reply{margin-top:10px!important}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.5 monospace}
.rating{display:grid;grid-template-columns:minmax(0,1fr) 145px;gap:12px;align-items:center;margin:13px 0}.rating small{display:block;color:#65736c;font-size:12px}
.ratings{border-top:1px solid #d6ded7;margin-top:20px;padding-top:8px}audio{width:100%}.verdict{margin:22px 0;background:#e9ede6;border-radius:12px;padding:18px}
textarea{width:100%;min-height:76px;margin-top:8px}label{font-size:14px}.scale{font-size:13px}#saved{font-size:13px;color:#596b64}
@media(max-width:700px){body{padding:14px}.columns{grid-template-columns:1fr}.rating{grid-template-columns:1fr 132px}}
</style>
<header><h1>MIST review</h1><div class="controls"><span id="saved"></span><button id="download">Download ratings</button></div></header>
<p class="muted">Read both conversations before choosing. Judge what is present; leave anything you cannot assess unrated. Your ratings stay in this browser until you download them.</p>
<nav><button id="prev">Previous</button><span id="position"></span><button id="next">Next</button></nav>
<p id="mode" class="muted"></p><div id="cards" class="columns"></div>
<section class="verdict"><label for="preference">Which would you rather talk to?</label> <select id="preference"><option value="">Choose</option><option>A</option><option>B</option><option value="tie">Tie</option><option value="unclear">Unclear</option></select>
<p class="muted">Consider the whole exchange, including whether it understood the situation and helped without becoming tiring.</p>
<label for="note">What made the difference? Add a turn number or audio timestamp.</label><textarea id="note" placeholder="Turn 2: ..."></textarea></section>
<p class="scale">1 = poor, 2 = weak, 3 = acceptable, 4 = good, 5 = excellent. Use "Cannot assess" when the evidence is missing.</p>
<script id="pack" type="application/json">__PACK_DATA__</script>
<script>
'use strict';
const pack=JSON.parse(document.getElementById('pack').textContent), storageKey='mist-review-'+pack.pack_sha256;
const $=id=>document.getElementById(id);let index=0,answers={};
try{answers=JSON.parse(localStorage.getItem(storageKey)||'{}');if(!answers||typeof answers!=='object'||Array.isArray(answers))answers={}}catch(_){answers={}}
const dimensions=[
 ['understanding','Understanding','Did it follow the meaning, context and corrections?'],
 ['emotional_fit','Emotional fit','Did its tone fit without guessing feelings or overreacting?'],
 ['usefulness','Usefulness','Was the answer or action accurate and helpful?'],
 ['conversational_flow','Conversation flow','Did the exchange progress without repetition or awkward detours?'],
 ['personality','Personality','Did it feel consistent and pleasant rather than forced?'],
 ['voice_quality','Voice quality','Was the provided audio clear, natural and free of artifacts?'],
 ['speech_timing','Speech timing','Only rate a recording that includes both people and real pauses.'],
 ['expressions','Expressions','Not assessable in this text/audio review.']];
function state(){const p=pack.pairs[index];return answers[p.pair_id]||(answers[p.pair_id]={pair_id:p.pair_id,view_mode:p.view_mode,options:{A:{view_mode:p.options.A.view_mode,ratings:{}},B:{view_mode:p.options.B.view_mode,ratings:{}}},preference:'',note:''})}
function save(){try{localStorage.setItem(storageKey,JSON.stringify(answers));$('saved').textContent='Saved in this browser'}catch(_){$('saved').textContent='Storage unavailable; download to save'}}
function el(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e}
function draw(){const pair=pack.pairs[index],s=state();$('position').textContent=`${index+1} / ${pack.pairs.length}`;$('prev').disabled=index===0;$('next').disabled=index===pack.pairs.length-1;
 $('mode').textContent=pair.view_mode==='text-only'?'Text only. Voice quality, speech timing and expressions cannot be rated here.':'Audio is available where shown. Do not infer live latency or interruptions from response-only audio. Expressions cannot be rated here.';
 $('cards').replaceChildren();for(const label of ['A','B']){const option=pair.options[label],card=el('article');card.append(el('h2',label));
 if(option.audio){const a=el('audio');a.controls=true;a.preload='none';a.src=option.audio;card.append(a)}else card.append(el('p','Text only','muted'));
 option.turns.forEach((turn,i)=>{const section=el('div',undefined,'turn');section.append(el('p',`Turn ${i+1} · You`,'role'),el('p',turn.user),el('p','MIST','role reply'),el('p',turn.text));if(turn.tools&&turn.tools.length){const details=el('details');details.append(el('summary','Tool calls'),el('pre',JSON.stringify(turn.tools,null,2)));section.append(details)}card.append(section)});
 const ratings=el('div',undefined,'ratings');for(const [id,title,hint] of dimensions){const row=el('label',undefined,'rating'),titleEl=el('span',title);titleEl.append(el('small',hint));const select=el('select');select.setAttribute('aria-label',label+' '+title);for(const [v,t] of [['','Unrated'],['1','1 · Poor'],['2','2 · Weak'],['3','3 · Acceptable'],['4','4 · Good'],['5','5 · Excellent'],['unassessable','Cannot assess']]){const o=el('option',t);o.value=v;select.append(o)}
 const unavailable=id==='expressions'||(id==='speech_timing'&&!option.conversation_audio)||(id==='voice_quality'&&!option.audio);if(unavailable){s.options[label].ratings[id]='unassessable';select.disabled=true}select.value=s.options[label].ratings[id]||'';select.onchange=()=>{s.options[label].ratings[id]=select.value;save()};row.append(titleEl,select);ratings.append(row)}card.append(ratings);$('cards').append(card)}
 $('preference').value=s.preference;$('note').value=s.note;save();}
$('prev').onclick=()=>{index--;draw()};$('next').onclick=()=>{index++;draw()};$('preference').onchange=()=>{state().preference=$('preference').value;save()};$('note').oninput=()=>{state().note=$('note').value;save()};
$('download').onclick=()=>{const result={schema_version:1,pack_sha256:pack.pack_sha256,reviewed_at:new Date().toISOString(),reviews:Object.values(answers)};const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=el('a');a.href=url;a.download='mist-ratings-'+pack.pack_sha256.slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
draw();
</script></html>
'''
