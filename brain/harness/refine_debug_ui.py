from pathlib import Path
root=Path(__file__).resolve().parents[1]/'duplex/static'
p=root/'debug.js';s=p.read_text(encoding='utf-8');s=s.replace("function render(){const list=selected();", "function render(){const opened=new Set([...$('events').querySelectorAll('details[open]')].map(e=>e.dataset.eventId));const list=selected();")
s=s.replace("const e=row.event;summary.textContent", "disclosure.dataset.eventId=String(row.id);disclosure.open=opened.has(String(row.id));const e=row.event;summary.textContent")
s=s.replace("cursor=data.cursor;render();", "cursor=data.cursor;if(data.events.length)render();")
p.write_text(s,encoding='utf-8')
p=root/'inspect.css';s=p.read_text(encoding='utf-8');s+='\n@media(max-width:780px){.layout>section:last-child{grid-row:1}.controls{grid-row:2}}\n';p.write_text(s,encoding='utf-8')
p=root/'expressions.js';s=p.read_text(encoding='utf-8');s=s.replace("$('previous').onclick=()=>seek(time-1000/60);$('next').onclick=()=>seek(time+1000/60);", "$('previous').onclick=()=>step(-1);$('next').onclick=()=>step(1);")
s=s.replace("function select(id)", "function step(direction){seek((Math.round(time/(1000/60))+direction)*(1000/60));}\nfunction select(id)")
s=s.replace("seek(time-1000/60);", "step(-1);").replace("seek(time+1000/60);", "step(1);")
p.write_text(s,encoding='utf-8')
