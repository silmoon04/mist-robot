# Metal gears for the existing MIST reductions

Use **HPC PG1-25 and PG1-50 as the dimensional starting point for the new knee stage**. Their plain steel bodies are 8 mm thick, matching the current gear slice. Both require specified machining. Preserve the 37.5 mm centres and 2:1 ratio; no change to the robot architecture is proposed. No purchase or external quotation request was made.

The **20:40 yaw/hip stages still need a designed horn adapter**. Substituting steel does not make the existing four-hole pattern fit a 20-tooth root. No verified stock gear/adapter combination closes that interface within the present 8 mm slice.

## Actual parts and prices

| Family | Relevant dimensions | Price and availability evidence | Fit assessment |
| --- | --- | --- | --- |
| HPC PG1-20/25/40/50 | 8 mm face and overall width; OD22/27/42/52; stock H8 bores8/8/8/10 | Catalogue GBP 11.33/12.40/14.96/16.44 each; live price and stock unverified | Closest to the present axial slice. Robot holes, locating features and smaller output bores are modifications. |
| Ondrives PSG1.0-20/25/40/50 | 10 mm face,22 mm overall; stock H7 bores5/6/10/10 | No public UK price or stock verified | 817M40T steel option, but it needs width machining or a layout change. |
| RAR/KHK SS1-20/25/40/50 | 10 mm face,20 mm overall; stock H7 bores8/8/10/10 | GBP 10.73/10.97/14.13/17.91 as displayed;25T had 8 in stock,50T had 1; VAT basis unspecified | Available UK 25:50 route, but larger axial envelope. |

The [supplier comparison](supplier_gear_options.md) links exact product pages and drawings. HPC's [official catalogue](https://www.hpcgears.com/pdf_c33/23.28-23.33.pdf) was downloaded and its standard-family drawing inspected. PG is the hubless 8 mm form; G adds a 12 mm hub for 20 mm total. The standard material is 214M15/045M10 steel, module 1,20 degree pressure angle. The 25:50 PG pair totals 142 g before machining and attachments, materially more than a lightweight printed/aluminium pair.

Do not quote a gear tooth rating for the modified assembly from these dimensions. HPC's catalogue check is for a 50T gear at 1000 rpm, with correction information elsewhere. It is not an unconditional rating for this reversing servo mechanism. Machining, heat treatment, tooth quality, backlash and lubrication require a finished specification.

## Horn geometry changes the machining requirement

