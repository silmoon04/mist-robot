from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1];studio=root/'art_direction/artist_studio_20260916'
(studio/'existing').mkdir(exist_ok=True)
shutil.copyfile(root/'face_assets/app/app_data.js',studio/'existing/app_data.js')
shutil.copyfile(root/'ui/static/face_runtime.js',studio/'existing/face_runtime.js')
p=studio/'index.html';s=p.read_text(encoding='utf-8').replace('Concept preview','Existing MIST assets').replace('downloads/available_smile.zip','downloads/available_neutral_39.zip')
s=s.replace('<script src="scene.js"></script><script src="data.js"></script><script src="studio.js"></script>','<script src="existing/app_data.js"></script><script src="existing/face_runtime.js"></script><script src="scene.js?v=existing1"></script><script src="data.js?v=existing1"></script><script src="studio.js?v=existing1"></script>')
s=s.replace('Preview PNGs are generated references, not finished artist drawings.','Preview frames use existing MIST assets. Drawing counts are the optional artist brief.').replace('new component drawings','proposed artist drawings')
p.write_text(s,encoding='utf-8')
p=studio/'studio.js';s=p.read_text(encoding='utf-8').replace("$('input-label').hidden=state.id!=='listening'||$('action').value!=='state';","$('input-label').hidden=true;")
p.write_text(s,encoding='utf-8')
p=studio/'export.cjs';s=p.read_text(encoding='utf-8').replace("+(s.id==='available'?'':' + procedural indicator')",'').replace("'Concept study. Not installed in the robot.'","'Existing MIST assets and renderer. Artist drawing scope is a separate proposal.'")
p.write_text(s,encoding='utf-8')
p=studio/'artist_notes.txt';s=p.read_text(encoding='utf-8');start=s.index('Four faces can speak:')
s='MIST face study: existing assets restored\n\nThe studio and frame downloads now use the original MIST face assets and animation renderer. No newly drawn eyes, mouths, waveforms, headphones or loading indicators are used. Available, listening and thinking offer existing variants for comparison. The proposed artist workload remains separate from these existing reference frames.\n\n'+s[start:]
a=s.index('The waveform, headphones and orbit');b=s.index('\n\nTemplates:',a)
s=s[:a]+'Any new waveform, headphones or loading indicator would be future work. Those concepts have been removed. Reaction clips hold existing expressions; no new reaction contour is drawn.'+s[b:]
p.write_text(s,encoding='utf-8')
