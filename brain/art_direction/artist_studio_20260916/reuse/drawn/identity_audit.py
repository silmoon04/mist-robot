"""Read-only artwork measurement. Writes audit reports, never changes drawings."""
from pathlib import Path
import json, math, hashlib, datetime
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
source_file = ROOT / 'brain/face_assets/app/app_data.js'
data = json.loads(source_file.read_text(encoding='utf-8').split('=', 1)[1].strip().rstrip(';'))
atlas_file = HERE / 'atlas.json'
atlas = json.loads(atlas_file.read_text(encoding='utf-8'))
groups = {
 'round': ['circle_gap_02','circle_gap_03','open_C_43','open_C_50'],
 'hook': ['angry_hook_00','droop_hook_08','droop_hook_09','droop_hook_10','circle_gap_04','open_C_42','open_C_46','open_C_47','open_C_49'],
 'arc': ['closed_lid_arc_05','closed_lid_arc_06','closed_lid_arc_07','happy_arc_15','happy_arc_16','happy_arc_17','happy_arc_18','happy_arc_19'],
 'loop': ['e_shape_11','e_shape_12','e_shape_13'],
 'slot': ['open_C_44','open_C_45','open_C_48','open_C_51'],
 'chevron': ['chevron_01'], 'bar': ['flat_bar_14']
}
refs = dict(round='circle_gap_03',hook='angry_hook_00',arc='happy_arc_16',loop='e_shape_12',slot='open_C_44',chevron='chevron_01',bar='flat_bar_14')
family_for = {p:f for f, ps in groups.items() for p in ps}
def bounds(points, pad=0):
 xs,ys=zip(*points)
 return dict(x=min(xs)-pad,y=min(ys)-pad,w=max(xs)-min(xs)+2*pad,h=max(ys)-min(ys)+2*pad)
def transform(points, angle=0, mirror=False, scale=1, dx=0,dy=0):
 c,s=math.cos(angle),math.sin(angle)
 return [(dx+scale*(c*x*(-1 if mirror else 1)-s*y),dy+scale*(s*x*(-1 if mirror else 1)+c*y)) for x,y in points]
def sample(part):
 ps=part['points'][:]
 if part['kind']=='fill': ps.append(ps[0])
 lengths=[0]
 for a,b in zip(ps,ps[1:]): lengths.append(lengths[-1]+math.dist(a,b))
 result=[]
 for n in range(64):
  distance=lengths[-1]*n/(64 if part['kind']=='fill' else 63)
  i=1
  while i<len(lengths)-1 and lengths[i]<distance: i+=1
  t=(distance-lengths[i-1])/(lengths[i]-lengths[i-1] or 1)
  result.append([ps[i-1][a]+(ps[i][a]-ps[i-1][a])*t for a in [0,1]])
 mean=[sum(p[a] for p in result)/64 for a in [0,1]]
 return [[p[a]-mean[a] for a in [0,1]] for p in result]
def align(source,target):
 a,b=sample(source),sample(target)
 best=None
 for mirror in [False,True]:
  for reverse in [False,True]:
   for shift in range(0,64 if source['kind']=='fill' else 1,4):
    aa=[[x*(-1 if mirror else 1),y] for x,y in a]
    bb=[b[((63-i if reverse else i)+shift)%64] for i in range(64)]
    dot=sum(x*qx+y*qy for (x,y),(qx,qy) in zip(aa,bb))
    cross=sum(x*qy-y*qx for (x,y),(qx,qy) in zip(aa,bb))
    angle=math.atan2(cross,dot)
    pp=transform(aa,angle)
    score=sum(math.dist(p,q)**2 for p,q in zip(pp,bb))+abs(angle)*1e-8+(1e-8 if mirror else 0)
    if best is None or score<best['score']: best=dict(score=score,rotation=angle,mirror=mirror)
 return best
ink_cache={}
def ink(asset,frame):
 key=(asset['file'],frame['x'],frame['y'],frame['w'],frame['h'])
 if key in ink_cache:return ink_cache[key]
 image=Image.open(HERE/asset['file']).convert('RGBA'); pixels=image.load(); out=[]
 for y in range(frame['y'],frame['y']+frame['h']):
  for x in range(frame['x'],frame['x']+frame['w']):
   r,g,b,a=pixels[x,y]
   if a>128 and max(r,g,b)-min(r,g,b)>40:
    out.append((x+.5-frame['cx'],y+.5-frame['cy']+asset['masterHeight']/2))
 ink_cache[key]=out
 return out