A fresh visual check of the [Feetech accessory drawing](../../references/C018_page7.png) establishes **4.5 mm overall horn thickness, but only 2.5 mm at the peripheral four M3 threads**. A **diameter 9 mm central boss projects 2 mm above that flange on the servo-facing side**. The four threaded holes are on 14 mm BCD. [Manufacturer specification](https://cdn.robotshop.com/media/F/Fit/RB-Fit-155/pdf/feetech_12v_30kg_cm_magnetic_encoding_servo_sts321_specification_pdf.pdf).

The section shows the diameter 5.9 spline opening on the raised-boss side and only diameter 3.2 screw clearance through the opposite face. The boss therefore faces the servo; the gear mounts against the opposite flat face. **No diameter 9 mm boss recess is required in the pinion from this drawing.** The stock 8 mm gear bore must clear the actual central retaining-screw head and its tool. The casing-to-horn-flat-face distance still depends on the fitted horn's axial stop and is not established by the accessory thickness alone.

The proposed PG1-25 machining is four **3.4 mm clearance holes on 14 mm BCD**, with a concentric locating/registration method specified from the actual horn. These are quotation and fit-test dimensions, not existing features in the catalogue gear. An ordinary clearance-hole pattern does not by itself promise repeatable concentricity.

Use ordinary M3 heads beyond the gear face in the initial design. An M3Ãƒâ€”10 through an 8 mm gear gives 2 mm nominal horn engagement. The horn's nominal 2.5 mm flange does not support an assumed 3-4 mm thread engagement. Verify useful thread depth, chamfers, screw-tip protrusion and rear clearance before fixing screw length. Retain the factory horn for its supplied spline; do not infer a machinable spline from 25 teeth and 5.9 mm OD alone.

For a standard unshifted root-circle screen, `root diameter = module*(teeth-2.5)`. Four 3.4 mm holes on 14 mm BCD leave **0.05 mm radial ligament at 20T**, versus **2.55 mm at 25T**. These numbers require the supplier's actual fillet/root contour and local stress check; they do not constitute a machining release.

For the retained 20T yaw/hip pinion, use a separate metal flange that bolts to the factory horn and drives a concentric keyed or pinned stub, with the gear on that stub. A supplier-engineered flanged pinion is another route. Both need a real drawing, shaft retention, screw access and an accepted axial envelope. The current task did not establish a stock adapter that fits the present packaging, so CAD should retain that interface as an explicit unresolved item.

## Knee output connection

PG1-50 occupies **y28.125..36.125 mm** unchanged. Prefer a factory **7 mm finished bore** for the input rotor shaft, or a designed **flush10 OD/7 ID/8 mm long centring bush** in the stock 10 mm bore. The bush centres the gear; it does not supply the torque connection.

Machine four M4 clearance holes on 16 mm PCD to match the proposed MISUMI A-pulley face pattern. Ordinary M4Ãƒâ€”14 screws through the 8 mm metal gear give 6 mm nominal engagement into the pulley's 8 mm nominal tapped depth. The metal gear should replace the printed carrier and its compression-sleeve arrangement here, rather than automatically retaining oversized 6.6 mm sleeve holes. With 4.5 mm clearance holes, the stock 10 mm bore leaves 0.75 mm inward ligament; a 7 mm finished bore leaves 2.25 mm.

For a positive low-play connection beyond face friction, a checkable custom proposal is **two 3 mm steel dowels on 20 mm PCD**, at 45/225 degrees between the four M4 holes, with 3 mm engagement in each part. This is not a standard MISUMI alteration or a verified supplied feature. At 5.5 N m design torque, equal load sharing gives 275 N per dowel,38.9 MPa single-shear stress and30.6 MPa projected bearing stress for 3 mm engagement. The actual pulley land, tooth-root depth, tapped-hole position and fit tolerances must be checked before accepting that pattern. Specify one controlled locating fit and the other assembly fit so the parts can be assembled without forcing misaligned holes.

A plain bore, axial collar or unspecified set screw is not a demonstrated positive torque path. The20:40 shaft outputs similarly need a keyed/pinned or manufacturer-rated hub connection; the PG1-40 stock 8 mm bore only fits an8 mm shaft nominally and requires modification for 7 mm.

## CAD follow-up

The previous retention recipe was replayed in the supplied CadQuery runtime. All **47 parts are valid single solids**, with **no build issues** after applying the adapter's own hole cuts. Primitive-solid mass is **110.93 g**. The [validation report](retention_solid_validation.json) covers individual solids; it does not replace the main assembly's connectivity, access and collision checks. The runtime exited with code 1 after producing the report, without an error message; a separate import-only CadQuery probe did the same. Geometry validation completed, but this was not a clean process-level test pass.

The new 25:50 pair reduces the output gear's working-load tangential force from 137.5 N to **110 N** at 2.75 N m; 20 degree separating force becomes **40.04 N**. Belt preload and its bearing reactions are unchanged. Recompute the final combined load and mass with the selected machined metal parts.

The [compact specification](metal_gear_spec.json) records exact catalogue geometry separately from proposed machining, along with the horn correction and remaining procurement checks. Ask for a final drawing/STEP, actual root/fillet profile, material condition, finished-face/bore tolerances, useful thread depths, permitted hole pattern, backlash and quoted price/dispatch. Nothing in this package claims that those custom features are already supplied.
