# MIST print test kit (v2)

Regenerated 2026-07-08 (v2.2). Calibration coupons, servo/horn/wheel fit tests, hinge mechanism experiments, adjustable femur/tibia beams, and optional component envelopes for PLA testing on the Neptune 4 Pro.

> **2026-07-12 compatibility notice:** the current Fusion baseline is femur
> 110 mm, tibia 70 mm, and wheel Ø70 mm. This kit's documented 65/85 mm beam
> baseline and Ø76 wheel slice are legacy experiments. The tibia beam only
> samples 75–120 mm, so it cannot validate the current 70 mm tibia. Use the
> clearance/servo/hole/cable coupons where their interface still matches, and
> regenerate geometry from the [Fusion guide](MIST_FUSION_360_GUIDE.md) before
> treating a leg or wheel coupon as current.

Scripts referenced by the original generation notes (not present in this
workspace as of 2026-07-12):

- `mist_3d/tools/build_print_test_kit.py`
- `mist_3d/tools/slice_neptune4pro_cura.py`

Generated/sliced output that is present in this repo:

- `mist_3d/MIST_print_tests/stl/`
- `mist_3d/MIST_print_tests/plates/`
- `mist_3d/MIST_print_tests/gcode/`
- `mist_3d/MIST_print_tests/slice_report.csv`

The old regeneration command is retained only as provenance. It will not work
until the missing scripts are restored:

```powershell
$env:MIST_PRINT_TEST_KIT_OUT='<LOCAL_HOME>\Downloads\MIST_print_tests'
python -B mist_3d\tools\build_print_test_kit.py
python -B mist_3d\tools\slice_neptune4pro_cura.py
```

## What changed in v2 (fixes over the first kit)

| v1 problem | v2 fix |
|---|---|
| Knuckle hinge halves were not coaxial (could never assemble) | Rebuilt: coaxial two-piece knuckle, M3 pin, ~±45° travel |
| Four-bar "pair" was fused into one rigid piece | Two separate bodies |
| Clevis had nothing to pivot in it | Matching 6mm tongue link included, 7mm gap + washers |
| Flexure leaves printed as a 44mm mid-air bridge | Leaves sit on the bed |
| 2:22h servo "pocket" was only 14mm deep (fake ear seat) and baked in a guessed clearance | Two 6mm ear-hang bracket plates (0.3 / 0.5mm), ~47min each, real mounting style |
| Clearance-test pegs were fused to the plate | Three separate handled pegs |
| No wheel test despite 4 wheel-mode servos | 76mm wheel-slice coupon with horn recess + slotted bolt circle |
| Femur beam could not hit the then-current 65mm concept baseline (10mm hole grid from 60) | Staggered rows give 5mm resolution on both beams; both are now legacy relative to 110/70 |
| No labels on any coupon | Debossed 7-segment labels (values are mm x10, e.g. `34` = 3.4mm) |
| Only walls were slowed; infill/skin/first layer ran at N4P profile defaults | All speeds capped (print 80, infill 100, skin 40, first layer 25) |
| Brim on everything | Skirt for coupons, brim only for tall dummy shells |
| Time estimator ignored acceleration | Trapezoidal accel model with junction slowdowns (expect ±15%) |

## Slicer profile

CuraEngine 5.13 CLI with the built-in `elegoo_neptune_4pro.def.json`. Final G-code is post-processed and bounds-checked against a 225 x 225mm bed with a 5mm safety margin.

| Setting | Value |
|---|---:|
| Layer height | 0.20mm (first 0.24) |
| Nozzle / bed | 210C / 60C |
| Fan | 0% through layers 0-3, 100% from layer 4 |
| Outer/inner wall speed | 35mm/s, first layer walls 20mm/s |
| Print / infill / skin / first layer | 80 / 100 / 40 / 20mm/s |
| First two layers | all G0/G1 feedrates capped at F1200 (20mm/s) after slicing |
| Small feature factor | 70–75% |
| Flow | 98% (first layer 100%) |
| Retraction | 0.8mm at 40mm/s (printer profile caps E-speed at 25mm/s) |
| Supports | OFF except `fit_wheel_slice_76`, `dummy_sts3215_solid`, `plate_2_servo_fit` (tree, build-plate only, 45° max lean) |
| Walls / infill | 3 / 15% (dummies 2 / 10%) |
| Adhesion | 1-line skirt, 2mm gap (dummy plates: 2mm brim) |