notes={
 'angry_hook_00':'Family exemplar retains angry slope; generated tube is heavier and proportions differ.',
 'circle_gap_02':'Original round gap points farther upward than circle_gap_03; rotation alone is approximate.',
 'circle_gap_03':'Reference eye; generated circle is slightly different in stroke thickness and gap.',
 'circle_gap_04':'Nearly horizontal upper bar and broad lower bowl are replaced by a rotated angry hook.',
 'closed_lid_arc_05':'Shallow closed U becomes a rotated generic happy arch; preserve original U curvature.',
 'closed_lid_arc_06':'Compact rounded U becomes the generic arch; preserve width, curvature and thickness.',
 'closed_lid_arc_07':'Asymmetric U with high right endpoint is replaced by symmetric arch.',
 'droop_hook_08':'Short bottom return and almost horizontal top become generic angry hook.',
 'droop_hook_09':'Upward-sloping lid and short lower return are not the angry-hook silhouette.',
 'droop_hook_10':'Broad shallow horizontal droop is replaced by a taller angry hook.',
 'e_shape_11':'Crossbar and upper dome proportions differ from the shared loop.',
 'e_shape_12':'Loop reference; generated crossbar is thicker and upper/lower proportions differ.',
 'e_shape_13':'Tilted crossbar is part of the source contour, not just a rotated identical loop.',
 'flat_bar_14':'Same basic topology; generated bar thickness differs and squeeze can exceed rest height.',
 'happy_arc_15':'Asymmetric high-right U is treated as rotated symmetric arch.',
 'happy_arc_16':'Arch reference; generated thick stroke and width/depth proportion differ.',
 'happy_arc_17':'Asymmetric high-left U loses its endpoint relationship in shared arch.',
 'happy_arc_18':'Deep asymmetrical U is the worst arc width fit; generic arch cannot preserve it.',
 'happy_arc_19':'Shallow arch is replaced by deeper/thicker shared arch.',
 'open_C_42':'Rounded descending hook is close to angry hook but lower return differs.',
 'open_C_43':'Taller C and opening angle differ from generic circle_gap_03.',
 'open_C_44':'Slot reference; generated slot has heavier parallel bars and rounder bend.',
 'open_C_45':'Short slot and different bar spacing are replaced with identical shared slot.',
 'open_C_46':'Upward lid and broad rounded bowl differ from rotated angry hook.',
 'open_C_47':'Nearly horizontal upper lid and smaller droop become taller angry hook.',
 'open_C_48':'Near-parallel horizontal slot differs in length and bar spacing.',
 'open_C_49':'Horizontal lid and wide bowl are not equivalent to rotated angry hook.',
 'open_C_50':'Round C with broader mouth opening differs from shared round gap.',
 'open_C_51':'Curved upper bar and slightly offset terminals are lost in generic slot.',
 'chevron_01':'Only source chevron; generated elbows and thick tubing still differ.'
}
parts={}
for family,ids in groups.items():
 asset=atlas['assets'][family]; master=asset['masterWidth'],asset['masterHeight']
 for ident in ids:
  part=data['parts'][ident]; box=bounds(part['points'],part.get('width',0)/2); fit=align(data['parts'][refs[family]],part)
  angle=fit['rotation']; c,s=abs(math.cos(angle)),abs(math.sin(angle)); rw=c*master[0]+s*master[1]; rh=s*master[0]+c*master[1]
  scale=min(box['w']/rw,box['h']/rh)
  draw=transform(ink(asset,asset['frames'][0]),angle,fit['mirror'],scale,box['x']+box['w']/2,box['y']+box['h']/2)
  gen=bounds(draw)
  ratios=[gen['w']/box['w'],gen['h']/box['h']]
  norm=math.sqrt(fit['score']/64)/math.hypot(box['w'],box['h'])
  severity='high' if min(ratios)<.8 or max(ratios)>1.25 or norm>.1 else 'medium' if min(ratios)<.9 or max(ratios)>1.12 or norm>.045 else 'low'
  parts[ident]=dict(family=family,reference=refs[family],severity=severity,originalBounds=box,generatedRestBounds=gen,widthRatio=ratios[0],heightRatio=ratios[1],centerShift=[gen['x']+gen['w']/2-box['x']-box['w']/2,gen['y']+gen['h']/2-box['y']-box['h']/2],rotationDegrees=math.degrees(angle),mirrored=fit['mirror'],referenceShapeNormalizedRms=norm,notes=notes[ident],uses=[])
faces=[]
rank={'low':0,'medium':1,'high':2}
for face in data['faces']:
 entry=dict(id=face['id'],eyes=[],mouth=face['slots'].get('mouth'),severity='low')
 for role in ['eye_L','eye_R']:
  slot=face['slots'][role]; p=parts[slot['part']]; p['uses'].append(dict(face=face['id'],role=role))
  entry['eyes'].append(dict(role=role,part=slot['part'],family=p['family'],severity=p['severity'],widthRatio=p['widthRatio'],heightRatio=p['heightRatio'],slotRotation=slot.get('rot',0),slotMirror=slot.get('mirror',False)))
  if rank[p['severity']]>rank[entry['severity']]:entry['severity']=p['severity']
 entry['mouthIssues']=[]
 mouth=entry['mouth']
 if mouth:
  if abs(mouth.get('rot',0))>.5: entry['mouthIssues'].append('Preview ignores original mouth rotation '+str(mouth['rot'])+' degrees')
  if mouth.get('mirror'):entry['mouthIssues'].append('Preview ignores original mouth mirroring')
 else: entry['mouthIssues'].append('No canonical mouth: production suppresses speech mouth, preview invents fallback mouth')
 if face['id'].startswith('37'):entry['mouthIssues'].append('Preview selects smile speech set; production selects neutral speech set')
 faces.append(entry)
