# C018 connector face evidence

Checked 2026-09-12 against the manufacturer's C018 drawing and the current leg CAD. The two bus sockets are on the auxiliary shaft face, alongside the auxiliary axis. The current longitudinal tail connector reserve uses the wrong face and cannot justify pointing the knee case outward.

## Primary sources inspected

- [Feetech ST-3215-C018 product page](https://www.feetechrc.com/525603.html) identifies the 12 V, 30 kg.cm C018 variant.
- [Feetech C018 specification, edition A/0, dated 2023-07-20](https://www.feetechrc.com/Data/feetechrc/upload/file/20240507/6385067068652648096680943.pdf). Local original: `design/mist_v2_20260906/references/C018_manufacturer_spec.pdf`. Page 6 was visually inspected through its existing `C018_page6.png` rendering. Only manufacturer dimensions and connector topology were used, with no old MIST part geometry.
- Page 6 lower right orthographic view shows the auxiliary shaft and two adjacent three-pin socket openings on the same broad face. The callout reads `5264/2.54 3P`. The main-shaft view is the upper left view; the ports are not drawn on that face. The case drawing gives 45.23 mm length, 24.73 mm width, 12.5 mm from the longitudinal case midpoint to the shaft axis, and the 29 mm face separation plus stepped rear profile.
- Page 7 was inspected for the supplied main horn and auxiliary disc. It does not dimension the cable plug or its swept routing space.
- [Waveshare ST3215 wiki](https://www.waveshare.com/wiki/ST3215_Servo) links an [official supplier STEP archive](https://files.waveshare.com/upload/5/59/ST3215-3D.zip). Downloaded as `ST3215-3D_supplier.zip` beside this note and extracted to `ST3215-3D_supplier/ST3215.step`, 3,025,101 bytes. The STEP header is dated 2022-06-08. It is a useful supplier geometry reference, but predates the dated C018 specification and has not been verified as the exact owned variant. The bounded inspection below records dimensions measured from that STEP separately from the C018 drawing.

Archive SHA256: `2735561E0C1DC899B35D4740273E5340F15967028D2DD4014FEED03D8175562C`.

## Correction in the current CAD coordinates

`cad/leg.py` puts the main shaft face at servo-local Z = 0 and the auxiliary face at Z = -29, with the auxiliary shaft extending toward negative Z. The connector extraction direction is outward through that auxiliary face, along local -Z. Insertion is along local +Z. This is parallel to the output shaft axis.

The `_pitch` transform maps outward local -Z to leg -Y, irrespective of the 180 degree tail orientation rotation around local Z. Turning the case tail inward relocates the sockets in the leg's XZ plane but does not turn their extraction direction into a longitudinal X direction.

The existing `servo_envelope()` opening at X = -33 to -27, Z = -25 to -14 models a hole through the tail end. `check_leg_grid.py` then reserves X = -47.73 to -32.73, Y = -9 to 9, Z = -27 to -9. That 15 by 18 by 18 mm box is an assumed allowance at the wrong face. Its pass or failure is not evidence about actual plug clearance. The tail aperture in `case_clamp()` inherits the same location assumption.

## Design implication and remaining measurements

An inward knee can tuck its long case between femur cheeks, subject to the actual case, clamp and moving-link checks. Cable access will likely require an opening or edge relief in the auxiliary cheek at the sockets' transformed position. A tibia yoke cheek that rotates across the same face also needs its swept cable clearance checked. The opening must pass the plug housing and permit service insertion, then allow the wires to bend without being trapped against a rotating cheek. A longitudinal tail opening alone does not establish this.

The inspected drawing does not dimension the complete plug housing, socket center offsets, insertion stroke, latch access, cable bend radius or wire bundle under strain relief. Those values remain unmeasured. No precise offsets were inferred from unscaled photos. Attempts to fetch current manufacturer product photos through the web tool did not provide inspectable images, so they were not used as evidence. Preserve a clearly labelled provisional reserve until the owned plug and case are measured or a matching supplier model is validated.

## Bounded supplier STEP inspection

`inspect_supplier.py` imports the downloaded STEP through OCP using the existing stable Python runtime and the new CAD's `geom.py`. It produces `supplier_orthographic.png` and `supplier_auxiliary_edges.png`. These are line projections of the supplier model, with internal edges visible in the three-view image, rather than hidden-line production drawings.

The imported assembly contains eight solids. Its overall bounds, including fitted accessories, are X = -35.611704 to 9.611704, Y = -28.2 to 9.6, Z = -12.361704 to 12.361704 mm. X is the long case direction, Y is the shaft direction, and Z is the short case direction. The 45.223408 by 24.723408 mm long/short dimensions closely match the C018 drawing's 45.23 by 24.73 mm.

The shaft axis is at supplier X = -25.5, Z = 0, and the case midpoint is X = -13. The 12.5 mm difference matches the C018 drawing. Reinspection of the high-resolution PDF witness lines corrected an earlier mistaken reading of that dimension as an end distance. The C018 short-end distance is 45.23/2 - 12.5 = 10.115 mm, and its long-end distance is 35.115 mm. The supplier STEP has 10.111704 and 35.111704 mm respectively, within 0.003296 mm of those nominal distances. Its footprint and shaft placement are therefore dimensionally compatible with C018 to the drawing precision. This compatibility does not establish exact purchased-unit identity. The main and auxiliary case planes near the shaft are supplier Y = 4.9 and -24.1 mm, giving the expected 29 mm separation. The auxiliary shell extends to Y = -28.2 and the opposite case shell to Y = 7.5. These extrema include local features, so they must not be treated as full-face positions. A complete mapping of the 32 and 35 mm profile callouts has not been established by this inspection.

The auxiliary shell shows an elongated access region adjacent to the shaft. Its visible boundary is approximately supplier X = -13.85 to -8.15, Z = -10.7 to 10.7 mm. These are shell opening extents, not two measured plug housings or port centers. The model does not expose a pair of detailed connector housings and pins in this region. In shaft-relative coordinates the slot lies approximately 11.65 to 17.35 mm toward the tail. This is a useful dimensional candidate for a cheek access window, given the matching footprint and shaft position. It remains a shell access region rather than a measured plugged-cable envelope.

The high-resolution `c018_dimension_witnesses.png` crop confirms that the symbols beside the paired sockets are G, V and S pin labels, not dimensions such as 5.3 mm. No exact socket center offsets are dimensioned there. Size a candidate cheek opening from the supplier shell access region plus a clearly labelled allowance, then replace the plug and cable allowance with measurements. The correction was recorded on 2026-09-12; the initial interpretation of the 12.5 mm witness lines was wrong.
