"""Build a portable artist brief from a proposed scope and current face references."""
from pathlib import Path
import csv,hashlib,html,json,shutil,subprocess,zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

EYES=[
 ('E01','Available','Relaxed open eyes; warm enough to sit with, not a permanent grin.','39_neutral_02_manual'),
 ('E02','Listening','Open and attentive, a little more lifted than E01.','25_neutral_2_03_manual'),
 ('E03','Happy','A clear smile in the eyes; retain some irregularity.','09_happy_03_manual'),
 ('E04','Focused','A soft squint, engaged rather than angry.','40_neutral_03_manual'),
 ('E05','Concerned','Gentle inner lift; empathetic, not crying by default.','32_sad_07_manual'),
 ('E06','Sleepy','Heavy lids and relaxed weight.','16_misc_16_manual'),
 ('E07','Annoyed','A mild flat-lidded deadpan, never the default.','07_annoyed_03_manual'),
 ('E08','Surprised','A brief clear widening without enormous eyes.','38_misc_2_06_manual'),
 ('E09','Curious','Small asymmetry; one eye slightly more lifted.','20_neutral_06_manual'),
 ('E10','Playful','A restrained side-eye or unequal squeeze.','10_happy_04_manual'),
]
MOUTHS=[('M01','Rest','Closed relaxed line; not an O.','rest'),('M02','Warm smile','Small uneven smile, not a large grin.',None),
 ('M03','Concern','Small shallow frown; keep the same anchor.',None),('M04','Playful','Small asymmetric smile.',None),
 ('M05','Lips together','A definite closed contact for M/B/P, distinct from relaxed rest.','MBP'),
 ('M06','Open speech','Medium open A; primary amplitude-driven talking pose.','AA'),
 ('M07','Wide speech','Wider, shallower E; keep corners soft.','EE'),
 ('M08','Round speech','Rounded O/U; also a brief surprise accent.','OO')]
POSES=[
 ('F01','Available','E01','M01','neutral','39_neutral_02_manual','Default between interactions. Tiny gaze changes; most of the time still.'),
 ('F02','Listening','E02','M01','listening','25_neutral_2_03_manual','Attend to the user. Closed mouth. One small settle when speech starts.'),
 ('F03','Thinking','E04','M01','thinking','39_neutral_02_manual','Closed mouth, gaze slightly up and sideways. No repeated talking motion.'),
 ('F04','Happy','E03','M02','happy','09_happy_03_manual','A short lift or squeeze for a real success. Then settle.'),
 ('F05','Curious','E09','M01','curious','20_neutral_06_manual','Unequal eye lift; keep the question gentle.'),
 ('F06','Focused','E04','M01','focused','40_neutral_03_manual','Same art as thinking, centered gaze. For checking a result.'),
 ('F07','Concerned','E05','M03','sad','32_sad_07_manual','Empathetic and quiet. No tears in the first release.'),
 ('F08','Sleepy','E06','M01','sleepy','16_misc_16_manual','Slow settle and occasional long blink; not the busy indicator.'),
 ('F09','Deadpan','E07','M01','angry','07_annoyed_03_manual','Mild irritation or dry humor, only when context supports it.'),
 ('F10','Surprised','E08','M08','surprised','38_misc_2_06_manual','Brief widened reaction. Close the O again rather than hold it indefinitely.'),
 ('F11','Playful','E10','M04','mischief','10_happy_04_manual','One small asymmetrical accent. No repeated wink loop.'),
 ('F12','Reassuring','E05','M02','reassuring','14_happy_16_manual','Concerned eyes plus a small smile. Calm and present.'),
]

