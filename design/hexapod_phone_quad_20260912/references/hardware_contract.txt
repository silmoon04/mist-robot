# Hardware contract, 12 September 2026

This fresh four-leg design uses twelve C018 servos for the legs and one for upright phone pan. No prior robot geometry is adopted. Manufacturer drawings establish nominal interfaces; delivered units and printed fits remain unmeasured.

The [Feetech C018 A/0 specification, dated 20 July 2023](https://cdn.robotshop.com/media/F/Fit/RB-Fit-155/pdf/feetech_12v_30kg_cm_magnetic_encoding_servo_sts321_specification_pdf.pdf) is manufacturer-authored and distributor-hosted. Pages 6 and 7 were visually checked against the local PDF. The manufacturer's [product index](https://www.feetechrc.com/products.html?keyword=STS3215) identifies ST-3215-C018 as the 12 V variant; generic STS3215 sheets can describe different variants.

| Drawing interface | Nominal value, mm unless stated |
|---|---|
| Case footprint | 45.23 × 24.73 |
| Axis from case midpoint | 12.5 toward the rounded end; short-end distance 10.115 and long-end distance 35.115 |
| Profile references | 32 and 35; do not substitute one rectangular case box for every section |
| Opposed local faces / projections / total | 29 / 3.4 output and 4.1 auxiliary / 36.5 |
| Output spline / retaining screw | 25T, Ø5.9 / M3×6 |
| Main horn | Ø19.95, four M3 on Ø14 circle |
| Main horn flange / total / boss | 2.5 / 4.5 / Ø9 |
| Female spline depth / central opening | 3.6 / Ø3.2 |
| Auxiliary stub / retaining screw | Ø6 / PA3.0×5 self-tapper |
| Auxiliary disc | Ø19.95, Ø6.05 bore, four M3 on Ø14 |
| Auxiliary disc flange / total | 2.1 / 3.1 |
| Connector | Dual 5264, 2.54 pitch, three pins: GND, Vcc, TTL |
| Supply / rated load / stall | 12 V nominal, 4 to 14 V range / 10 kg·cm at 0.9 A / 30 kg·cm at 2.7 A |
| Mass | 55 ±1 g each |

Correction recorded 12 September 2026: page 6 dimensions 12.5 mm from the case midpoint to the shaft axis. The earlier interpretation as a short-end distance was wrong. See the [high-resolution witness-line crop](../manufacturing/knee_inward_study/c018_dimension_witnesses.png). The supplier STEP independently matches the 12.5 mm center offset; its footprint differs by less than 0.007 mm from the rounded drawing values. The adjacent G, V and S socket labels are pin names, not socket-position dimensions.

The main horn's raised spline boss faces the servo. Printed cheeks contact its flat outer face. Peripheral screw engagement comes from the 2.5 mm flange, not the total horn thickness. Preserve central screw and tool access. The mounted horn stack depends on actual spline seating; adding 4.5 mm to the shaft tip is incorrect. The [auxiliary drawing crop](aux_detail.png) confirms Ø6 and PA3.0×5; these must not be confused with the powered shaft interface.

Use a direct-drive U-yoke: its powered cheek bolts to the supplied metal horn; the opposed cheek bolts to the supplied auxiliary metal disc. A removable bridge closes the yoke around a positively located two-piece case clamp. Provide clamp contact lands and end stops while keeping both connector sockets open. Use independent cheek assembly so neither side must be sprung over the case. This supports the moving link from both sides, subject to checking auxiliary free rotation, screw retention and actual load capacity. It does not establish a bearing load rating. Do not replace the metal spline with printed teeth or assume a spare 626 bearing fits the stub: its 6 mm width exceeds the 4.1 mm projection.

Rated load converts to 0.981 N·m; stall is 2.942 N·m. Rated load is not an unlimited continuous thermal guarantee. The specified cyclic life test uses one-fifth stall, equivalent to 0.588 N·m. Use that lower value for initial sustained-load screening, then validate temperatures and loaded walking experimentally. Thirteen bare servos weigh approximately 715 g. Nominal aggregate rated and stall currents are 11.7 and 35.1 A; these arithmetic sums are not a measured gait demand or fuse selection.

The sockets face the auxiliary shaft side. Supplier STEP geometry establishes their location; the nearby G, V and S labels are electrical pin names. The operator measured about 34.8 to 35 mm across the bare case including the rear bulge, about 1.5 mm added by the cable, and requested 2 to 3 mm working clearance for the flexible lead. R4 uses the 35 mm case profile, 1.5 mm plug projection and 2 mm additional clearance in the cable pocket. This supersedes the earlier 15 mm reservation. These approximate overall measurements do not establish exact shaft-referenced plug coordinates or insertion clearance. Check the actual plugged servo in the combined case-and-shaft fixture and through the intended sweep. See [the operator measurement](../manufacturing/knee_inward_study/OPERATOR_MEASUREMENT.md) and [connector evidence](../manufacturing/knee_inward_study/connector_evidence.md).

The [official Xiaomi specifications](https://www.mi.com/mi9se/specs) give Mi9SE dimensions 147.5 × 70.5 × 7.45 mm, mass 155 g and USB-C charging. They do not dimension camera bump, lens centres, buttons or plug overmould. The bare phone sits upright in landscape orientation in an open-backed cradle with edge retention and side access to USB. The phone uses its battery and Wi-Fi during unrestricted pan; park and disable pan before connecting USB. Verify the camera view, button relief, retaining pads and actual plug with the phone coupon.

The local inventory history records about ten each of 693ZZ, 623ZZ, 685ZZ, 624ZZ, 687ZZ, 627ZZ, 626ZZ and 608ZZ. Nominal ID × OD × width respectively: 3×8×4, 3×10×4, 5×11×5, 4×13×5, 7×14×5, 7×22×7, 6×19×6 and 8×22×7 mm. Screws, nuts, washers and inserts are owned; exact counts, lengths and insert sizes are unresolved. Earlier July claims that all M3 hardware is missing are stale.

The owned [Neptune 4 Pro](https://www.elegoo.com/products/elegoo-neptune-4-pro-fdm-3d-printer) has 225×225×265 mm build volume. Use a conservative 215 mm XY packing area. Previously used PLA settings were 0.30 mm layers, five walls and 30% cubic infill; they are history, not qualification. Print the R4 combined case-and-shaft gauge, horn-stack and auxiliary-disc coupons at the final orientation, PLA and wall count. Test the supplied clearance alternatives, M3 holes, tool access and freely rotating opposed cheeks. Acceptance requires hand assembly without hammering, positive retention and unrestricted leads throughout the intended joint sweep. Structural PLA specimens and the supported single-leg test precede loaded operation. A change of material or orientation requires its own repeat tests.
