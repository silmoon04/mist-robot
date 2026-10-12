# MIST printing bootcamp - Neptune 4 Pro + 3kg PLA, zero experience

What to do with the printer *right now*, before the MIST parts arrive. Companion to `MIST_FIELD_GUIDE.md` (section 5 printing notes) and Phase 6 of `MIST_BUILD_PHASES.md`.

The goal by the time servos arrive: **(a)** you can drive the printer and you know its *measured* real-world tolerances, not guessed ones; **(b)** you can design a box with accurately-placed holes in CAD and print it so a screw fits on the first try. That is 90% of what MIST's printed parts actually are.

Treat this like the electronics phases: one change at a time, keep notes, small test pieces before big prints. A failed 20-minute coupon teaches the same lesson as a failed 9-hour leg, at 1/27th the cost.

## 0. Mindset and vocabulary

A 3D printer is a hot-glue robot with delusions of precision. Everything below is about learning where the delusion ends:

- **Slicer** — the compiler. Takes a 3D model (STL/STEP), emits G-code (the instruction stream). Nearly every print quality problem is fixed in the slicer, not CAD.
- **Layer height** — vertical resolution, typically 0.2mm. Lower = slower + prettier, and it changes almost nothing for MIST's mechanical parts.
- **Walls/perimeters** — the solid outline of each layer. Strength lives here. Mechanical parts want 3-4 walls, not more infill.
- **Infill** — the sparse lattice inside. 15% for cosmetic, 30-40% for mechanical. Diminishing returns above ~50%.
- **Supports** — sacrificial scaffolding under steep overhangs. Avoid *needing* them by design; they scar surfaces and waste time.
- **Brim** — a throwaway skirt around the first layer for adhesion. Cheap insurance on tall/thin parts.
- **First layer** — where 80% of failures happen. If layer one goes down clean, the print almost always finishes.

PLA specifically: the easiest material there is — low warp, forgiving, sharp detail. Its two real weaknesses are brittleness (snaps rather than bends, unlike PETG) and heat (goes soft ~55-60°C — sunny windowsill, car, or a warm servo). Perfect prototype material, wrong final-robot material. You have 3kg; the whole point of 3kg is to waste some learning.

## 1. Commissioning the printer (day 1)

1. Stable, level surface — not carpet, not a wobbly shelf. Printers shake.
2. Follow the manual's assembly/check steps. Specifically check: belts taut (they should twang, not flap), wheels/rails no wobble, nozzle tightened, bed plate seated on its magnet.
3. Run the printer's own **auto-level** routine from the touchscreen, then set **Z-offset** per the manual (the gap between nozzle and bed at zero — the single most important number on the machine).
4. Load PLA (~200-215°C nozzle, ~60°C bed), and print a model **from the included USB stick** first. A pre-sliced file validates the *machine* with your skills removed from the equation.
5. The Neptune 4 series runs Klipper and has a web control panel (Fluidd) reachable over your LAN — check the touchscreen network menu for the printer's IP and open it in a browser. As a programmer you'll live in this: file upload, temperature graphs, fine Z-offset nudges, print progress. If your firmware build doesn't expose it, USB stick + touchscreen works fine.

Safety, briefly: the nozzle is 200°C+ and the bed 60°C — same finger rules as the soldering iron. PLA fumes are mild but ventilate anyway. Stay near the printer for the whole first print and the first layer of every print after that. Keep the glass/PEI plate clean — wash with washing-up liquid and water when prints stop sticking; skin oils are the usual culprit.

**Gate: one clean pre-sliced print before installing a slicer.**

## 2. The slicer (day 1-2)

Install **OrcaSlicer** (free, open source) — it has a built-in Neptune 4 Pro profile and, crucially, a built-in **calibration menu** that generates most of the test prints in section 3 for you. The bundled Elegoo Cura also works if Orca feels overwhelming, but Orca's calibration tools are worth it.

Workflow: download a known-good STL (printables.com / thingiverse.com) → open in Orca → pick the Neptune 4 Pro profile + PLA 0.2mm preset → slice → look at the preview layer-by-layer (this is the compile output; learn to read it) → export/upload → print.

Print 2-3 fun things from the internet first. Seriously — a Benchy boat, a phone stand, whatever. It builds the loop (slice → print → inspect) with zero design risk, and the Benchy is itself a diagnostic (overhangs, bridging, stringing, small features).

**Gate: a Benchy you're not embarrassed by.**

## 3. Calibration ladder — measuring the real constraints (week 1)

Each of these is a purpose-built coupon that turns "3D printing has tolerances" into *numbers for your machine*. Run them in order; write the results in a note — those numbers feed straight into the MIST CAD. Orca's Calibration menu generates most of them.

