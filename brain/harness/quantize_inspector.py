from pathlib import Path
p=Path(__file__).resolve().parents[1]/'duplex/static/expressions.js'
s=p.read_text(encoding='utf-8').replace('time=Math.max(0,Math.min(4000,value));','time=Math.max(0,Math.min(4000,Math.round(value/(1000/60))*(1000/60)));')
s=s.replace("$('play').onclick=()=>{playing=!playing;$('play').textContent=playing?'Pause':'Play';last=performance.now();};", "$('play').onclick=()=>{playing=!playing;if(!playing){seek(time);return;}$('play').textContent='Pause';last=performance.now();};")
p.write_text(s,encoding='utf-8')
