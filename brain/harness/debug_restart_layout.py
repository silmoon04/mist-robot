from pathlib import Path
root=Path(__file__).resolve().parents[1]/'duplex/static'
p=root/'inspect.css';s=p.read_text(encoding='utf-8').replace('max-height:65vh;border:1px solid #344247','max-width:1000px;border:1px solid #344247').replace('width:auto!important;height:auto!important','');p.write_text(s,encoding='utf-8')
p=root/'debug.js';s=p.read_text(encoding='utf-8').replace('let rows=[],cursor=0,paused=false;',"let rows=[],cursor=0,paused=false,traceId='';")
s=s.replace('/debug/events?after=${cursor}', '/debug/events?after=${cursor}&trace=${traceId}')
s=s.replace("const data=await response.json();", "const data=await response.json();const reset=traceId&&traceId!==data.trace_id;if(reset){rows=[];metrics.clear();turnStarts.clear();lastUserDone=null;}traceId=data.trace_id;")
s=s.replace('if(data.events.length)render();','if(data.events.length||reset)render();')
s=s.replace('`${Math.round(e.first_byte_s*1000)} ms`',"Number.isFinite(e.first_byte_s)?`${Math.round(e.first_byte_s*1000)} ms`:'No audio'")
p.write_text(s,encoding='utf-8')
for name in ('debug.html','expressions.html'):
    p=root/name;s=p.read_text(encoding='utf-8').replace('v=debug2','v=debug3');p.write_text(s,encoding='utf-8')
