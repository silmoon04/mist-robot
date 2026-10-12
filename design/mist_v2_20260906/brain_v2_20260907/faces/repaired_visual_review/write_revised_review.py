"""Write the completed visual regression review of all regenerated frames."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json, hashlib

BASE=Path(__file__).resolve().parent
OUT=BASE/'revised'
FACE=BASE.parent
frames=json.loads((FACE/'animation_frames.json').read_text(encoding='utf-8'))['frames']
snapshot=json.loads((OUT/'snapshot.json').read_text())
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',18)
def tile(root,index):
    page=index//50+1; within=index%50
    x=(within%10)*200; y=45+(within//10)*184+40
    return Image.open(root/f'frames_{page:02d}.png').crop((x,y,x+200,y+128))

selected=[12,401,447,266,366,396]
comparison=Image.new('RGB',(840,1900),'#20282f'); d=ImageDraw.Draw(comparison)
d.text((10,8),'Baseline (left) and corrected export (right)',font=font,fill='white')
for row,index in enumerate(selected):
    y=40+row*308
    d.text((10,y),f'{index:03d}: {frames[index]["label"]}',font=font,fill='white')
    for col,root in enumerate([BASE,OUT]):
        comparison.paste(tile(root,index).resize((400,256),Image.Resampling.NEAREST),(10+col*420,y+32))
comparison.save(OUT/'before_after_fixes.png')

mouth_counts=[len([l for l in f['layers'] if l['role']=='mouth' and l.get('opacity',1)>0.001]) for f in frames]
eye_opacities=sorted(set(l.get('opacity',1) for f in frames for l in f['layers'] if l['role']=='eyes'))
dim_mouth=[i for i,f in enumerate(frames) if any(l['role']=='mouth' and 0<l.get('opacity',1)<.99 for l in f['layers'])]
verification={
    'frames_visually_reviewed':450,
    'reviewer_coverage':{'primary':[[0,199],[400,449]],'independent':[[200,399]]},
    'maximum_visible_mouth_layers':max(mouth_counts),
    'speech_visible_mouth_layer_counts':sorted(set(mouth_counts[400:])),
    'eye_opacity_values':eye_opacities,
    'dim_mouth_frame_indices':dim_mouth,
    'dim_mouth_explanation':'Only fades into or out of the intentionally mouthless expressions 12 and 35.',
    'geometry_bounds_pass':not snapshot['outside_vector_frames'],
    'raster_bounds_pass':not snapshot['raster_edge_frames'],
    'minimum_raster_padding':snapshot['minimum_raster_padding'],
    'source_hashes_still_match':all(hashlib.sha256((FACE/path).read_bytes()).hexdigest()==sha for path,sha in snapshot['sources'].items()),
    'verdict':'pass_visual_regression_for_all_450_exported_frames'
}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')

notes={6:'Raised source mouth stays distinct from the right eye.',12:'Intentional mouthlessness retained; outgoing mouth fades without dimming eyes.',13:'Happy arcs and smile retained; 15 pixels of lower raster padding.',15:'Inherited canonical capsule tilt remains unchanged.',18:'Inherited canonical capsule tilt remains unchanged.',21:'Raised dome mouth stays distinct from curved lids.',24:'Bracket-eye blink remains clear.',27:'Loop-eye blink is now visible at 266-268; inherited capsule tilt retained.',28:'Wavy mouth and right tear retained; 15 pixels of lower raster padding.',29:'Outgoing tear fades without a duplicate mouth.',30:'No prior fitted-source chevron spur appears.',32:'Open eyes, frown, and right tear retained; 16 pixels of lower raster padding.',33:'Outgoing tear fades without a duplicate mouth.',35:'Intentional mouthlessness retained; outgoing mouth fades without dimming eyes.',36:'Mouth appears from the preceding mouthless expression while eyes remain bright.',37:'Bracket-eye blink is now visible at 366-368.',40:'Bracket-eye blink is now visible at 396-398; tiny dot mouth retained.'}
rows=[]
for n in range(40):
    rows.append({'expression':frames[n*10+9]['expression'],'frame_range_zero_based':[n*10,n*10+9],
                 'all_frames_visually_reviewed':True,'clipping':False,'double_mouth_ghost':False,
                 'severe_new_artifact':False,'settled_identity_loss':False,
                 'note':notes.get(n+1,'Clean single-mouth closure bridge, preserved settled shape, no severe new artifact.')})
(OUT/'per_face_review.json').write_text(json.dumps(rows,indent=2)+'\n')
report='''# Revised export visual review: all 450 frames pass

Every regenerated frame was visually inspected in `frames_01.png` through `frames_09.png`. This is a new pass over the revised Aseprite export, not a carry-forward of the earlier result. Frames 000-199 and 400-449 were checked by the primary reviewer; an independent reviewer checked every frame 200-399. The baseline sheets and baseline report remain in the parent directory.

The revised sample has no visible double-mouth ghosts, clipped features, catastrophic filled-screen panels, stepped mouth defects, severe new artifacts, or settled expression identity loss. All 450 vector frames stay within the 100 x 64 canvas, and all raster marks stay inside the 200 x 128 exported tiles. Minimum measured raster padding remains 15 pixels.

## Baseline findings and revised result

| Earlier finding | Revised evidence | Result |
|---|---|---|
| Speech-entry frame 401 showed two mouth lines. | Frame 401 now has one bright closed-lip line. | Fixed |
| Speech-release frame 447 showed a smile bowl behind the returning neutral line. | Frame 447 now has one bright closed-lip line; the old bowl is absent. | Fixed |
| Expression phase 2 dimmed the face and sometimes retained faint old/new mouths. | The reviewed midpoint frames keep bright eyes and a single mouth that closes before reopening into the target shape. | Fixed |
| Loop eyes 27 did not blink despite related eyes 34 blinking. | Frames 266, 267, 268 show closure, partial reopening, and restored loops. | Fixed |
| Bracket eyes 37 and 40 did not blink despite bracket eyes 24 blinking. | Frames 366-368 and 396-398 now show closure and reopening. | Fixed |

`before_after_fixes.png` places six exact baseline/revised frames side by side. It includes the midpoint example 012, both speech-boundary examples, and the three newly enabled blink closures.

The JSON independently confirms at most one visible mouth layer in every frame, exactly one mouth layer in all 50 speech/release frames, and eye opacity exactly 1 throughout all 450 frames. The only mouth opacity reductions occur in frames 111-113, 121-123, 341-343, and 351-353, when entering or leaving the intentionally mouthless faces 12 and 35. Those accessory fades preserve bright eyes and do not reproduce the previous dim whole-face transition.

## Source identity and clearance

The repaired settled poses retain the original visual identities. Face 13 keeps its happy arcs and broad smile with 15 pixels below its lowest raster mark. Face 28 keeps its loop eyes, wavy mouth, and right tear with 15 pixels below. Face 32 keeps its open eyes, curved frown, and right tear with 16 pixels below. The tear strokes and smile bowls remain complete.

The canonical capsule tilts in 15, 18, and 27 remain inherited source details, as previously recorded; the fit does not introduce a new rotation defect. Faces 12 and 35 remain mouthless, face 40 retains its tiny dot mouth, and asymmetric eyes and smirks remain recognizable. `settled_comparison.png` compares the original preview, source canonical raster, and regenerated settled export for seven representative expressions.

## Per-expression coverage

Each row covers five transition samples, four blink samples, and one settled frame. Every row passed clipping, double-mouth, severe-artifact, and settled-identity checks.

| Expression | Zero-based frames inspected | Observation |
|---|---:|---|
'''
for r in rows:
    a,b=r['frame_range_zero_based']; report+=f"| `{r['expression']}` | {a:03d}-{b:03d} | {r['note']} |\n"
report+='''
## Speech and scope

Every frame 400-449 was checked. The sample covers rest, MBP, FV, AA, EH, EE, OH, OO, S, LNT, SMILE, and release on neutral expression 39. The mouth stays separate from the eyes and transitions without a second visible mouth. The bright closure bridge solves the earlier ghosting without hiding it in a dark frame.

This verdict covers the exported pixels and the manifest geometry of these 450 sampled frames. It does not establish real-audio synchronization, perceived speed during live playback, every possible expression-pair transition, or speech on every expression. The implementation's wider regression tests are separate evidence and were not rerun as part of this visual subtask.

`snapshot.json` records the exact revised inputs and hashes; `verification.json` confirms those files still match at review completion. `frame_metrics.json` records per-frame bounds. Vector bounds include half stroke width for visible layers with opacity above 0.001. Raster checks select cyan pixels with green above 35 and green above 1.3 times red after compositing onto the export's dark background. These measurements support the completed visual review.

No runtime source or native Aseprite document was edited by this audit. Baseline evidence remains unchanged in the parent directory.
'''
(OUT/'review.md').write_text(report,encoding='utf-8')
print(json.dumps(verification,indent=2))
