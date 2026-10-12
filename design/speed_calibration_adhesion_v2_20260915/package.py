from pathlib import Path
import json, hashlib, zipfile, subprocess, sys
ROOT=Path(__file__).resolve().parent
old=ROOT.parent/'speed_calibration_20260915'
d=json.loads((ROOT/'test_design.json').read_text())
v=json.loads((ROOT/'VALIDATION.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert v['status']=='pass' and sha(ROOT/d['gcode_file'])==v['gcode_sha256']==d['gcode_sha256']
intro='''# Calibration V2: slower start and wider bases

Print EN4Pro_Calibration_V2_Slow_Start.gcode directly. Do not re-slice it.
Neptune 4 Pro, stock 0.4 mm nozzle, same PLA, 210 C nozzle and 60 C bed.

The earlier claimed 55-minute replacement was not generated. This file is the checked replacement.
Allow about 3.5 hours plus heating and homing, using approximately 37 g PLA.
The calculated motion estimates are 174 to 193 minutes; these are not measured printer times.

Each base extends 1 mm beyond its previous outline and now has four solid layers, 1.12 mm total.
These attached foundations stay on the calibration pieces. No supports are needed.

Layer | Extrusion speed | XY travel | Acceleration | Fan
1 | 12 mm/s | 40 mm/s | 250 mm/s2 | off
2 | 20 mm/s | 50 mm/s | 400 mm/s2 | off
3 | 25 mm/s | 60 mm/s | 500 mm/s2 | 25 percent
4 | 30 mm/s | 70 mm/s | 600 mm/s2 | 50 percent

Raised labels print at 20 mm/s and 500 mm/s2 with 60 mm/s travel.
The original six test bands then run at their original settings. This includes up to
10000 mm/s2 in the final acceleration band and 28 mm3/s in the final flow band.
Those later levels deliberately test the limits; the gentler base cannot guarantee they will succeed.

Wash and dry the build plate as planned. Check that the first-layer lines join and stay attached.
If they curl, separate or follow the nozzle, stop instead of letting the test continue.
Slower motion cannot correct an unsuitable Z offset, dirty surface or a loose part.
Stop if a piece detaches, the nozzle catches it or the extruder repeatedly skips.

Band heights have changed because the base is thicker. Use the included Band_Reference.png.
The front flow tower finishes first; the printer then lowers behind it to build the rear pieces.
That lowering is intentional, with the stock toolhead clearance checked.

The software checks verify commands and geometry, not physical adhesion or printer condition.
No file has been copied to USB and no printer commands have been sent.
'''
(ROOT/'START_HERE.txt').write_text(intro)
guide=(old/'READ_ME_FIRST.md').read_text()
import re
guide=re.sub(r'Approximately .*?These are calculated motion estimates, not measured printer times\.', 'Approximately 37 g PLA, 12.4 m filament. Motion estimates are 174 to 193 minutes before heating and homing. Allow about 3.5 hours plus startup. These are calculated estimates, not measured printer times.',guide)
guide=guide.replace('fan off on the first base layer','fan off on the first two base layers')
for prior,current in zip(json.loads((old/'test_design.json').read_text())['schedule'],d['schedule']):
    guide=guide.replace(f"| {prior['band']} | {prior['z_bottom_mm']:.2f} to {prior['z_top_mm']:.2f} mm",f"| {current['band']} | {current['z_bottom_mm']:.2f} to {current['z_top_mm']:.2f} mm")
guide=re.sub(r'Static validation passed: .*?This is code validation, not a completed physical print\.',f"Static validation passed: {v['parsed_move_count']} spatial moves and all 36 zone/band combinations, including the revised base limits. G-code SHA-256: {v['gcode_sha256']}. This is code validation, not a completed physical print.",guide)
for name in ('READ_ME_FIRST.md','READ_ME_FIRST.txt'):(ROOT/name).write_text(intro+'\n'+guide)
(ROOT/'RESULTS.csv').write_bytes((old/'RESULTS.csv').read_bytes())
checks=[ROOT/n for n in ('test_design.json','VALIDATION.json','READ_ME_FIRST.txt','START_HERE.txt')]
subprocess.run([sys.executable,'<LOCAL_HOME>/.codex/hooks/output_punctuation.py','register','--fix',*map(str,checks)],check=True)
subprocess.run([sys.executable,'<LOCAL_HOME>/.codex/hooks/output_punctuation.py','check',*map(str,checks)],check=True)
files=[ROOT/d['gcode_file'],*checks,*[ROOT/n for n in ('READ_ME_FIRST.md','RESULTS.csv','Print_Map.png','Toolpath_Preview.png','Band_Reference.png','generate.py','validate.py','render.py','package.py')]]
(ROOT/'SHA256SUMS.csv').write_text('file,sha256\n'+''.join(f'{p.name},{sha(p)}\n' for p in files))
files.append(ROOT/'SHA256SUMS.csv')
target=ROOT/'Neptune4Pro_Calibration_V2_Slow_Start.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files:z.write(p,p.name)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    for p in files:assert hashlib.sha256(z.read(p.name)).hexdigest()==sha(p)
print('READY',target)
