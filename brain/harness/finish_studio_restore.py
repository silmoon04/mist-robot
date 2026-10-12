from pathlib import Path
root=Path(__file__).resolve().parents[1]/'art_direction/artist_studio_20260916'
p=root/'studio.css';s=p.read_text(encoding='utf-8')+'\n.inspector dd{overflow-wrap:anywhere;min-width:0}\n';p.write_text(s,encoding='utf-8')
p=root/'studio.js';s=p.read_text(encoding='utf-8');s=s.replace("['Eyes',state.eyes],['Rest mouth',state.mouth]", "['Eyes',S.data.faces.find(f=>f.id===state.sources[Math.max(0,state.options.indexOf(option))]).slots.eye_L?.part||'none'],['Rest mouth',S.data.faces.find(f=>f.id===state.sources[Math.max(0,state.options.indexOf(option))]).slots.mouth?.part||'none']")
p.write_text(s,encoding='utf-8')
p=root/'index.html';s=p.read_text(encoding='utf-8').replace('State alternatives','Existing variants').replace('Core + state alternatives','Core + existing variants')
s=s.replace('The alternative state previews','The existing variant previews')
s=s.replace('Existing MIST assets','Existing MIST assets')
p.write_text(s,encoding='utf-8')
p=root/'artist_notes.txt';s=p.read_text(encoding='utf-8').replace('Reaction clips hold existing expressions; no new reaction contour is drawn.','Reaction clips hold existing expressions; no new reaction contour is drawn. The six-frame blink exports sample the existing 185 ms procedural blink. The eight-frame transitions sample the existing 260 ms renderer transition. The artist blink/transition recipes above remain proposals, not replacements for those routines.')
s=s.replace('These are generated previews.','These are generated frames from existing assets.')
p.write_text(s,encoding='utf-8')
