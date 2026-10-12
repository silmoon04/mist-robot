"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const node = (tag, text, className) => { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; };
  const fmt = value => typeof value === "number" ? `${value.toFixed(2)} s` : "Not measured";
  const labels = {first_text_s:"First Luna text",first_tool_s:"First tool call",first_speakable_phrase_s:"First complete speech phrase",total_s:"Luna turn completion",fixture_end_to_first_delta_s:"Microphone end to native text",fixture_end_to_first_tool_s:"Microphone end to tool",fixture_end_to_face_s:"Microphone end to face event",result_from_start_s:"Background result",start_handle_s:"Background dispatch"};
  let data, selected = [], page = 0;
  const pageSize = 12;
  const runMap = new Map();
  function addOptions(id, values) { const first = $(id).firstElementChild; $(id).replaceChildren(first); [...new Set(values)].sort().forEach(value => { const option = node("option", value); option.value = value; $(id).append(option); }); }
  function technical(title, value) { const el = node("details", undefined, "technical"); el.append(node("summary", title)); el.addEventListener("toggle", () => { if (el.open && el.children.length === 1) el.append(node("pre", JSON.stringify(value, null, 2))); }); return el; }
  function outcome(turn) { return turn.status === "pass" ? "Contract pass" : turn.status === "fail" ? "Contract failure" : "Not graded"; }
  function turnElement(turn, s) {
    const el = node("article", undefined, "turn");
    const heading = node("div", undefined, "turn-heading"); heading.append(node("span", turn.id), node("span", outcome(turn), turn.status));
    if (turn.state_protected === true) heading.append(node("span", "State guard passed", "guard"));
    if (turn.display_protected === true) heading.append(node("span", "Display guard passed", "guard"));
    el.append(heading);
    const dialogue = node("div", undefined, "dialogue");
    const line = (who, text) => { dialogue.append(node("span", who, "speaker"), node("p", text || "No text recorded", `speech${text ? "" : " empty"}`)); };
    if (s.kind === "native") {
      line("Input", turn.input);
      if (turn.transcripts.length) turn.transcripts.forEach(t => line(t.role === "user" ? "Heard" : "Front", t.text));
      else line("Front", "");
    } else { line("You", turn.input); line("Luna", turn.text); }
    el.append(dialogue);
    const timingKeys = s.kind === "native" ? ["fixture_end_to_first_delta_s","fixture_end_to_first_tool_s","fixture_end_to_face_s"] : ["first_text_s","first_speakable_phrase_s","first_tool_s","total_s","result_from_start_s"];
    const times = timingKeys.filter(k => typeof turn.timings[k] === "number").map(k => `${labels[k] || k}: ${fmt(turn.timings[k])}`);
    if (times.length) el.append(node("p", times.join(" · "), "turn-time"));
    if (turn.failures.length || turn.errors.length) { const list = node("ul", undefined, "failure-list"); [...turn.failures, ...turn.errors].forEach(f => list.append(node("li", typeof f === "string" ? f : JSON.stringify(f)))); el.append(list); }
    if (turn.tools.length || turn.receipts.length) el.append(technical(`Tools and receipts (${turn.tools.length || turn.receipts.length})`, {calls:turn.tools,receipts:turn.receipts}));
    el.append(technical("Checks and timing detail", {...turn.detail, measured_timings:turn.timings}));
    return el;
  }
  function sessionElement(s) {
    const el = node("details", undefined, "session");
    const summary = node("summary");
    const title = node("div", s.style, "session-title"); title.append(node("div", `${s.suite} / ${s.run} / ${s.group}`, "meta")); summary.append(title);
    const counts = node("div", undefined, "counts"); counts.append(node("span", `${s.turns.length} records`));
    ["pass","fail","ungraded"].forEach(k => { const n = s.turns.filter(t=>t.status===k).length; if (n) counts.append(node("span", `${n} ${k === "ungraded" ? "not graded" : k}`, k)); });
    const guarded = s.turns.filter(t=>t.state_protected === true || t.display_protected === true).length;
    if (guarded) counts.append(node("span", `${guarded} guard checks passed`, "guard"));
    summary.append(counts); el.append(summary);
    el.addEventListener("toggle", () => {
      if (!el.open || el.children.length > 1) return;
      const body = node("div", undefined, "session-body"), run = runMap.get(s.run_id);
      body.append(node("p", s.kind === "native" ? "Native realtime front voice; Luna delegated tools. Synthetic microphone, TTS recorder, no speaker audio." : "Direct Luna text and tools. No synthesized speech.", "scope"));
      if (s.correlation_invalid) body.append(node("p", "Historical case correlation is invalid. Read the corrected trace review before relying on these case verdicts.", "scope warning"));
      if (run.limits.length) body.append(technical("Run limits", run.limits));
      s.turns.forEach(turn => body.append(turnElement(turn,s)));
      body.append(technical("Run and source", {source:s.source,...run.metadata})); el.append(body);
    });
    return el;
  }
  function draw() {
    const root = $("sessions"); root.replaceChildren(); selected.slice(page*pageSize,(page+1)*pageSize).forEach(s=>root.append(sessionElement(s)));
    $("match-count").textContent = `${selected.length} conversations or case groups · ${selected.reduce((n,s)=>n+s.turns.length,0)} records shown in their full context`;
    $("page").textContent = selected.length ? `${page+1} / ${Math.ceil(selected.length/pageSize)}` : "No matches";
    $("previous").disabled = page === 0; $("next").disabled = (page+1)*pageSize >= selected.length;
  }
  function filter() {
    const query = $("search").value.trim().toLocaleLowerCase(), result = $("result").value;
    selected = data.sessions.filter(s => (!$("suite").value || s.suite === $("suite").value) && (!$("run").value || s.run === $("run").value) && (!$("style").value || s.style === $("style").value) && (!query || JSON.stringify(s).toLocaleLowerCase().includes(query)) && (!result || s.turns.some(t=>result === "guarded" ? t.state_protected === true || t.display_protected === true : t.status === result)));
    page = 0; draw();
  }
  function timings() {
    const metric = $("metric").value, root = $("timing-rows"); root.replaceChildren();
    data.runs.forEach(run => { const value = run.metrics[metric]; if (!value) return; const tr = node("tr"); [run.id,String(value.n),fmt(value.median_s),fmt(value.p90_s)].forEach(text=>tr.append(node("td",text))); root.append(tr); });
    $("metric-note").textContent = metric.startsWith("fixture_") ? "From the end of the paced microphone fixture to a native event. This excludes speaker playback, and is separate from direct Luna text timing." : "From turn submission to the recorded text or tool boundary. No speech-recognition, synthesis or speaker delay is included. Missing values are excluded, never treated as zero.";
  }
  fetch("luna-tests.json", {cache:"no-store"}).then(r=>{if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json();}).then(value=>{
    data = value; data.runs.forEach(r=>runMap.set(r.id,r));
    $("totals").textContent = `${data.counts.records} recorded turns and cases · ${data.counts.runs} runs`;
    $("built").textContent = `Snapshot ${new Date(data.generated_at).toLocaleString()}`;
    data.notes.forEach(text=>$("notes").append(node("p",text)));
    addOptions("suite",data.sessions.map(s=>s.suite)); addOptions("run",data.sessions.map(s=>s.run)); addOptions("style",data.sessions.map(s=>s.style));
    Object.entries(labels).filter(([key])=>data.runs.some(r=>r.metrics[key])).forEach(([key,text])=>{const option=node("option",text);option.value=key;$("metric").append(option);});
    data.reviews.forEach(review=>{const box=technical(review.source,review.report);if(review.text){box.replaceChildren(node("summary",review.source),node("pre",review.text,"review"));}$("review-list").append(box);});
    data.deterministic.forEach(item=>$("deterministic-list").append(technical(item.source,item.report)));
    data.sources.forEach(source=>$("source-list").append(node("p",`${source.path}\nSHA256 ${source.sha256}`)));
    data.gaps.forEach(gap=>$("source-list").append(node("p",gap,"warning")));
    $("filters").addEventListener("submit",event=>event.preventDefault());$("filters").addEventListener("input",filter);$("filters").addEventListener("reset",()=>setTimeout(filter,0));
    $("previous").addEventListener("click",()=>{page--;draw();});$("next").addEventListener("click",()=>{page++;draw();});$("metric").addEventListener("change",timings);
    document.querySelectorAll("nav button").forEach(button=>button.addEventListener("click",()=>{document.querySelectorAll(".panel").forEach(p=>p.hidden=p.id!==button.dataset.panel);document.querySelectorAll("nav button").forEach(b=>b.setAttribute("aria-pressed",String(b===button)));}));
    filter();timings();$("load-state").hidden=true;$("content").hidden=false;
  }).catch(error=>{$("load-state").textContent=`Could not load the recorded tests: ${error.message}`;});
})();
