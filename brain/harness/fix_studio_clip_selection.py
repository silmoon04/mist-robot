from pathlib import Path
root=Path(__file__).resolve().parents[1]/'art_direction/artist_studio_20260916'
p=root/'studio.js';s=p.read_text(encoding='utf-8')
s=s.replace("if(mode==='speech')return'speech_'+state.id;","if(mode==='speech'||(mode==='state'&&state.kind==='Speaking'))return'speech_'+state.id;")
s=s.replace("$('action').value='state';for(const button", "$('action').value=s.kind==='Speaking'?'speech':'state';for(const button")
s=s.replace("$('action').querySelector('[value=speech]').disabled=!state.talk;", "$('action').querySelector('[value=speech]').disabled=!state.talk;$('action').querySelector('[value=state]').disabled=state.kind==='Speaking';")
p.write_text(s,encoding='utf-8')
p=root/'index.html';s=p.read_text(encoding='utf-8').replace('v=existing1','v=existing2');p.write_text(s,encoding='utf-8')
