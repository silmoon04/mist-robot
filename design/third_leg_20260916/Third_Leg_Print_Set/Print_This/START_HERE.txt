# Third leg print set

Print one copy of `Third_Leg_Complete_With_Supports.stl` using `Neptune4Pro_Third_Leg_Faster_030.curaprofile`. This is one complete set of 14 printed leg components on one bed, including the yaw clamp, all three caps and four spacers. Keep your two completed legs and centre hub.

Use your existing Elegoo Neptune 4 Pro printer configuration and startup routine, with a 0.4 mm nozzle and PLA. Import the STL as one object and keep its supplied orientation and scale. Import and select the profile separately; the model does not activate it automatically. The 3MF contains the same geometry as separate named objects. Use either the STL or the 3MF, not both.

The orange comb in `Knee_Saddle_Support.png` is part of the supplied print geometry. Keep it in the slice, then remove it after printing. Automatic tree support remains enabled for other undersides. Model brim and support brim are disabled; the separate skirt is not attached to the parts. Retain the blue structural ribs and coxa print feet.

## Time and settings

| Same complete plate | CuraEngine estimate | PLA estimate |
| --- | --- | --- |
| Faster 0.30 mm profile | 8 h 43 min | 177 g |
| Familiar 0.28 mm profile | 10 h 18 min | 175 g |

The faster profile saves about 95 minutes, or 15%. Both estimates include the removable comb and generated tree supports. The old overnight plate contained only eight parts, so its time is not a like-for-like comparison with this full set.

The comparison uses the same installed Cura 5.13 Neptune acceleration limits for both slices. Earlier analysis used a lower generic machine acceleration limit, which produced longer estimates. Actual Cura settings, printer firmware, heating and motion can change the time. These are slicer estimates, not measured print durations.

| Setting | Faster profile |
| --- | --- |
| Layer height | 0.30 mm; first layer remains 0.28 mm |
| Walls | 5, with 0.42 mm nominal line width |
| Top and bottom | 5 layers, nominally 1.5 mm |
| Infill | 25% gyroid |
| Outer / inner walls | 50 / 85 mm/s |
| Infill / top and bottom | 85 / 60 mm/s |
| First layer | 25 mm/s, 500 mm/s2 |
| PLA / bed | 215 C after the first layer; 210 C first layer; 60 C bed |
| Travel | 190 mm/s |
| Flow ceiling | 11 mm3/s candidate |
| Retraction | Existing 0.5 mm at 35 mm/s |

The familiar profile retains 0.28 mm, 210 C, outer walls at 40 mm/s, inner walls/infill at 65 mm/s and the previous 8 mm3/s flow ceiling. It also uses a skirt and the new removable comb. No acceleration increase was retained in either print profile.

The new 0.30 mm process and higher flow have not been physically tested on your filament. Check the initial layers and extrusion on this first use. The faster file is a candidate process, not a guarantee of unchanged finish or unattended reliability. The familiar profile is included if you prefer the previously successful speeds.

## What changed

- The knee-servo saddle on the main femur has a removable comb underneath its elevated flat underside. Its narrow fins rise from a thin base, with a nominal 0.7 mm geometric gap to the model. Actual sliced contact spacing depends on layer rounding. The fins avoid the model below and have no intersecting CAD volume with the part.
- Nine clamp nut openings have shallow tapered lead-ins. Their inner seats and M3 through-bolt positions remain unchanged. The entry is relieved for 0.4 mm of depth; this is not a larger pocket throughout.
- The main femur has one insert pocket and the main tibia has two. They accept the confirmed M3 inserts with 4 mm outside diameter and 5 mm length. Each has a 3.5 mm pilot extending 5.6 mm, and a 4 mm entry for the first 0.55 mm. This follows your successful drilling approach. Do not enlarge the full pocket to 4 mm.
- All four spacers are 13 mm tall, 5.5 mm outside diameter, with a 3.4 mm bore, matching the set you confirmed is installed and rotating freely.
- The main brackets keep five walls and 25% infill. The speed increase does not depend on reducing their wall count.

