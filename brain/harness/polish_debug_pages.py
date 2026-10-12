from pathlib import Path
root=Path(__file__).resolve().parents[1]/'duplex/static'
p=root/'debug.js';s=p.read_text(encoding='utf-8')
old="return(!query||s.includes(query))&&(!category||s.includes(category));"
new="const k=kind(r);const match={tool:k.includes('tool'),tts:k.startsWith('tts')||k==='latency'||k.startsWith('conversion'),playback:k.includes('playback')||k.startsWith('audio'),expression:k==='expression'||k==='face',brain:k==='brain_job'||k.includes('background'),transcript:k.startsWith('transcript'),native:k.startsWith('native')||k==='debug_model'||k==='ready'};return(!query||s.includes(query))&&(!category||match[category]);"
assert old in s;s=s.replace(old,new)
s=s.replace("[e.phase,e.name,e.state", "[e.phase,e.name,e.detail?.toolName,e.detail?.type,e.state")
p.write_text(s,encoding='utf-8')
for name in ('debug.html','expressions.html'):
    p=root/name;s=p.read_text(encoding='utf-8').replace('/duplex/inspect.css','/duplex/inspect.css?v=debug2').replace('/duplex/debug.js','/duplex/debug.js?v=debug2').replace('/duplex/expressions.js','/duplex/expressions.js?v=debug2');p.write_text(s,encoding='utf-8')
p=root/'index.html';s=p.read_text(encoding='utf-8').replace('v=20260914-debug1','v=20260914-debug2');p.write_text(s,encoding='utf-8')
