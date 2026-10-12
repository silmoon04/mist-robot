# Concealed wheel transmission, 7 September 2026

Keep the longitudinal FIT0493 layout as the current packaging candidate and use **KHK SM1-20 geometry** for the real 20T/module1/1:1 miter envelope. Specify **SM1-20H Hardened Plus** as the minimum plausible tooth-material candidate for the stated 1 A torque screen. Neither the plain gear nor the complete hardened assembly is released for unrestricted operation. No gear, motor or coupling was purchased.

The [geometry contract](miter_geometry_contract.json) records the manufacturer dimensions and both output orientations. The CAD agent received the dimensions before this report, including the conflict with the existing outer wheel bearing.

## Supplier dimensions to use in CAD

The [KHK 2025 catalogue](https://khkgears.net/pdf/2025/miter-gears.pdf), printed page 330, and [SM1-20H manufacturer page](https://catalog.khkgears.us/item/miter-gears/steel-miter-gears-sm/sm1-20h) establish:

| Property | Nominal value |
| --- | ---: |
| Bore | 6 mm |
| Hub diameter B | 16 mm |
| Outer pitch diameter C | 20 mm |
| Maximum tooth-tip diameter D | 21.41 mm |
| Apex-to-back mounting distance E | 20 mm |
| Overall axial length F | 13.94 mm |
| Crown-to-back G | 10.71 mm |
| Hub width H | 8 mm |
| Bore length I | 12 mm |
| Tooth face along cone J | 5 mm |
| Holding land K | 9.86 mm |
| Mass | 19 g each,38 g per pair |

This is a 45 degree pitch cone,90 degree shaft intersection,20 degree pressure-angle Gleason straight miter. Two matching gears are needed; an arbitrary same-module bevel gear is not automatically interchangeable. The plain SM gear has a nominal H7 bore; confirm finished bore and runout after hardening before assigning that fit to SM1-20H.

With the wheel apex at u140 and longitudinal input axis at Y20, the input gear's back is **u120**, hub is **u120..128**, maximum tip crown is **u130.71**, and frontmost extent is **u133.94**. The outer pitch plane is u130. The mean pitch plane used for force calculation is u131.768, not u130.

For an output hub pointing outward in +Y, the back face is **Y40**, the hub spans **Y32..40**, the tooth tip crown is Y29.29 and the frontmost extent is Y26.06. The proposed626 bearing at **Y37..43 overlaps this gear**. A bearing near Y42..48 permits some housing-floor/shim clearance, but its retainer grows the outer casing. Check the actual floor and inner-race spacer before choosing final coordinates.

An inward-facing output hub instead has back Y0, hub Y0..8 and frontmost extent Y13.94. It can leave the outer bearing in place but occupies the existing wheel hub/spoke volume. It requires a revised wheel hub and a full rotation sweep. It is an explicit alternative, not a claim that the current wheel clears the gear.

The current input pair at u106..112 and 114..120 leaves no spacer or shim before the gear back. A proposed fit within the same longitudinal envelope is **u105.5..111.5 and113.5..119.5**, leaving 0.5 mm after the coupling and0.5 mm for a steel inner-race spacer before the gear. The casing/bearing abutments, shim diameters and axial load path remain assembly checks.

## Working load and stall are separate

The KHK reference values are **0.89 NÂ·m bending /0.084 NÂ·m surface durability for SM1-20**, and **0.89/0.37 NÂ·m for SM1-20H**. The reference conditions include 100 rpm, more than 10^7cycles, uniform loading, a bidirectional bending allowance, and 100cSt lubricant at50Â°C. Those assumptions do not establish performance in this printed enclosure at the actual wheel speed.

At the supplied **0.172 NÂ·m endpoint estimate for a 1 A winding-current cap**, the plain gear exceeds its catalogue surface value by a factor of 2.05. The hardened reference surface value divided by twice 0.172 is 1.076. This supports further evaluation of the hardened part, with little spare margin after that chosen service factor. The motor endpoint model reaches about **299 rpm at 12 V and 0.172 NÂ·m**, so an actual-speed/lubrication calculation is still required. Do not label the 100 rpm table as a 300 rpm rating.

The separate **1.177 NÂ·m uncapped motor stall** exceeds the 0.89 NÂ·m bending reference. Current limiting may constrain motor-produced torque, but it does not establish resistance to externally applied wheel impacts or fault conditions. Retain a conditional current limit and stall detection; any unrestricted-stall requirement needs a different verified gear/shaft arrangement.

Using mean pitch radius 8.232 mm gives the following transmission-only screen:

| Quantity | 0.172 NÂ·m working case | 1.177 NÂ·m stall case |
| --- | ---: | ---: |
| Tangential tooth force | 20.89 N | 142.97 N |
| Separating radial force | 5.38 N | 36.80 N |
| Axial thrust on each shaft | 5.38 N | 36.80 N |
| Resultant transverse load | 21.57 N | 147.63 N |
| Input bearing reactions, centres u108.5/116.5 | âˆ’41.2/+62.7 N | âˆ’281.8/+429.4 N |
| Near-bearing bending moment | 0.329 NÂ·m | 2.254 NÂ·m |
| Ideal 6 mm-shaft bending stress | 15.5 MPa | 106.3 MPa |
| Ideal 6 mm-shaft torsion stress | 4.06 MPa | 27.8 MPa |

The opposite-sign bearing reaction comes from the overhung gear. These values exclude ground-load bending on the wheel axle, acceleration, machining notches, bearing clearances and frame deflection. Axial thrust should close through supported shaft shoulders/spacers and bearings, not through the motor's 4 mm shaft or an unspecified coupling.

SM1-20 is a plain-bore part. A checkable positive torque connection is a **2 mm transverse steel pin through the 16 mm hub and 6 mm shaft**, centred 4 mm from the hub back. This is a machining proposal, not a supplied feature. Its ideal double-shear stress is 9.1 MPa at the working cap and 62.4 MPa at full motor stall. Shaft cross-hole stress, hub edge distance, fit and pin retention still need checking. The existing 4D-to-6 mm 20 mm-long coupling remains a procurement envelope until a real part with dimensions and holding-torque data is selected.

Allowing an assumed 85-95% efficiency for the added transmission gives approximately **0.146-0.163 NÂ·m at the wheel** from the 0.172 NÂ·m shaft estimate. This range is an assumption, not a measured efficiency claim.

## Price and other real options

[RAR UK lists plain SM1-20](https://www.rargears.com/gears/miter-gears/steel-miter-gears/SM1-20) at **Â£14.13 each**, with 10-14 days subject to manufacturer availability. Two cost Â£28.26 as displayed; VAT treatment was not stated beside the price. No verified UK price or lead time was found for the required hardened SM1-20H variant. Do not substitute the plain grade on price alone.

The similarly sized **SMSG1-20R/L** ground spiral pair has higher reference working-load capacity, 1.17 NÂ·m bending and 0.97 NÂ·m surface durability at its 600 rpm basis. However, [RAR shows Â£91.48 per gear](https://www.rargears.com/gears/miter-gears/ground-spiral-miter-gears/SMSG1-20R), or Â£182.96 per pair. It needs opposite-hand gears and different thrust calculations. It is a costly comparison, not a recommendation for the stated budget.

The [right-angle motor comparison](right_angle_motor_options.md) found **DFRobot FIT0489-D** at **Â£17.29 including VAT** from TME, with a documented operating point of **0.2158 NÂ·m at 32 rpm**. On an 85 mm wheel that is 0.142 m/s and 5.08 N ideal traction. Its approximately 81 mm-long/32 mm-wide body,167 g mass and self-locking worm gearbox differ materially from the 61Ã—25 mm,98 g FIT0493 package. It does not preserve the original rolling speed or backdrivability. The Â£5.80 Adafruit 3802 alternative lacks credible continuous-torque evidence and has a drawing mismatch. Neither is accepted as a drop-in replacement.

## Verified manufacturer CAD

The actual [SM1-20_On.stp](../../references/KHK_SM1_20/SM1-20_On.stp) is now downloaded and verified: 215,015 bytes, SHA-256 `c4aebaa418f6955130f9bf4f4a798dc478b181fea47327865db2d7aedb386a98`. The [download receipt](../../references/KHK_SM1_20/receipt.json) supersedes the earlier no-local-file caveat. The original [generation receipt](khk_sm1_20_step_generation_receipt.json) remains unchanged as a historical record.

Fusion imported one supplier solid in two nested wrappers. Its [native pair check](../../cad/fusion_live_20260907/vendor_pair_probe/README.md) found **13.8656mmÂ³ interference at0Â°/0Â°**, followed by no reported intersections at input phases0Â°,3Â°,6Â°,9Â°,12Â°,15Â° and18Â° with `output phase=9Â°-input phase`. This is seven sampled positions over one tooth pitch, not continuous mesh, contact-pattern, backlash or load validation. The [native verification JSON](../../cad/fusion_live_20260907/vendor_pair_probe/verification.json) and [F3D](../../cad/fusion_live_20260907/vendor_pair_probe/KHK_native_pair.f3d) preserve those results.

OCP and Fusion agree on the bounding box, X/ZÂ±10.705 mm and Yâˆ’20..âˆ’6.06 mm relative to the pitch apex. Their integrated volumes differ by **0.289%**: 2,332.5320 versus 2,339.2692mmÂ³. Volume equivalence remains unverified. An earlier null Boolean is a failed calculation, not zero interference. Keep the supplier's 19 g mass per gear rather than deriving a new nominal mass from either volume. The imported file represents plain SM1-20 geometry; it does not establish SM1-20H material strength or duty capacity.

## Hardened pair, shaft lock and home assembly follow-up

The [bounded supplier follow-up](hardened_pair_supplier_followup.md) did not establish a live UK price or delivered lead time for **SM1-20H**. Two are required per leg, eight for four legs. TheÂ£14.13 plain SM listing cannot be used to price the hardened version or claim the same availability. The hardening-service manufacturing time mentioned in general literature is also not a delivered UK lead time.

KHK's **SM1-20J6** provides a 6 H7 bore and M4 radial set-screw provision, 4 mm from the rear hub face. It has no keyway. The [current SM catalogue](https://khkgears.net/pdf/sm.pdf) specifically excludes its J-Series lineup from Hardened Plus. Do not invent an `SM1-20HJ6` or `SM1-20J6H` combination from general H/J marketing. No shaft-holding or installation-torque rating was found for the M4 connection.

No supplier-made 6 mm clamp interface was verified that simply attaches to the selected hardened plain gear and completes the torque path. A shaft collar touching the rear face provides axial location; it does not couple the gear to the shaft. A bought clamp would still need an approved interface to the gear and enough axial space. The proposed crosspin avoids relying solely on friction, but its matched gear/shaft holes, fit, retention and effect on shaft strength remain custom machining work.

Printed brackets, covers and fit coupons can be made at home. The current transmission is **not yet a verified kit for assembly with printed parts and hand tools**: the hardened-gear attachment, final shaft/bore fits, thrust spacers, backlash setting and 4D-to6 mm coupling remain open. A printed drill guide does not by itself validate a small cross-drilled hardened hub or restore a concentric bore after heat treatment. The practical next purchasing item is a quotation for factory-finished gears and matching shaft interfaces, with price and drawings, rather than loose plain-bore gears whose attachment is left implicit. No quotation was sent.

The existing FIT0493 budget line is **Â£25.61 including VAT per motor**, alreadyÂ£10.61 above the user's approximateÂ£15 motor target. Four motors alone areÂ£102.44 against aÂ£60 bare-motor target. This is the existing project price allowance, not a newly verified shopping quote. Hardened gears, shaft locks/machining, couplings, extra bearings, lubrication/seals, drivers and delivery are additional. Because the required hardened-pair and lock prices are missing, **no complete concealed-drive cost is established**. Keep the cost of the unsuitable plain gears and the slower worm-motor alternative separate from that missing system price.