## Inserts and the three shorter bridge screws

Install the inserts before installing the servos. Use controlled heat to seat them square and flush, then let them cool fully before tightening screws. These are pilot pockets for heat insertion, not cold press-fit holes. Clear minor stringing first; do not hammer the inserts in.

| Main part on the plate map | Insert location | Matching cheek | Fastener |
| --- | --- | --- | --- |
| 10. Main femur and knee saddle | One small hole in the end face of the raised connecting bridge | 11. Femur auxiliary cheek | One M3x10 and one 0.5 mm flat washer |
| 13. Straight tibia and foot | Two small holes in the end face of its raised connecting bridge | 14. Tibia auxiliary cheek | Two M3x10, each with one 0.5 mm flat washer |

The insert openings face the detachable cheeks. They are separate from the four peripheral holes around each servo shaft. Do not put inserts into the metal horn or auxiliary disc holes.

Each M3x10 passes through the 5 mm cheek and one 0.5 mm washer, leaving 4.5 mm to engage the 5 mm insert. The insert must be flush; this calculation also depends on washer thickness. Do not substitute the former M3x30 bridge screws here. The old internal nut-loading slots remain in the geometry but are unused for these three connections. Do not load nuts there as well.

This removes three loose bridge nuts and replaces three long screws with shorter ones. It does not reduce the number of screws. The nine servo case-clamp screws remain M3x30 with captive nuts: they clamp across the case without depending on an insert's pullout resistance in the end wall. They now have the easier nut entries.

## Assembly order

1. Remove the orange comb and tree supports. Check the knee saddle's underside and all clamp tabs are complete. Keep the integral ribs and feet.
2. Install the three bridge inserts and let them cool. Fit the remaining clamp and coxa post nuts before enclosing their access slots.
3. Assemble the yaw saddle, servo and cap, then the upper coxa, inward-facing hip servo and its cap in the same arrangement as your working legs.
4. Fit the lower coxa arm and four matching 13 mm spacers. Follow the hardware stack you used on your freely rotating completed joints. Do not pull the arms into alignment by tightening screws.
5. Attach the main femur to the hip horn, fit the knee servo and its cap, then fit the femur auxiliary cheek. Use its new single M3x10 bridge screw and washer.
6. Attach the main tibia to the knee horn, then the tibia auxiliary cheek. Use its two new M3x10 bridge screws and washers.
7. Keep the existing peripheral horn fasteners: M3x6 with one 0.5 mm washer at the main pitch cheeks, and M3x12 with two 0.5 mm washers at the auxiliary pitch cheeks. Keep the supplied centre retainers and their correct fixed-stub/rotating-disc arrangement. The insert screws do not replace any of these.
8. Check free movement, cable clearance and screw seating before powering the assembled leg. Begin unloaded and with small movements before connecting it to the hub.

The 13 mm spacers are included on the basis of your physical fit report. The historical CAD stack used 11.6 mm, so this release does not claim a newly calculated yaw screw engagement or axial stack for the changed spacers. Preserve the working hardware arrangement and check that the screws engage without bottoming or binding.

The separate cheeks allow the main plates to print flat and provide access to the servo discs. Combining them now would change print orientation, support needs and assembly access. Your two assembled legs do not need replacing just to match these easier bridge fixings.

## Checks and remaining limits

All 14 parts passed mesh checks for closed surfaces and consistent face direction. The modified bodies are valid single CAD solids. The insert pockets and lead-ins remove material locally without moving the existing servo and horn interfaces. Sliced motion fits within the conservative 225 by 225 mm bed envelope.

Both slices were checked for tree-support centreline midpoints inside the defined fastener openings; none were found. The comb spacing screen found a maximum sampled horizontal distance of 2.5 mm to a fin or existing model beneath the targeted underside. These checks do not prove easy support removal, successful bridging or insert pullout strength.

This is a revised physical prototype. The new insert connections and faster process still need their first physical result. No new full-robot load capacity or gait qualification is claimed. Individual STEP and oriented STL files are included for further changes.
