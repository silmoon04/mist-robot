from pathlib import Path
import json,csv,hashlib,zipfile,shutil,html
ROOT=Path(__file__).resolve().parent;DESIGN=ROOT.parent
PRINT=DESIGN/'fourth_leg_20260917/print'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
with (PRINT/'SHA256SUMS.csv').open(newline='') as f:
 for row in csv.DictReader(f):
  p=PRINT/row['file'];assert p.is_file() and sha(p)==row['sha256'],p
  checks.append({'file':row['file'],'sha256':sha(p),'status':'matches saved checksum'})
archive=DESIGN/'fourth_leg_20260917/Fourth_Leg_Print_Set.zip'
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for p in PRINT.iterdir():
  if p.is_file():assert z.read(p.name)==p.read_bytes(),p
r=json.loads((PRINT/'Fourth_Leg_Check.json').read_text())
assert r['plate_1']['sha256']==sha(PRINT/'01_Main_Parts_With_Supports.stl')
assert r['plate_2']['sha256']==sha(PRINT/'02_Brackets_And_Caps.stl')
assert r['profile_sha256']==sha(PRINT/'Neptune4Pro_Recovery_Balanced_028.curaprofile')
for row in r['plate_2']['parts']:
 assert row['source_sha256']==sha(DESIGN/'third_leg_20260916/output/print_stl'/(row['name']+'.stl'))