| # | Test | What it teaches | Pass / output |
|---:|---|---|---|
| 1 | First-layer / Z-offset patch | The foundation skill. Too high = spaghetti, too low = scars and stuck prints. | Uniform lines, no gaps, no ripples. |
| 2 | Temperature tower | Your PLA's best nozzle temp (each spool differs a bit). | Pick the band with best surface + least stringing; note it. |
| 3 | Flow calibration | Over/under-extrusion — affects every dimension. | Orca guides this; note the flow %. |
| 4 | Retraction / stringing tower | The hairy-whiskers problem. | Minimal strings between towers; note retraction length. |
| 5 | Overhang test (steps 20°→70°) | THE design constraint: where your printer's unsupported overhang limit is. | Usually degrades ~50-60°. Note the angle where it gets ugly. |
| 6 | Bridging test | How far it can print across open air. | Note usable bridge length (often 20-40mm). |
| 7 | Clearance test (pegs into holes whose **hole-minus-peg diametral gaps** are 0.1/0.2/0.3/0.4 mm) | Which total diameter difference produces press, sliding, or free fits on this material/orientation. | Record both diametral gap and radial gap (= diametral/2); do not copy the number into a rectangular per-face pocket. |
| 8 | Hole-size coupon (vertical holes 2/2.5/3/4/5mm) | FDM holes print undersized. | Needs calipers (in the post) — defer measurement until they arrive; a M3 screw is a usable go/no-go gauge meanwhile. |
| 9 | Screw boss coupon | Self-tapper into a printed boss: how big the pilot hole, how thick the boss, does it split? | M2/M3 screws bite firmly without splitting the boss. |

Notes:

- Your calipers are in the AliExpress order and may not have arrived — tests 1-7 don't need them; test 8-9 measurements can wait or use actual screws as gauges.
- Change ONE setting between prints. Same rule as the harness: if two things changed, you're guessing, not debugging.
- Expected total filament for the whole ladder: well under 300g. That's what the 3kg is for.

**Gate: a written note with your machine's numbers — best temp, retraction, overhang limit, press-fit and free-fit clearance, hole compensation.**

## 4. CAD — yes, start modelling now (week 1-2, parallel with section 3)

Current recommendation (superseding the 2026-07-06 Onshape decision):
**Autodesk Fusion**, using a **Hybrid Design** in **Parametric Modeling Mode**.
The project now has a current parameter/axis authority and a complete beginner
workflow in [`MIST_FUSION_360_GUIDE.md`](MIST_FUSION_360_GUIDE.md). It was
checked against Fusion `v2704.1.23` on 2026-07-12.

Why the choice changed: MIST needs a top-down parameter skeleton, moving
components and joints, repeated leg occurrences, mass/CoM inspection, drawings,
and controlled 3MF/STEP export in one tool. A one-file Hybrid Design is the
simplest way for the first build to share parameters across internal components.
A later Part + Assembly split is cleaner for collaboration and reuse, but it
adds external-reference management. Onshape remains a valid alternative if
browser-only CAD is a hard requirement; the downside is that this repo's current
click paths, naming, parameter CSV, and validation guide are now Fusion-specific.

Programmer aside: code-CAD (OpenSCAD or build123d) is excellent for repeatable
coupon families and simple fixtures. Keep Fusion as the manufacturing and
assembly authority; use code-CAD when deterministic generation is the actual
advantage. Blender remains a mesh/aesthetic/render tool, not the source for
dimensioned printable interfaces.