Note: CuraEngine's CLI writes placeholder headers (`;TIME:6666`, `Filament used: 0m`), so times below come from an acceleration-aware G-code simulation. Treat as ±15%.

**Bed placement (fixed 2026-07-08):** CuraEngine CLI adds the bed-center offset itself, so STLs must be exported centered on the origin. Early G-code (and all of GPT's v1 G-code) was shifted +112.5mm into the back-right corner - wide plates ran off the bed. STLs are now origin-centered, `center_object=true` is set, expression placeholders like `{machine_depth - 5}` are substituted, and every sliced file is recentered only if its final G-code envelope fits within X/Y 5..220mm. If a preview shows a part off the plate, do not print it. The original scripts are absent; restore them from a known source or reslice the checked STL in a trusted current profile and regenerate the report. Supports are also now off by default: with them globally on, Cura grew trees for 3.4mm pin holes and the trees leaned past the plate edge.

**Locked file fallback:** if CrealityPrint or another previewer has a canonical `.gcode` file open, the slicer writes a `.FRESH.gcode` replacement instead of leaving stale output. The current v2.2 reslice wrote canonical names directly; no `.FRESH.gcode` files are needed.

## Print order

1. **`plate_1_calibration`** — everything else depends on knowing your printer's hole shrink and screw-boss behavior. Nothing here needs hardware.
2. Measure plate 1: which hole prints to true M2/M2.5/M3 tap and clearance size, which boss pilots split, which peg clearance slides.
3. **`plate_2_servo_fit`** — brackets, horn disc, wheel slice, solid servo dummy. If plate 1 shows a different process correction, create/revise the affected coupon in the current Fusion model; the missing generator cannot be rerun here. Ideally print this after the first real STS3215 arrives; the dummy stands in until then.
4. **`plate_3_hinges_linkages`** — needs M3 bolts, nuts, washers on hand.
5. **`plate_4_leg_geometry`** — femur/tibia beams + pose board. If you want to skip the 3h pose board, print `link_femur_adjustable` + `link_tibia_adjustable` individually (~1h each) and pin them to cardboard instead.
6. **`plate_7_second_leg`** — second femur + tibia + clevis, plus the four-bar coupler/ground links. It is packed into narrower rows in v2.1 so the final toolpath keeps the same 5mm bed margin. Print when you move from "one joint feels right" to assembling a leg chain or two-leg stance test.
7. **Plates 5–6 (dummies) are optional.** Print the LiPo envelope if you want a strap/tray mockup; use the real phone, and cardboard boxes are fine for the small boards.

## How many of each?

Measurement coupons are one-offs — a second copy measures nothing new. Multiples only matter for parts you assemble:

| Part | Total qty | Why |
|---|---:|---|
| all `cal_*` coupons | 1 | printer measurement, one-off |
| `fit_servo_bracket` | 1 of each clearance | pick the winner, reprint the winner if you need more mounts |
| `fit_horn_disc`, `fit_wheel_slice_76` | 1 | interface check; reprint after locking the measured bolt circle |
| `dummy_sts3215_solid` | 2–4 | 2 for bay layout; 4 to mock one full leg corner (3 DOF + wheel) |
| `hinge_clevis_tongue` | 2 | a 2-DOF leg chain needs hip + knee pivots |
| `link_femur/tibia_adjustable` | 2 each | two-leg stance / diagonal-support pose tests |
| `link_fourbar_pair` + `link_coupler_pair` | 1 each | 2 long bars + coupler + ground = a complete four-bar (or use the pose grid as ground) |
| `hinge_knuckle_m3`, flexure, rocker, horn lug | 1 | feel/comparison coupons |
| LiPo dummy | 1 | one pack rides the robot |

Plates 3+4 give one of each; plate 7 completes the pairs. Reuse an existing
G-code file only after confirming the exact printer, nozzle, material and
profile assumptions; preview every layer/toolpath, verify bed bounds and a
known dimension, and reslice if anything differs. A filename is not a safety
certificate.

## Combined plates

| G-code | Contents | Size (mm) | Est. time | PLA |
|---|---|---:|---:|---:|
| `plate_1_calibration.gcode` | hole sizes, screw bosses, clearance+pegs, cable tunnels | 171.5 x 154.0 x 12 | 4:23 | 53.9g |
| `plate_2_servo_fit.gcode` | 2 brackets, horn disc, wheel slice, servo dummy | 192.0 x 130.0 x 39 | 5:01 | 74.4g |
| `plate_3_hinges_linkages.gcode` | horn lug, clevis+tongue, knuckle, flexure, rocker, four-bar | 182.9 x 194.9 x 20 | 3:41 | 45.4g |
| `plate_4_leg_geometry.gcode` | femur beam, tibia beam, pose board | 150.0 x 154.0 x 5 | 5:22 | 64.0g |
| `plate_7_second_leg.gcode` | 2nd femur, 2nd tibia, 2nd clevis+tongue, coupler pair | 144.0 x 108.0 x 20 | 3:26 | 43.3g |
| `plate_5_dummies_power.gcode` (optional) | LiPo (HOOVO 2200), XT90-S, UBEC, PDB | 184.0 x 89.5 x 24.5 | 3:32 | 32.2g |
| `plate_6_dummies_boards.gcode` (optional) | phone, ESP32, servo adapter | 147.5 x 113.5 x 13 | 2:52 | 28.0g |

Core kit (plates 1-4): ~18.5h, ~238g. With plate 7: ~22h, ~281g. Everything: ~28.3h, ~341g.

## Verified G-code bounds

These are final toolpath bounds, not raw STL dimensions. Every verified file stays inside X/Y 5..220mm on the 225 x 225mm Neptune 4 Pro plate.

| G-code | Final XY bounds | Margin |
|---|---:|---:|
| `plate_1_calibration.gcode` | X12.28..212.72 Y5.00..220.00 | 5.00mm |
| `plate_2_servo_fit.gcode` | X7.15..217.85 Y5.00..220.00 | 5.00mm |
| `plate_3_hinges_linkages.gcode` | X9.43..215.57 Y5.00..220.00 | 5.00mm |
| `plate_4_leg_geometry.gcode` | X17.65..207.35 Y5.00..220.00 | 5.00mm |
| `plate_7_second_leg.gcode` | X19.15..205.85 Y5.00..220.00 | 5.00mm |
| `plate_5_dummies_power.gcode` | X6.30..218.70 Y5.00..220.00 | 5.00mm |
| `plate_6_dummies_boards.gcode` | X15.43..209.57 Y5.00..220.00 | 5.00mm |

## Individual prints

| G-code | Est. time | PLA | Notes |
|---|---:|---:|---|
| `cal_hole_sizes` | 1:03 | 12.7g | labels = diameter x10 (`18`...`34`) |
| `cal_screw_boss` | 1:15 | 14.5g | pilot 1.6-2.8mm |
| `cal_clearance_pegs` | 1:13 | 14.8g | hole-minus-5 mm-pin **diametral** gaps 0.1–0.6 mm; 3 loose pegs |
| `cal_cable_tunnels` | 0:55 | 12.3g | 4/6/8/10mm channels |
| `fit_servo_bracket_c03` / `_c05` | 0:48 each | 9.8g / 9.7g | ear-hang mount, historically labelled 0.3/0.5 mm body clearance; measure the mesh/coupon and state per-side versus total before transferring a value |
| `fit_horn_disc` | 0:16 | 3.1g | horn recess + slotted bolt circle |
| `fit_wheel_slice_76` | 1:38 | 21.0g | wheel-mode mounting/wobble test; support verified |
| `dummy_sts3215_solid` | 1:37 | 30.1g | print 2 if you want a pair for layout; support verified |
| `hinge_horn_lug` | 0:25 | 4.8g | single-shear reference |
| `hinge_clevis_tongue` | 0:46 | 10.4g | best first hinge; M3 + 2 washers |
| `hinge_knuckle_m3` | 0:48 | 10.7g | slide together sideways, then pin; free ±90° |
| `hinge_flexure_leaves` | 0:24 | 4.7g | comparison only |
| `link_rocker` | 0:28 | 4.9g | mounts on a real horn |
| `link_fourbar_pair` | 0:56 | 10.6g | two separate bars, holes 45-95mm |
| `link_coupler_pair` | 0:40 | 7.5g | short coupler + ground links, holes 20-60mm |
| `link_femur_adjustable` | 1:01 | 12.5g | 60-110mm in 5mm steps |
| `link_tibia_adjustable` | 1:03 | 13.3g | 75-120mm in 5mm steps |
| `jig_pose_grid` | 3:21 | 38.5g | optional; cardboard works |
| `dummy_lipo_hoovo_2200` | 1:32 | 15.0g | optional battery envelope |
| `dummy_xt90s_loop` | 0:52 | 7.2g | optional power-loop envelope |
| `dummy_ubec_5v5a` | 0:18 | 2.7g | optional UBEC envelope |
| `dummy_xt60_xt30_pdb` | 0:49 | 6.9g | optional PDB envelope |
| `dummy_phone_mi9se` | 1:49 | 18.7g | optional; real phone is better for layout |
| `dummy_esp32_devkit` | 0:35 | 5.1g | optional board envelope |
| `dummy_bus_servo_adapter` | 0:30 | 4.3g | optional adapter envelope |

## Using the beams

Labels every 20mm on the centerline; the row next to the labels' near edge is the 10mm grid, the far row is offset +5mm. Length = pivot hole to chosen hole (axis-to-axis, not plastic end-to-end). The historical sequence was 65/85, 75/85, 65/95, 80/100; none is the current 110/70 CAD baseline, and the tibia ladder cannot reach 70 mm. Use these parts only for qualitative geometry lessons. Keep any loaded test inside its documented fixture limits.

## Caliper-check list (unconfirmed dimensions)

Nominal listing records: body 45.2 x 24.7 x 35mm, 25T/OD5.9 spline, M3x6 output screw. Measure the delivered lot before mating geometry. The old text referenced constants in `build_print_test_kit.py`, but that script is absent; record measured values in the Fusion parameter table and rebuild the affected coupon:

- Ear extension per end (5.9mm assumed) and ear underside height (26.5mm assumed)
- Ear hole pitch (17mm assumed) — bracket holes are 2.6mm, drill to fit
- Shaft axis position from body end (11.3mm assumed)
- Horn diameter 21mm / thickness 3.4mm — recess printed at 21.3mm
- Horn screw bolt circle — printed as radial slots covering 12–16mm; measure the real horn, then lock the value in
- HOOVO 3S 2200 pack — envelope is 104 x 34.5 x 24.5 (`dummy_lipo_hoovo_2200`); measure the real pack before finalizing the battery tray, and leave the tray adjustable — the basket notes a bigger (~5200mAh) pack as a later wheeling upgrade

## Sources

- STS3215/ST3215 body + spline + output screw: Feetech listing (`feetechrc.com/525603.html`), DFRobot ST3215 30kg page
- HOOVO 3S 2200: dims from the order listing (104 x 34.5 x 24.5, ~180g); the basket doc's Overlander 3350 default was not what was ordered
- Neptune 4 Pro bed: Cura 5.13 `elegoo_neptune_4pro.def.json` (225 x 225 x 265)

## Notes

- These are PLA test parts. Redo the servo bracket, horn disc, and wheel in PETG before trusting load-bearing parts (PETG order is in the post).
- If a plate part fails mid-print, print its individual STL instead of restarting the whole plate.
- **G-code post-processing (added after the adversarial audit 2026-07-08):** raw CuraEngine CLI output contains unresolved `{placeholder}` temperatures in the Elegoo start/end G-code (frontend-only substitution) - Klipper aborts on them. `slice_neptune4pro_cura.py` now substitutes them, enforces fan 0% on layers 0-3 / 100% from layer 4 exactly, caps all G0/G1 feedrates to F1200 for layers 0-1, verifies support toolpaths for support-required files, and strips stray cold-temperature commands CuraEngine emits mid-print. Never print raw un-post-processed CuraEngine CLI output on this machine.
- The staggered beam rows put holes 5.5mm off the pivot centerline, so stagger-row lengths run ~0.13–0.25mm long — irrelevant for leg-feel testing.
- First layer and second layer G0/G1 feedrates are capped at F1200 (20mm/s). Normal walls resume after that, with the fan turning on at layer 4.