def manifest():
    rows=[]
    for id,name,brief,ref in EYES:rows.append(dict(id=id,group='Base eye pairs',name=name,draw=brief,reference=ref,pilot=id in ('E01','E04'),unit='eye pair'))
    for id,name,brief,viseme in MOUTHS:rows.append(dict(id=id,group='Mouths',name=name,draw=brief,reference=viseme or 'rest',pilot=id in ('M01','M06'),unit='mouth'))
    for i,(family,base) in enumerate([('open','E01'),('happy','E03'),('focused','E04'),('downcast','E05')]):
        for j,state in enumerate(['half_closed','closed']):
            id=f'B{i*2+j+1:02d}';rows.append(dict(id=id,group='Blink eye pairs',name=family+' '+state.replace('_',' '),draw=f'{state.replace("_"," ").capitalize()} lid drawing for the {family} family. Match {base} anchors and line weight.',reference=base,pilot=id in ('B01','B02'),unit='eye pair'))
    accents=[('Surprise anticipation','Brief inward squash before E08 opens.','E08'),('Surprise overshoot','Slightly wider than E08, then settle back.','E08'),('Happy squeeze','Compressed happy eyes for a one-off reaction.','E03'),('Thinking squint','Brief extra focus, then return to E04.','E04'),('Playful asymmetry','A readable asymmetric accent for E10.','E10'),('Sleepy droop','A little heavier than E06, then recover.','E06')]
    for i,(name,draw,ref) in enumerate(accents):rows.append(dict(id=f'A{i+1:02d}',group='Accent eye pairs',name=name,draw=draw,reference=ref,pilot=False,unit='eye pair'))
    for i,base in enumerate(['E01','E03','E04']):
        for j,variant in enumerate(['B','C']):rows.append(dict(id=f'R{i*2+j+1:02d}',group='Alternate eye redraws',name=base+' redraw '+variant,draw='A subtly different contour of the same pose. Keep position, scale, expression and average line weight unchanged.',reference=base,pilot=False,unit='eye pair'))
    assert len(rows)==38 and sum(r['pilot'] for r in rows)==6
    return {'status':'Proposed artist scope, not approved new art or a production runtime change','date':'2026-09-16',
      'counts':{'production_component_drawings':38,'eye_pair_drawings':30,'individual_eye_layers':60,'mouth_drawings':8,'pose_compositions':12,'pilot_components_included_in_38':6,'style_exploration_composites_separate':6},
      'rows':rows,'poses':[dict(zip(['id','name','eyes','mouth','state','reference','direction'],r)) for r in POSES],
      'canvas':{'logical_width':100,'logical_height':64,'master_width':1600,'master_height':1024,'eye_L_anchor':[28,29.4],'eye_R_anchor':[72,29.4],'mouth_anchor':[50,49.5],'safe_box':[5.5,5.5,94.5,58.5]},
      'limits':['Reference faces were derived from surviving local assets, not new artist work. Original capture sources are missing; ownership and license of earlier reference designs have not been established in this pack. Treat them as functional references, not a request to copy another designer.','A timeline exposure is not a new drawing. An eye-pair unit contains two separately editable eye layers.','Full viseme-driven speech and alternate-drawing playback require runtime integration. Current production speech mainly uses AA/rest.']}

def template(row):
    guide='''<rect x="5.5" y="5.5" width="89" height="53" fill="none" stroke="#8d979e" stroke-width=".15" stroke-dasharray="1 1"/><path d="M28 10V57M72 10V57M8 29.4H92M8 49.5H92" fill="none" stroke="#82939b" stroke-width=".12"/><circle cx="28" cy="29.4" r=".45" fill="#b37a26"/><circle cx="72" cy="29.4" r=".45" fill="#b37a26"/><circle cx="50" cy="49.5" r=".45" fill="#b37a26"/>'''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="1600" height="1024" viewBox="0 0 100 64">
