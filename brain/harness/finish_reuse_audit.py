from pathlib import Path
import json,shutil,xml.etree.ElementTree as ET,hashlib,csv
root=Path(__file__).resolve().parents[2]
out=root/'brain/art_direction/artist_studio_20260916/reuse'
motion={
 'Round gap':['circle_gap_02','circle_gap_03','open_C_43','open_C_50'],
 'Hooked lid':['angry_hook_00','droop_hook_08','droop_hook_09','droop_hook_10','circle_gap_04','open_C_42','open_C_46','open_C_47','open_C_49'],
 'Arc':['closed_lid_arc_05','closed_lid_arc_06','closed_lid_arc_07','happy_arc_15','happy_arc_16','happy_arc_17','happy_arc_18','happy_arc_19'],
 'Loop with crossbar':['e_shape_11','e_shape_12','e_shape_13'],
 'Narrow slot':['open_C_44','open_C_45','open_C_48','open_C_51'],
 'Chevron':['chevron_01'],
 'Flat bar':['flat_bar_14']}
audit=json.loads((out/'audit.json').read_text());audit['motion_families']=motion
assert sorted(p for v in motion.values() for p in v)==sorted(g['id'] for g in audit['groups'] if g['kind']=='eyes')
rows=[]
for clip in audit['studio_clips']:
 for p in sorted((out.parent/'frame_assets'/clip['clip']).glob('*.svg')):
  tree=ET.parse(p).getroot()
  for i,path in enumerate(tree.findall('.//{http://www.w3.org/2000/svg}path')):
   rows.append({'clip':clip['clip'],'status':clip['status'],'frame':p.stem,'source_face':tree.get('data-source',''),'layer_index':i,'role':path.get('data-role','unlabelled'),'part':path.get('data-part','unlabelled'),'path_sha256':hashlib.sha256(ET.tostring(path)).hexdigest()})
with (out/'studio_layers.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
audit['studio_path_layers_audited']=len(rows)
(out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');(out/'audit.js').write_text('window.REUSE_AUDIT='+json.dumps(audit)+';\n')
pilot=out/'imagegen_pilot';pilot.mkdir(exist_ok=True)
shutil.copy2('<LOCAL_HOME>/.codex/generated_images/01a0a95c-7264-71d1-9c8d-9bb094301225/exec-4f804d33-512d-495d-ad0c-1b2a7a74ef47.png',pilot/'blink_study.png')
(pilot/'review.txt').write_text('ImageGen built-in tool, one reference-based blink strip. Not accepted for production.\nThe half-closed frames have different upper-arc directions. The eye splits into disconnected contours, registration changes, and edge specks remain. Keep this as a failed continuity study. Existing components remain the production source. No generated cel was substituted in the previews.\n')
prompt='''Use case: precise-object-edit. Asset type: animator key-pose study, a single horizontal four-cell sprite strip on a genuinely transparent background. Reference image is the existing MIST single round eye, not a whole face. Preserve its turquoise color #5eeadd, thick rounded stroke, left-facing small gap, silhouette, and simple robot identity. Generate four equally sized cells from left to right: original open eye; halfway closing eye with the top arc lowered toward the lower lid; fully closed gentle curved lower lid; halfway reopening eye matching the second cel. Each cel contains exactly one eye with identical horizontal center registration relative to its cell, same width and line weight, bottom lid registration fixed. Subtle clean hand-drawn character and smooth confident contour; no scribbles, no texture noise, no pupils, no eyeballs, no lashes, no mouth, no face, no extra symbols, no text or labels, no borders, no glow, no shadow. Keep generous empty margins. This is a conservative motion study of the existing asset, not a style redesign. The closed lid should be a single solid rounded stroke, not a flattened ring.'''
(pilot/'prompt.txt').write_text(prompt+'\n')
p=out/'reuse.js';s=p.read_text(encoding='utf-8')
s=s.replace("head('Drawing list');const n=A.counts;$('#content').innerHTML=`", "head('Drawing list');const n=A.counts;$('#content').innerHTML=`<p><b>Start with 14 drawings:</b> one round eye, its half-closed and closed poses, and the 11 shared speech mouths. Test that small set before repainting the whole library.</p><details><summary>7 eye motion groups</summary><p class=\"note\">These share an animation recipe, not necessarily an identical silhouette. Keep their existing variants; transfer timing and closure behaviour between them.</p><table>${Object.entries(A.motion_families).map(([name,ids])=>`<tr><th>${name}</th><td>${ids.join(', ')}</td></tr>`).join('')}</table></details>")
s=s.replace('<details><summary>ImageGen</summary>', '<details><summary>ImageGen pilot / needs cleanup</summary><img style="width:100%;background:#0c1411" src="imagegen_pilot/blink_study.png" alt="Unapproved generated blink strip"><p class="note">The first test changed the upper arc between closing and reopening, moved the registration, and left edge specks. It is not ready to use. Existing reference frames remain unchanged.</p><a href="imagegen_pilot/prompt.txt" download>Generation prompt</a>')
p.write_text(s,encoding='utf-8')
p=out/'artist_notes.txt';s=p.read_text(encoding='utf-8').replace('The current pack contains deterministic renders of existing assets. It does not contain AI-painted replacement artwork.','The working frame folders contain deterministic renders of existing assets. The separate imagegen_pilot folder holds one unapproved generated strip and its prompt. Its half-closed poses differ in contour and registration, so it was not adopted.')
s+='\nSuggested first commission: 14 component drawings. One round open eye, half-closed and closed versions, and 11 speech mouth poses. Prove the look on that small set before repainting everything.\nSeven eye motion groups share timing recipes while retaining their exact source outlines: '+', '.join(motion)+'.\n'
p.write_text(s,encoding='utf-8')
p=out.parent/'index.html';s=p.read_text(encoding='utf-8').replace('<nav aria-label="Views">','<nav aria-label="Views"><a href="reuse/" style="padding:7px 10px">Reuse map</a>')
p.write_text(s,encoding='utf-8')
print(json.dumps({'studio_path_layers_audited':len(rows),'motion_families':len(motion)}))
