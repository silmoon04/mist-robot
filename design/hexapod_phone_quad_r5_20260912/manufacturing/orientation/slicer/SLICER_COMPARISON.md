# CuraEngine orientation comparison

Analysis only. All saved G-code commands are disabled. Do not send these files to a printer.

| Part | Orientation | Support angle | Time min | Model and support g | Support g | Support share |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| femur_main_and_knee_saddle | current | 50 | 172.4 | 30.83 | 3.58 | 11.6% |
| tibia_curved_main_and_foot | current | 50 | 132.6 | 22.59 | 2.94 | 13.0% |
| coxa_upper_and_hip_saddle | current | 50 | 156.8 | 29.31 | 3.33 | 11.3% |
| femur_main_and_knee_saddle | tilt45_about_long_axis | 50 | 154.8 | 27.19 | 0.32 | 1.2% |
| femur_main_and_knee_saddle | tilt45_support_angle40 | 40 | 258.2 | 41.54 | 14.54 | 35.0% |
| coxa_upper_and_hip_saddle | flip_x180 | 50 | 156.5 | 29.19 | 3.24 | 11.1% |

Settings: 0.4 mm nozzle, 0.20 mm layers, 0.42 mm lines, five walls, six top and bottom layers, 35% gyroid, 210/60 C PLA, 20 mm/s first layer, 35 mm/s outer walls, 60 mm/s inner walls, 80 mm/s infill. Supports are normal zigzag at 15%, with a 0.6 mm roof at 60%, 0.2 mm vertical separation, 0.5 mm XY separation and a 50 degree overhang angle. The nominal build envelope is 225 x 225 x 265 mm.

Source hashes and frozen numeric inputs are recorded in slice_manifest.json and resolved_settings.json. The comparison describes the source snapshots only; subsequent CAD revisions need new slicing.

Limitations:

- This is a frozen numeric engine profile, not the Cura GUI quality profile or a validated machine profile.
- Unused settings retain explicit Cura factory defaults. No frontend value expressions are evaluated.
- Time estimates are slicer predictions at the recorded conservative acceleration; hardware is unmeasured.
- Deposited mass uses 1.24 g/cm3 PLA density and excludes retraction-only moves, purging and startup.
- No adhesion brim is used around the model; support brims are enabled.
- Support volume is deposited filament, not the empty geometric support envelope.
- Slicing predicts support cost, not printed strength or support removability.

At the 50 degree support threshold, the 45 degree femur variant reduces deposited support by 90.9% and total deposited material by 11.8%. Its estimated time is 10.2% shorter. This is a candidate orientation, subject to load-direction review and an adhesion test: it has no model brim in this comparison.

The additional 40 degree threshold slice tests sensitivity: a 50 degree setting deliberately leaves nominal 45 degree planes unsupported. Their ability to print well still depends on cooling, bead overlap and the actual PLA. The long X axis remains parallel to the layer plane under the X rotation, but bracket surfaces change orientation and the small initial contact needs a physical adhesion check.

The coxa X180 flip changes support from about 3.33 g to 3.24 g and estimated time from 156.8 to 156.5 minutes. This small difference means plate contact and load direction should drive the orientation decision.
