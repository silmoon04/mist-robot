# Proximal knee transmission interface

This package specifies a sliding motor/pulley cassette and a face-bolted rotor for the next leg CAD variant. It preserves the Gates 375-3MGT-09,32:32,9 mm belt selection and 139.5 mm nominal pulley centres. It is a dimensioned prototype interface; neither the printed torque carriers nor the completed leg has a load/backlash release. No hardware was purchased and no supplier was contacted.

## Geometry implemented

The dependency-free [retention recipe](../../cad/leg_proximal_20260907/retention_recipe.py) returns 47 parts, 8 target-specific cut groups and metadata. It uses `x=transverse`, `y=shaft axis`, `z=-u`, where u runs from the proximal pulley toward the knee. The caller supplies the motor cassette, bearing housings, main carriage plate and fixed rail connections. Main leg integration owns collision sweeps and world transforms.

`build_retention_recipe(femur_length_mm=139.5, carriage_u_mm=0, mount_y_mm=-7, input_right_bearing_start_y_mm=42.325, knee_right_bearing_start_y_mm=42.325, axial_endfloat_mm=0.05)`

The complete motor, 20:40 reduction pair, input pulley and 627 supports move together. This preserves gear mesh as belt tension is adjusted. Positive carriage travel moves the proximal pulley toward the knee: `C=139.5-delta`. The implemented 4 mm travel is delta −1..+3 mm, giving 140.5..136.5 mm geometric centres. Most travel is for installation; the final tensioned position must be measured. The catalogue's nominal length is not an unloaded reference from which to prescribe an exact stretch displacement.

The proximal carriage end is circular R17 to clear the fixed yaw case. It widens to x±25 at the mounting lands after u16. Mounting planes are fixed rail/femur cheek y−13..−7 and carriage y−7..−3. Four M4 bolts sit at u22/56 and x±18. Each carriage slot is 4.4 mm wide and 8.4 mm overall long, with 4 mm centre travel. The slots are asymmetric about nominal bolt positions to implement delta −1..+3. Each ordinary M4 head bears on a 12×14×1.5 mm steel spreader above the slot. Lower washers and nuts still need integration with the real femur's existing features.

The fixed distal jack bridge spans u76..96. An M4×30,0.7 mm-pitch screw pushes a 12×12×1.5 mm steel pad at the carriage's distal edge. A steel DIN6334 M4×12 coupling nut sits at u78..90 and reacts into an 18×18×2 mm steel plate at u90..92, backed by a 4 mm printed wall at u92..96. A jam nut locks against the downstream bridge face. Reserve a straight3 mm hex-key approach from u110 and 7 mm spanner access. The caller must connect this bridge to the rails, cut a side-loading opening for the steel plate and fit a small retaining cover without removing the downstream load wall. [Coupling-nut drawing](https://www.aspenfasteners.com/content/2D_PDF/product90/ME426-407X12.PDF), [M4×30 dimensional example](https://www.accu.co.uk/metric-cap-head-screws/608075-SSCF-M4-30-A2-R360).

This is a locked adjustment. Belt loading keeps the screw against its pad; no spring idler is added. The two guide rails must constrain transverse movement and yaw, while the four through-bolts clamp the carriage. The jack remains a positive longitudinal stop after tightening. Initial guide clearances and clamp preload remain print/assembly fit choices.

## Rotor and axial stack

Use proposed factory configurations `GPA32GT3090-A-H7-QFC16-M4` and `GPA32GT3090-A-H8-QFC16-M4`. MISUMI's published rules allow four M4 axial holes on 16mmPCD with 8 mm nominal tapped depth in this A-shape pulley. These strings still need acceptance and a drawing from the supplier. The catalogue states Gates Unitta 3GT compatibility; confirm the supplied 375-3MGT-09 pairing on the quotation. [Pulley drawing](https://uk.misumi-ec.com/pdf/fa/2014/P1_1383-1384_F19_EN_001.pdf), [alteration rules](https://uk.misumi-ec.com/pdf/fa/2014/P1_1377-1378_F19_EN.pdf).