<title>{row['id']} {html.escape(row['name'])}: blank drawing template</title>
<desc>Proposed asset. No new art is supplied. Hide GUIDES and REFERENCE before exporting. Keep full canvas registration.</desc>
<g id="GUIDES" opacity=".5">{guide}<text x="6" y="8" font-size="1.5" fill="#66757b">{row['id']} | {html.escape(row['name'])} | hide guides before export</text></g>
<g id="REFERENCE" style="display:none"/>
<g id="eye_L" fill="#5eeadd"/><g id="eye_R" fill="#5eeadd"/><g id="mouth" fill="#5eeadd"/><g id="accents" fill="#5eeadd"/>
</svg>'''

def main():
    data=manifest();(HERE/'assets').mkdir(exist_ok=True);(HERE/'templates').mkdir(exist_ok=True);(HERE/'references').mkdir(exist_ok=True)
    (HERE/'drawing_manifest.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    with (HERE/'drawing_checklist.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=['id','group','name','unit','pilot','draw','reference','status','artist_notes']);writer.writeheader()
        for row in data['rows']:writer.writerow({**row,'status':'not started','artist_notes':''})
    clips=[('idle_available',96,'F01 + B01/B02','Tiny gaze shift and one blink'),('listening_hold',72,'F02','Closed mouth; attentive hold'),('thinking_hold',96,'F03 + A04','Closed mouth; offset gaze; one squint')]
    for family,start in [('open',1),('happy',3),('focused',5),('downcast',7)]:clips.append((f'blink_{family}',6,f'base + B{start:02d}/B{start+1:02d}','OPEN HALF CLOSED CLOSED HALF OPEN'))
    clips.extend([('neutral_to_thinking',8,'F01 -> F03; blink families','T02 blink bridge'),('neutral_to_happy',8,'F01 -> A03 -> F04','T03 happy accent'),('neutral_to_surprise',8,'A01 -> A02 -> F10','T03 anticipate and settle'),('happy_to_concerned',8,'F04 -> F07; blink families','T02 test mouth and eye change')])
    for mood,pose in [('neutral','F01'),('happy','F04'),('concerned','F07')]:clips.append((f'speech_{mood}',72,f'{pose} eyes + M01/M05/M06/M07/M08','Same speech test over different eye expressions'))
    clips.append(('speech_interrupt',24,'speech mouth -> closed mouth; F02','Stop speech with audio; listening wins'))
    assert len(clips)==15 and sum(c[1] for c in clips)==560
    with (HERE/'animation_clips.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f);writer.writerow(['clip','timeline_frames','fps','duration_ms','reuse_components','direction','new_drawings']);
        for name,frames,parts,direction in clips:writer.writerow([name,frames,24,round(frames/24*1000,3),parts,direction,'0 beyond the 38 listed components'])
    for row in data['rows']:(HERE/'templates'/f"{row['id']}_{row['name'].replace(' ','_')}.svg").write_text(template(row),encoding='utf-8')
    shutil.copyfile(ROOT/'brain/ui/static/face_runtime.js',HERE/'assets/face_runtime.js')
    shutil.copyfile(ROOT/'brain/face_assets/app/app_data.js',HERE/'assets/app_data.js')
    for name in ['board.js','board.css']:shutil.copyfile(HERE/name,HERE/'assets'/name)
    (HERE/'assets/brief_data.js').write_text('window.ARTIST_BRIEF='+json.dumps(data,ensure_ascii=True)+';\n',encoding='utf-8')
    subprocess.run(['node',str(HERE/'render_references.cjs')],cwd=ROOT,check=True)
    source=HERE/'page.html';page=source.read_text(encoding='utf-8')
    for token,file in [('@@BRIEF@@','START_HERE.md'),('@@MOTION@@','MOTION_GUIDE.md')]:
        page=page.replace(token,html.escape((HERE/file).read_text(encoding='utf-8')))
    (HERE/'index.html').write_text(page,encoding='utf-8')
    alltext='\n\n'.join((HERE/name).read_text(encoding='utf-8') for name in ['START_HERE.md','MOTION_GUIDE.md','DELIVERY_SPEC.md','MESSAGE_TO_ARTIST.txt'])
    (HERE/'artist_brief.txt').write_text(alltext,encoding='utf-8')
    print(json.dumps({'components':len(data['rows']),'pilot':sum(r['pilot'] for r in data['rows']),'folder':str(HERE)}))

if __name__=='__main__':main()