The core loop to learn (it's the same in every CAD package): **sketch on a plane → constrain/dimension it → extrude into 3D → repeat on the new faces → fillet/chamfer edges**. Everything MIST needs is that loop plus a hole tool.

### Project ladder (each one printable, each one useful)

1. **Initial cube** — 20mm cube with your initials embossed. Teaches: sketch, dimension, extrude, text, printing something *you* made. (30 min in CAD.)
2. **Cable clips** — a C-clip sized to your desk cables, 5-minute print. Teaches: measuring a real object, clearance in practice, designing for print orientation (the clip must flex along layers, not across). Print five variants in one go and see which survives.
3. **Fastener coupon** — flat plate with a row of holes for M2/M3 screws and one slot. Teaches: the hole tool, your machine's hole-shrink numbers from test 8, parametric dimensions (make hole diameter a variable, change it once, everything updates — this will feel like home).
4. **ESP32 / OLED project box** — a real enclosure for hardware you already own: the ELEGOO ESP32-WROVER cam board, or a bezel/housing for the SH1106 OLED robot eyes. Teaches: measuring PCBs, standoffs/bosses, lid fits (use your measured press-fit clearance), cutouts for connectors. This is the graduation piece — it's exactly a mini version of MIST's electronics tray.
5. **STS3215 servo envelope and ear bracket — from the best available drawing before the servos arrive.** Model the 45.2 × 24.7 × 35 mm body as a placeholder, but keep ear pitch/thickness, output-axis location, auxiliary shaft, horn pattern, and both cable exits tagged **MEASURE**. When the servos arrive, Phase 6 becomes *measure, update, print coupon* rather than *start from zero*. Do not release a final bracket from the listing or AI art.
6. **Wheel-hub bolt-circle coupon** — a disc with the horn's screw pattern (also in the datasheet drawing). Teaches: circular patterns, and it's literally Phase 6's "horn/wheel bolt-pattern test piece".

Suggested pace: projects 1-3 in week 1 alongside the calibration ladder, 4-6 in week 2. By then you'll have real CAD mileage and the MIST-specific coupons drafted.

## 5. Design rules to internalize (the constraints CAD must respect)

These are why section 3's numbers matter — pin this list next to the CAD window:

- **The 45° rule**: faces overhanging more than ~45-55° from vertical droop without support. Design around it: chamfer under features instead of leaving them flat-bottomed, orient the part so overhangs disappear.
- **Layers are the grain.** Parts are strong along layers, weak between them (like wood). A screw boss loaded across layers splits; a clip flexing across layers snaps. Decide print orientation *while designing*, not after.
- **Holes print small** (by your measured amount, typically 0.2-0.4mm) and horizontal holes print as slight ovals — either add your compensation or drill/ream after.
- **Nothing thinner than 2 perimeters** (~1mm wall) survives handling. Bosses want 2.4mm+ of wall around the hole.
- **First-layer edges flare** slightly (elephant foot) — a 0.5mm chamfer on every bottom edge makes parts sit flat and look intentional.
- **Fillet inside corners** — sharp inside corners are crack starters in brittle PLA (and in PETG later).
- **Flat side down.** Every part wants one big flat face to print on. Design it in.
- **Clearance is a design input, not a hope**: use your measured press-fit and free-fit numbers from test 7. Never model two mating parts at identical dimensions.
- **Big single parts warp and fail expensively** — MIST's chassis should be modular/bolted anyway (it also survives redesigns better).

## 6. Print-failure playbook (the ones you will actually hit)

| Symptom | Cause, in order of likelihood | Fix |
|---|---|---|
| Nothing sticks / spaghetti at layer 1 | Z-offset too high; dirty plate; bed not at temp | Re-run Z-offset; wash plate with dish soap; 60°C bed for PLA |
| Print stuck to plate like it's welded | Z-offset too low (also causes shiny squished first layer) | Raise Z-offset a little; flex the plate to pop parts; never chisel |
| Whiskers/strings everywhere | Temp too high; retraction too low; damp filament | Re-check temp tower; retraction test; PLA can get damp too — dry storage |
| Corners lifting mid-print | Draughts; dirty plate; huge flat part | Close windows; wash plate; add brim; split the part |
| Layers shifted sideways partway up | Loose belt; something snagged; too fast | Check belt tension; check spool feeds freely; slow down |
| Surface turns rough/blobby mid-print | Wet filament; partial clog; overheating at low layer times | Dry filament; cold-pull/clean nozzle; add minimum layer time |
| A perfect print that's the wrong size | Slicer scale; hole shrink; measuring wrong | Model 20mm cube, print, measure — separates machine error from design error |

Same universal algorithm as the electronics: change one thing, retest the smallest print that proves the change, keep the note.

## 7. What NOT to do yet

- Don't print full legs or a chassis "to have them ready" — no CAD is validated against real servos yet, and PLA versions won't go on the robot anyway. Coupons and prototypes only.
- Don't chase perfection — a working clearance number beats a beautiful Benchy. Stop tuning when coupons pass.
- Don't tune five slicer settings at once. One change at a time.
- Don't print TPU or PETG settings knowledge from YouTube into muscle memory yet — learn vanilla PLA first; the others come with their own docs when the spools arrive.
- Don't leave long prints fully unattended in the early days, and never overnight on a printer you commissioned last week.

## 8. How this feeds the MIST phases

By the time the servo boxes arrive you'll have: a commissioned, calibrated printer with known numbers; working CAD skills; a drafted servo pocket and horn bolt-circle waiting for verification. Phase 6 ("CAD measurement and print coupons") collapses from *learn everything at once under time pressure* to *measure the real servo with calipers, adjust two sketch dimensions, reprint one coupon*. When PETG arrives: one temperature tower + reprint of the fastener and pocket coupons in PETG (per the field guide, PLA-tuned clearances transfer only approximately), and you're cleared to print real parts.
