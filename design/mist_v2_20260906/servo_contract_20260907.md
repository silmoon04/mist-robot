# C018 dimensions and positioning-mode correction

The C018 manufacturer specification provides more usable information than the first draft retained. Its [local PDF](references/C018_manufacturer_spec.pdf) and [manufacturer source](https://cdn.robotshop.com/media/F/Fit/RB-Fit-155/pdf/feetech_12v_30kg_cm_magnetic_encoding_servo_sts321_specification_pdf.pdf) describe the A/0 variant. The physical units still need identification and measurement before these drawing dimensions become a fitted assembly.

## Travel is mode-dependent

Page 4 states that the mechanism has no rotation limit. Page 5 describes multi-loop absolute positioning up to plus/minus seven turns at the highest precision, and states that the turn count is not retained through power loss. It also lists the ordinary 0–360 degree position mode and closed/open-loop velocity modes.

The simulator's earlier plus/minus 175 degree shaft limits are therefore a deliberate **single-turn commissioning assumption**. They are not the C018's physical travel limit. The 350-degree shaft span permits 175 degrees of joint travel at 2:1, which cannot cover the entire requested 200-degree yaw span. At 3.5:1 it permits 100 degrees of hip travel. Each interval is centred on the calibrated assembled pose. These limits do not rule out higher reductions using a verified multi-turn mode.

A multi-turn candidate must include an unambiguous initial position and a way to recover after power loss, brownout or a controller restart. Its firmware/protocol behavior, actual range and homing method have not been tested here. Do not silently expand the current hardware limits or write the old bench's calibration into the new mechanism. Purely geometric collision limits also remain independent of the servo's supported mode.

The existing parameter file and saved runs retain their original limits. New expanded-travel experiments must use a separately identified parameter snapshot and state that the mode and startup recovery remain unverified.

## Drawing-controlled interfaces

The rendered [outline drawing](references/C018_page6.png) and [accessory drawing](references/C018_page7.png) were visually inspected on 7 September 2026. These agree with the older `fusion360/mist_c018_one_leg_fusion.py` constants:

| Interface | Drawing value |
|---|---:|
| Case footprint | 45.23 x 24.73 mm |
| Output axis from short end | 12.5 mm |
| Case centre offset from output axis along long dimension | 10.115 mm |
| Main axial references | 32 / 35 mm; see outline profile |
| Output-bearing-face to auxiliary-bearing-face span | 29 mm |
| Output and auxiliary projections | 3.4 / 4.1 mm |
| Overall projection span | 36.5 mm |
| Output spline | 25 teeth, nominal 5.9 mm OD |
| Centre retention screw | M3 x 6 |
| Supplied output horn | 19.95 mm OD, 4.5 mm total axial envelope |
| Main horn peripheral flange | 2.5 mm thick |
| Raised spline boss | 9 mm OD; 2 mm projection above the flange |
| Female spline recess / outer central opening | 3.6 mm depth / 3.2 mm through opening |
| Horn attachment | Four M3 holes on 14 mm bolt circle |

Do not place a 45.23 mm case symmetrically around its output axis. The old successful 25.23 mm cradle opening includes intentional clearance around the 24.73 mm case width. It is a prior physical fit result, not a new measurement of every unit. The supplied metal horn should carry the spline interface; a guessed printed spline is unnecessary.

The prior direct horn model uses 3.6 mm clearance holes at radius 7 mm and a 5.5 mm centre tool-access opening. Those are prototype CAD choices. They are not the drawing's M3 thread diameter. A small input gear may need a separate axially offset horn flange so the bolt holes do not cut through its tooth roots or collide with the mating gear.

The case has no ordinary projecting mounting ears. A real case clamp, positive axial location, cable clearance and accessible horn screws remain necessary. The older Rev-F notes explain how a cap that never contacted the case produced motion play; that defect must not be reintroduced by leaving a nominal saddle without its closing cap.

## Horn orientation and screw engagement

The main horn's raised boss faces the servo. The female 5.9 mm spline opens from that side; it cannot be installed over the servo shaft through the opposite 3.2 mm retaining-screw opening. The gear therefore contacts the flat outer flange face. A briefly proposed 9.2 mm rear pinion recess was based on reversing this orientation and has been removed from the current metal-gear specification.

The 4.5 mm dimension is the total horn envelope, not the available peripheral thread depth. The four M3 attachment screws pass into a 2.5 mm flange; an 8 mm gear with nominal M3 x 10 screws gives about 2 mm engagement before washers, tolerances and countersinks are considered. The central retaining screw and tool also need clearance. The mounted axial stack must seat the servo spline inside the 3.6 mm female recess rather than add the whole horn thickness above the shaft tip. Delivered-part seating and screw-head dimensions remain measurements for the first assembly.

The 20T printed pinion also has a separate attachment defect: its 3.6 mm clearance holes on the 14 mm circle leave only about 0.079 mm to the generated root outline. A wider face does not restore that radial material. See the [manufacturing review](package/proximal_review_20260907/review.md) and [metal-gear interface study](package/metal_gears_20260907/metal_gear_recommendation.md). The old static CAD export remains historical evidence, not a qualified horn stack.