report=dict(status='mismatches found',checkedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope=dict(faces=len(faces),eyes=sum(len(f['eyes']) for f in faces),sourceParts=len(parts),atlasFrames=sum(len(a['frames']) for a in atlas['assets'].values())),hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source_file,atlas_file,ROOT/'brain/ui/static/drawn_face_renderer.js',HERE/'preview.js']},method=['Visually inspected faces_sheet.png, eyes_sheet.png, all seven initial generated eye sheets and both accepted v2 eye sheets.','Independently reproduced source-to-reference rigid registration and renderer min-scale math.','Measured actual generated rest-cel ink pixels, not just crop rectangles, after the renderer transform.','Original bounds use dense source contour points plus stroke radius. Curved SVG smoothing can move extrema slightly.','Ratio severity is diagnostic: high means below 0.8 or above 1.25 on either dimension, or >0.1 normalized source-reference RMS. It is not a perceptual quality score.','Low severity does not mean exact identity match. All 30 source shapes are replaced by seven generated representatives at rest.'],parts=parts,faces=faces,findings=[{'severity':'high','issue':'Canonical identities replaced at rest','detail':'Every eye uses its generated family representative at rest; grouping was broad motion compatibility, not shape equivalence.','fix':'Keep canonical source art for rest and settled; preserve exact slot placement. Use generated cels only within blink, with per-part retargeting.'},{'severity':'high','issue':'Arbitrary rectangle rotation shrinks eyes','detail':'Uniform scale uses rotated master rectangle bounds. Rotating a mostly empty rectangle overestimates ink extents and can substantially shrink both dimensions.','fix':'Fit measured ink support or explicit family basis, not rotated crop rectangles. Enforce source width and endpoints in per-part blink retargeting.'},{'severity':'high','issue':'Mid-transition hard cut','detail':'rigAt selects previous before half and current after half. Blink only changes lid pose; mouth, tears, eye slots and sizes jump at the midpoint.','fix':'Interpolate shared layer placement and use opacity transitions for incompatible topology. Keep speech timeline independent of expression changes.'},{'severity':'medium','issue':'Preview and production speaking geometry disagree','detail':'Preview clamps mouth width and omits rotation/mirror; production uses raw width, rotation/mirror and face fitting. Face 37 uses different mouth family. Faces 12 and 35 have no mouth: preview fabricates one, production cannot speak visually.','fix':'One shared renderer and explicit per-face speech policy.'}],recommendation='Preserve exact canonical artwork outside blink; use reusable transitions on layer transforms and opacity, with generated intermediate cels retargeted per source part. The model should select semantic face intents and duration, not part IDs or frame indices.')
(HERE/'identity_audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
lines=['# Face identity audit','', 'Coverage: 40 faces, 80 placed eyes, 30 source eye parts. This report records the implementation before identity fixes.','', 'Generated rest ink / original dimensions. Values below 1 mean the rest eye is smaller than the canonical eye. Severity is a diagnostic threshold, not a naturalness rating.','', '| Part | Family | Severity | Width | Height | Alignment angle | Affected faces |','|---|---|---|---:|---:|---:|---|']
for p,v in sorted(parts.items(),key=lambda x:(-rank[x[1]['severity']],x[1]['widthRatio'],x[0])):
 lines.append(f"| {p} | {v['family']} | {v['severity']} | {v['widthRatio']:.2f} | {v['heightRatio']:.2f} | {v['rotationDegrees']:.1f} | {', '.join(sorted(set(u['face'][:2] for u in v['uses'])))} |")
lines+=['','## Findings','']
for f in report['findings']:lines += [f"**{f['severity']}: {f['issue']}**",'',f['detail'],'',f"Fix: {f['fix']}",'']
lines+=['## Per-face review','','| Face | Left eye | Right eye | Severity | Mouth issue |','|---|---|---|---|---|']
for f in faces:lines.append(f"| {f['id']} | {f['eyes'][0]['part']} | {f['eyes'][1]['part']} | {f['severity']} | {'; '.join(f['mouthIssues']) or 'No extra transform discrepancy detected'} |")
(HERE/'identity_audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'scope':report['scope'],'partSeverity':{s:sum(p['severity']==s for p in parts.values()) for s in rank},'faceSeverity':{s:sum(f['severity']==s for f in faces) for s in rank},'worstParts':[{ 'part':p,'w':round(v['widthRatio'],3),'h':round(v['heightRatio'],3),'faces':sorted(set(u['face'][:2] for u in v['uses']))} for p,v in sorted(parts.items(),key=lambda x:min(x[1]['widthRatio'],x[1]['heightRatio']))[:10]]},indent=2))
