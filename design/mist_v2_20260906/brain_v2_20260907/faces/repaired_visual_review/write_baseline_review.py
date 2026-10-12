"""Record the first complete visual pass before transition corrections."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json

OUT=Path(__file__).resolve().parent
FACE=OUT.parent
animation=json.loads((FACE/'animation_frames.json').read_text(encoding='utf-8'))['frames']
meta=json.loads((FACE/'aseprite_check'/'aseprite_frames.json').read_text(encoding='utf-8'))['frames']
source=Image.open(FACE/'aseprite_check'/'aseprite_frames.png').convert('RGBA')
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',18)
preview=Image.new('RGB',(1500,730),'#20282f'); d=ImageDraw.Draw(preview)
for j,i in enumerate([400,401,402,446,447,448]):
    r=meta[i]['frame']; crop=source.crop((r['x'],r['y'],r['x']+r['w'],r['y']+r['h']))
    bg=Image.new('RGBA',crop.size,'#07090c'); bg.alpha_composite(crop)
    x=(j%3)*500; y=(j//3)*360
    d.text((x+10,y+10),f'{i:03d}: {animation[i]["label"]}',fill='white',font=font)
    preview.paste(bg.convert('RGB').resize((500,320),Image.Resampling.NEAREST),(x,y+40))
preview.save(OUT/'baseline_speech_boundary_closeups.png')

notes={6:'Raised source mouth stays separate from right eye.',12:'Intentional mouthlessness preserved.',13:'Original happy arc/smile identity retained; new bottom padding is 15 pixels.',15:'Pre-existing canonical capsule tilt retained.',18:'Pre-existing canonical capsule tilt retained.',21:'Raised dome mouth and lids remain separate.',24:'Bracket eyes close and reopen visibly.',27:'Pre-existing canonical capsule tilt retained; no visible blink despite related loop-eye face 34 blinking.',28:'Wavy mouth and right tear preserved; new bottom padding is 15 pixels.',29:'Preceding tear disappears; raised wavy mouth stays distinct.',30:'No fitted-source chevron spur appears in the new canonical export.',32:'Curved frown and right tear preserved; new bottom padding is 16 pixels.',33:'Preceding tear disappears; asymmetric eyes preserved.',35:'Intentional mouthlessness preserved.',37:'Bracket eyes show no visible blink, unlike related bracket face 24.',40:'Tiny mouth retained; bracket eyes show no visible blink, unlike related bracket face 24.'}
rows=[]
for i in range(40):
    rows.append({'expression':animation[i*10+9]['expression'],'frame_range_zero_based':[i*10,i*10+9],
                 'every_frame_visually_reviewed':True,'clipping_observed':False,'settled_identity_loss_observed':False,
                 'baseline_transition_issue':'Phase 2 dims the face and can retain faint old/new mouth contours.',
                 'specific_note':notes.get(i+1,'Settled shape and sampled blink phases preserve source identity.')})
(OUT/'baseline_per_face_review.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
text='''# First complete review of the 450-frame repaired face export

This is the baseline visual review before the subsequent mouth-transition correction. The exact input hashes are in `snapshot.json`; the nine contact sheets preserve those pixels even if the source files are regenerated later.

Every exported frame was visually reviewed: 200 expression-transition samples, 160 blink samples, 40 settled expressions, and 50 neutral-face speech/release samples. The review split at frame 200: one reviewer checked 000-199 and 400-449, while an independent reviewer checked 200-399. Both found the same transition brightness issue.

All 450 frames pass static vector bounds, and no measured cyan mark reaches a raster edge. The minimum raster padding is 15 pixels in the 200 x 128 export. No clipped tear, solid-cyan failure, new fitted-source join spur, stepped mouth, or settled expression identity loss was visible. This pass does not certify all expression-pair transitions or speech on all 40 faces; the sample contains the ordered expression sequence and speech on neutral face 39.

## Issues found

1. **Speech entry and release briefly show two mouths.** Frame 401 contains the old neutral line above the incoming speech-rest line. Frame 447 contains the outgoing smile bowl behind the incoming neutral line. The latter is plainly visible. `baseline_speech_boundary_closeups.png` shows both with their immediate neighbors.
2. **Expression transitions have a conspicuous dark midpoint.** Transition phase 2 dims the eyes and mouths. At frame 012, for example, eye opacity is about 0.232 and each outgoing/incoming mouth opacity is about 0.052. Several midpoints retain faint overlapping old/new mouths. This prevents bright geometric distortion but produces a visible dark beat and double contours in still frames. It appeared throughout the 40-expression sequence.
3. **Similar eye forms have inconsistent blink eligibility.** Face 27's loop eyes do not visibly blink, while face 34's do. Faces 37 and 40's bracket eyes do not visibly blink, while face 24's do. The manifest confirms different `open` flags: face 27 has `e_shape_13`/`e_shape_12` marked false, face 34's `e_shape_12` is true, faces 37/40 use `open_C_44` false, and face 24 uses `open_C_51`/`open_C_45` true. This is a motion-policy inconsistency, separate from visual geometry.

The first two findings were sent to the implementation owner before this report was written. A single closure bridge was proposed for the next export; this baseline does not claim that change is already verified. The blink observation was also sent for a deliberate eligibility decision.

## Repaired settled poses

Face 13 retains its happy arcs and broad smile while gaining 15 pixels of bottom padding. Face 28 preserves its loop eyes, wavy mouth, and right tear with 15 pixels below the lowest mark. Face 32 preserves its open eyes, curved frown, and right tear with 16 pixels below. No tear or smile was truncated to achieve the fit.

Faces 15, 18, and 27 retain the capsule tilts previously identified in the canonical source audit; those are inherited source choices. Faces 12 and 35 remain intentionally mouthless. The new export uses flat cyan art and antialiased pixels, so absence of the source raster's neon glow is a style difference and was not counted as lost geometry. Enlarged nearest-neighbor pixels in the comparison sheet are an inspection aid.

`settled_comparison.png` places original previews, prior canonical renders, and new settled export frames together for faces 13, 28, 32, 15, 18, 27, and 39.

## Per-expression coverage

All rows passed clipping and settled-identity checks. The common transition midpoint issue applies to the sequence as described above.

| Expression | Zero-based frames inspected | Specific observation |
|---|---:|---|
'''
for r in rows:
    a,b=r['frame_range_zero_based']; text+=f"| `{r['expression']}` | {a:03d}-{b:03d} | {r['specific_note']} |\n"
text+='''
## Speech coverage and measurement limits

Frames 400-449 cover rest, MBP, FV, AA, EH, EE, OH, OO, S, LNT, SMILE, and release. The mouth remains below the eyes and the source eye geometry stays recognizable. In addition to the boundary ghosts above, the still sequence does not establish timing against real audio or whether neighboring visemes look sufficiently different in motion.

`frame_metrics.json` records every label, visible layer count, vector bounds, raster cyan bounds, and padding. Vector bounds include half the stroke width for visible layers with opacity above 0.001. Raster checks identify pixels with green above 35 and green above 1.3 times red, after compositing the exported tile onto its dark background. The bounds check excludes no bright facial geometry, but is not a substitute for the completed visual inspection.

No runtime code or native Aseprite document was edited during this review.
'''
(OUT/'baseline_review.md').write_text(text,encoding='utf-8')
print('Baseline visual review and speech closeups saved.')