assets=ROOT/'assets';assets.mkdir(exist_ok=True)
for name in ['Plate_2_Map.png','Support_Map.png','Femur_Upper_Lip_Support.png']:shutil.copy2(PRINT/name,assets/name)
parts=[('P1-A','coxa_upper_and_hip_saddle','Upper coxa and hip case saddle'),('P1-B','femur_main_and_knee_saddle','Main femur and knee case saddle'),('P1-C','tibia_curved_main_and_foot','Straight tibia and foot')]
parts += [('P2-'+str(i),row['name'],row['name'].replace('_',' ')) for i,row in enumerate(r['plate_2']['parts'],1)]
rows=''.join('<tr><td><input type="checkbox" aria-label="Present '+pid+'"> '+pid+'</td><td><code>'+name+'</code></td><td>'+desc+'</td></tr>' for pid,name,desc in parts)
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fourth leg: inspect and assemble</title>
<style>body{font:16px/1.5 system-ui,sans-serif;color:#19323b;background:#f6f7f3;margin:auto;max-width:1080px;padding:28px}h1{font-size:30px}h2{margin-top:32px}table{border-collapse:collapse;width:100%;background:white}th,td{padding:9px;border:1px solid #c7d3d6;text-align:left}code{font-size:13px;overflow-wrap:anywhere}img{max-width:100%;height:auto}section,.note{background:white;padding:18px;margin:16px 0;border:1px solid #cad5d6;border-radius:8px}.note{border-left:5px solid #c48a32}input{width:18px;height:18px}li{margin:9px 0}.images{display:grid;grid-template-columns:1fr 1fr;gap:16px}a{color:#075b86}@media(max-width:750px){.images{display:block}body{padding:14px}}@media print{body{background:white;padding:0;font-size:11px}section{break-inside:avoid}a{color:inherit}}</style>
<h1>Fourth leg: inspect what you have, then assemble</h1>
<p>8 October 2026. Use this alongside the saved fourth-leg package. <strong>This is not a request to print again.</strong> First identify which parts are already complete. Checkboxes are temporary inspection marks and are not saved or treated as reported results.</p>
<div class="note"><strong>Known from your reports:</strong> two full legs and the hub were assembled/printed earlier; you confirmed that the 13 mm spacers fit and the joint turns freely. The fast third-leg print lost the coxa and tibia, and the femur was stopped unfinished. <strong>Still unknown:</strong> whether the corrected recovery print and fourth-leg plates finished, released cleanly and assembled successfully.</div>
<p><a href="../fourth_leg_20260917/Fourth_Leg_Print_Set.zip">Existing fourth-leg package</a> · <a href="../fourth_leg_20260917/print/START_HERE.txt">Package instructions</a> · <a href="audit.json">File consistency audit</a></p>
<h2>1. Account for ten parts and four reused spacers</h2>
<p>P1-A/B/C identify the three main parts below. P2 numbers match the existing plate-map numbers. Exact part IDs are shown so similarly named old parts are not substituted accidentally.</p>
<table><tr><th>Present</th><th>Exact part ID</th><th>Role</th></tr>'''+rows+'''</table>
<p><input type="checkbox"> Four matching existing spacers: <strong>13 mm height, 5.5 mm OD, 3.4 mm bore</strong>. No new spacers needed. Do not mix in the old 11.3/11.6/11.9 mm trial pieces.</p>
<div class="images"><figure><img src="assets/Support_Map.png" alt="Three main parts in order: coxa, femur, tibia; orange indicates removable supports"><figcaption>Plate 1: left P1-A, middle P1-B, right P1-C. Orange supports are removed; blue ribs and feet stay.</figcaption></figure><figure><img src="assets/Plate_2_Map.png" alt="Seven numbered brackets and caps in the second plate"><figcaption>Plate 2: labels P2-1 through P2-7 follow these numbers.</figcaption></figure></div>
<h2>2. Inspect before spending time on assembly</h2>
<table><tr><th>Check</th><th>Go</th><th>No-go: keep part aside</th></tr>
<tr><td>P1-A coxa</td><td>Post, both saddle ends and holes are complete; base sits without rocking.</td><td>Lifted/twisted base, loose strands replacing a wall, split layers or missing clamp tab.</td></tr>
<tr><td>P1-B femur</td><td>Both saddle levels and the small upper lip are complete after removing supports.</td><td>Flat stop layer below the full top, missing upper lip, sagged strands where solid material should be.</td></tr>
<tr><td>P1-C tibia</td><td>Shank and toe are continuous, bridge has two intact fixings.</td><td>Detached print, torn layers, incomplete toe or cracks around either fixing.</td></tr>
<tr><td>All mating faces</td><td>Support remnants and brim clear; pieces seat without using screws to pull them together.</td><td>Force needed to overcome a mismatch, cracked nut wall or crooked insert.</td></tr></table>
<details><summary>See the upper femur support location</summary><img src="assets/Femur_Upper_Lip_Support.png" alt="Transparent femur showing the added tall support to the upper lip"></details>
<h2>3. Hardware for this revision</h2>
<table><tr><th>Connection</th><th>Hardware and location</th><th>Fit gate</th></tr>
<tr><td>Three fixed servo case clamps</td><td>9 × M3×30, 9 nuts, one flat washer per screw. Yaw: P2-1 + P2-2. Hip: P1-A + P2-4. Knee: P1-B + P2-6.</td><td>Case seats fully; cap engages all screws evenly. Preserve the designed small gap; do not crush the cap shut.</td></tr>
<tr><td>Femur and tibia bridge closures</td><td>3 × M3 inserts, 4 mm OD × 5 mm long; 3 × M3×10; one 0.5 mm flat washer each. One insert in P1-B, two in P1-C.</td><td>Insert flush and square; cheek seats, screw engages without bottoming. With 5 mm cheek and 0.5 mm washer, nominal engagement is 4.5 mm.</td></tr>
<tr><td>Main horn peripheral holes</td><td>12 × M3×6, each with one 0.5 mm washer across yaw, hip and knee.</td><td>Metal horn threads engage without bottoming; retain the supplied centre retainer separately.</td></tr>
<tr><td>Pitch auxiliary discs</td><td>8 × M3×12; TWO 0.5 mm washers per screw. Four at P2-5 femur cheek, four at P2-7 tibia cheek.</td><td>Integral stand-off rings face inward; do not add loose spacers beneath those rings.</td></tr>
<tr><td>Coxa post closure</td><td>2 × M3×20 with two post nuts and one washer per screw; P1-A + P2-3.</td><td>Load the nuts before closing access. No hammering or forced alignment.</td></tr>
<tr><td>Yaw auxiliary side</td><td>Four reused 13 mm spacers. Historical BOM lists four M3×20 with two 0.5 mm washers each; that calculation used 11.6 mm spacers.</td><td><strong>Unresolved stack:</strong> preserve the hardware arrangement from your physically working joint. Do not treat the historical screw/washer stack as revalidated for 13 mm.</td></tr></table>
<p>Also needed: three STS3215 servos, three matching main horns, three auxiliary discs, their supplied centre screws/retainer washers, and bus cables. Washer OD was reported around 7.7 mm; the 0.5 mm thickness used above remains a design assumption unless measured. This list excludes hub mounting hardware.</p>
<div class="note"><strong>Revision trap:</strong> the older September 15 animation/guide shows long bridge screws and captive bridge nuts. For P1-B/P1-C in this package use the three inserts and M3×10 screws above. Leave the old internal bridge nut slots empty. Never put the M3×30 bridge screws into the new inserts.</div>
<h2>4. Assembly sequence and stop points</h2>
<ol><li><strong>Prepare the bare prints.</strong> Remove only support/brim. Check all three main parts against section 2. Fit the three inserts before enclosing access, following your established heat-insertion process, and let them cool.</li>
<li><strong>Yaw case and coxa.</strong> Match P2-1/P2-2 around the yaw servo. Fit the supplied discs and retainers, then P1-A to the main horn. Keep the auxiliary retainer washer on the fixed stub, not clamping the rotating disc.</li>
<li><strong>Hip case and lower coxa.</strong> Put the hip case inward in P1-A and close with P2-4. Fit the post nuts, then P2-3 and four matching spacers. Stop if the stack only aligns when pulled together by screws.</li>
<li><strong>Femur and knee case.</strong> Attach P1-B to the hip main horn. Seat the knee servo in its saddle and fit P2-6. Fit P2-5 with its ring inward, attach to the auxiliary disc, then close the bridge with one M3×10 and washer.</li>
<li><strong>Tibia.</strong> Attach P1-C to the knee main horn. Fit P2-7 ring inward, attach to the auxiliary disc, then close the two bridge holes with two M3×10 screws and washers.</li>
<li><strong>Static review before hub integration.</strong> Confirm seated mating faces, intact tabs, accessible cables and no loose spacers or screws. Compare with an existing working leg. Keep power off for this inspection; this checklist does not command servo motion or set raw servo positions. Stop for any binding or mismatch already observed.</li></ol>
<h2>Expected fit versus measured results</h2><p>The archived files and checksums were verified today. The corrected supports and insert geometry are the saved revision, not new changes. CAD fit and slicer checks do not demonstrate completed prints, insert pullout strength, screw engagement in the changed yaw stack or loaded four-leg operation.</p>
<p><strong>Next observation:</strong> Did the corrected main-parts plate finish with an intact upper femur lip and with all three parts staying attached to the bed?</p></html>'''
(ROOT/'Inspection_And_Assembly.html').write_text(page,encoding='utf-8')
audit={'checked_on':'2026-10-08','status':'package bytes and saved references consistent','archive_sha256':sha(archive),'files':checks,'zip_matches_folder':True,'plate_2_source_hashes_match':True,
 'physical_result':'Recovery and fourth-leg print/fit results unreported. No new print, device operation or geometry change performed.',
 'finding':{'id':'MECH-ASM-REV-01','evidence':'September 15 assembly guide specifies 11.6 mm spacers and M3x30 captive-nut bridges; September 17 package specifies reused 13 mm spacers and M3x10 insert bridges.',
 'change':'New inspection checklist explicitly supersedes old bridge instructions for the current revision and labels the yaw stack unresolved. Existing archives preserved.',
 'validation':'Part IDs and hardware compared against saved fourth-leg instructions and third-leg insert geometry. Links and assets checked by the handoff validator.',
 'limit':'User-reported spacer fit does not establish numeric screw engagement. No physical assembly outcome inferred.'}}
(ROOT/'audit.json').write_text(json.dumps(audit,indent=2))
from html.parser import HTMLParser
class Links(HTMLParser):
 def handle_starttag(self,tag,attrs):
  for k,v in attrs:
   if k in ('href','src') and not v.startswith(('http','#')):assert (ROOT/v).resolve().exists(),v
Links().feed(page)
assert len(parts)==10 and len(set(x[1] for x in parts))==10
print('PASS: saved checksums, archive contents, source hashes, ten part IDs and local links.')