| Axial item | Proposed y interval or centre,mm |
| --- | --- |
| Left input627 | 5..12, centre8.5 |
| A-shape input/output pulley | 14.125..28.125 |
| Belt centre | 21.125 |
| Input40T gear or knee adapter | 28.125..36.125 |
| Ordinary M4 face heads | 36.125..40.125 |
| Right input627 and outer knee608 | 42.325..49.325, centre45.825 |
| Input shaft | 3..51.325, diameter7 |
| Knee shaft | −24..52, diameter8 |
| Left knee608 | −14.2..−7.2, centre−10.7 |

Moving the input 40T gear between the 627 pair lets it bolt directly to the pulley. The knee pulley similarly bolts to a printed hub with rails reaching the tibia tie points at u48, x±9. This torque path avoids dependence on an unspecified shaft grub screw. It requires the printed carrier, sleeves and face connection to be validated.

The recipe uses ordinary M4×14 socket screws with 7 mm head diameter and 4 mm head height. Nominal engagement is 6 mm into the 8 mm-deep pulley holes. Eight custom steel sleeves,OD6.5/ID4.3/L8 mm, carry the heads through the printed carriers. No head counterbores remain. The screw exists as a standard UK product: [Accu M4×14](https://www.accu.co.uk/metric-cap-head-screws/250554-SSCF-M4-14-A4-R360). Actual useful tap depth, end chamfers and thread engagement must be checked on the supplier drawing.

Ordinary M4 threads inside 4.3 mm sleeves do not form a precision locating joint. If face friction slips and the clearance is taken up in hole bearing,0.3 mm diametral clearance at8 mm radius corresponds to roughly 2.15 degrees of reversal movement. This is a conditional failure estimate, not a prediction that the preloaded joint will move by that amount. A tested face-friction joint or positively located metal carrier is required for the low-backlash objective. The JSON and part notes retain that unresolved interface explicitly.

M3 end screws and custom steel OD12/ID3.2/t1.6 washers locate the steel shafts axially. Both washers bear directly on the shaft ends. The selected spacer train is 0.05 mm shorter than the shaft span so screw tightening reacts on the shaft rather than forcing preload through the bearing pair. Measure the real stack and adjust spacer length to obtain the intended 0.02..0.10 mm prototype endfloat range. Nominal CAD lengths cannot establish that fit.

The head-clearance spacers neck to OD8.6 through y36.125..40.625, then grow to OD10 at the right bearing. Their IDs are 7.2 and 8.2 mm. The knee neck therefore has only 0.2 mm radial wall and 5.28 mm² section. It is an explicit custom-machining and axial-load check, not a stock tube assumed strong enough. The input neck has 17.37 mm² section. Neither neck is intended to carry arbitrary end-screw clamp force. Confirm the actual bearing inner-race abutment and chamfer before making spacers.

## Tension and load estimates

For 2.75 N·m working peak, the initial low-speed estimate is 108.89 N per span, giving 217.78 N radial pulley load. Gates' sonic mass constant for standard 3MGT is 2.8grams/metre/mm, giving a calculated 235.6 Hz starting target at 139.5 mm free span and 9 mm width. The adjusted sonic constant is not a verified physical belt mass. Measure both spans after hand rotation and again after locking; use the final actual span in the calculation. [Gates manual, printedp65](https://www.gates.com/content/dam/documents-library/catalogs/light-power-and-precision-manual.pdf), [Gates sonic constants](https://www.gatesaustralia.com.au/~/media/files/gates-au/industrial/brochures-and-marketing-collateral/508c-stm-card-aus--nz-september-2013.pdf).

As a stiffness proxy, Gates' long-length 3MGT9 table gives 8.9 lbf for 0.1% elongation and describes equivalent tensile modulus to conventional belts. This implies EA≈39.59 kN and `dT/dC≈2EA/L=211.1N/mm` for a 375 mm loop. Thus 0.1 mm centre movement changes span tension about 21.1 N in a rigid assembly. A full 0.7 mm screw turn would change it about 147.8 N; even 1/32turn is about 4.62 N. Frame compliance lowers the effective slope and creep changes the position with time. Measure the assembled slope rather than installing by screw count. The catalogue centre-distance tolerance of±0.23 mm for this belt length alone corresponds to roughly±48.6 N under this proxy, another reason to provide adjustment.

| Bearing pair | Belt-only reactions,N | Conservative belt plus gear reaction bound,N |
| --- | --- | --- |
| Input627 at y8.5/45.825 | 144.1 / 73.7 | 197.8 / 166.3 |
| Knee608 at y−10.7/45.825 | 95.2 / 122.6 | Additional ground/wheel loads excluded |

The input bound adds absolute gear-reaction contributions, using the 40T, module 1, 20 degree gear at y32.125: 137.5 N tangential and 50.05 N separating force. It avoids assuming favourable vector cancellation. Belt preload alone gives 5.69 N·m overturning moment between belt centre y21.125 and carriage midplane y−5. The 34 mm mounting-row spacing gives a 167 N row-pair couple, about 84 N per bolt, before gear and external loads. Add short bearing-to-carriage gussets and check the printed rail/plate assembly under that moment.

These are transmission-only working-load estimates. They exclude the leg's full ground reaction, dynamic acceleration, servo stall and impact. No bearing life or complete shaft strength conclusion follows from them. Full nominal servo stall after2:1 is about 5.884 N·m before losses and variation; existing torque/stall limits remain conditional.

## Mass and alternatives

The slider adds zero bearings and zero idler-bearing mass. Its hardware and jack bridge have a conservative 51.2 g additive-volume estimate. A separate carriage plate is approximately 18.8 g before cuts and fixed rails approximately 24 g before cuts; the latter overlaps existing femur structure. These cannot be summed as an exact net addition until the final CAD union/difference is measured. The full 47-part retention recipe is approximately 113 g gross, including the tibia adapter and shaft spacers which replace existing parts. [Mass calculation](retention_mass_estimate.json) separates the parts and basis. The supplied M4×14 mass is 2.05 g each; other preliminary values deliberately ignore Boolean overlap/cuts and so are upper bounds.

The fully specified Mädler 61520800 locking bush carries a 20 N·m catalogue rating but adds 40 g each. Pairing it with a correct steel 15 mm-bore GT pulley is not yet cleared: its 70MPa hub pressure produces an estimated 193.5MPa von Mises stress in a smooth ID15/OD25 cylinder before local details. A yield margin of two needs at least 387MPa certified material strength. The catalogue's generic steel name does not establish that strength. The Fairloc 32T alternative is supplied with a 6 mm bore; request factory 7/8 mm versions and exact slip-torque data rather than reaming the wedge. Both remain documented procurement alternatives in [supplier notes](supplier_interface_notes.md).

## Integration and verification

Apply `input_gear`, `input_shaft`, `knee_shaft`, `tibia_main_cheek`, `carriage_plate` and `fixed_rails` cut groups to the corresponding parent geometry. Apply `tibia_hub` cuts to `RT_knee_face_bolted_adapter`. All `RT_input_*` parts carry `rigid_group=knee_input_rotor`; rotate those with the knee input. Slider and jack parts stay in the femur frame. Input coordinates already include `carriage_u_mm`; do not translate them a second time.

The module was compiled and its three travel settings were checked for supported primitive types and unique part names. The saved snapshot records the latest nominal recipe. Parent CAD must verify solids, shaft/housing fits, part connectivity, tool access and full-motion/travel collisions. A low-load reversing test and tension-repeatability measurement are required before assigning an operating torque to the printed carriers.
