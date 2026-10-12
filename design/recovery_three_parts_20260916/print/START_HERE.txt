# Reprint only these three parts

Use `Recovery_Three_Parts_With_Supports.stl` with `Neptune4Pro_Recovery_Three_Parts_028.curaprofile`. Keep your existing Neptune 4 Pro printer setup and startup routine, 0.4 mm nozzle and PLA. Import the profile separately and select it; loading the model does not activate the profile.

The plate contains the coxa upper/hip saddle, femur main/knee saddle and tibia main/foot. No spacers, caps, auxiliary cheeks or hub are included. Keep the successfully completed parts. These main parts retain the previous insert-compatible geometry and dimensions.

Import the STL at 100% scale and keep its orientation. It includes the removable support geometry. The optional 3MF contains the same arranged objects; do not import both formats. Do not auto-orient, drop separate support objects or delete the thin support fins. Keep automatic tree supports enabled as specified in the profile.

Estimated print time is 7 h 12 min, using about 109 g of PLA. This includes the support geometry and adhesion material. It is a CuraEngine estimate, not a measured duration, and excludes heating. No printable G-code is supplied: slice with your configured printer startup routine.

## What changed after the failed print

The previous manual femur support covered only the underside at 10.5 mm. It did not cover the small upper lip at about 37.9 mm. This recovery plate adds a bed-starting support tower beneath that lip, plus support beneath the other low ledge. See `Femur_Upper_Lip_Support.png` and `Support_Map.png`.

The coxa has added support beneath its elevated post sections. The tibia has a removable comb beneath its long raised shank. The support bases start on the bed; the upper surfaces leave a separation gap of roughly two to three 0.28 mm layers. The support fins and bases are sacrificial. Remove them after printing; retain the main ribs and integral coxa feet.

The previous faster plate omitted the brim and the tall coxa and tibia detached. Contamination, insufficient bed contact, curling, nozzle contact and motion can all contribute. The user's report does not establish one cause or demonstrate that the bed mesh is wrong. This recovery keeps the proven part geometry and backs off the process changes.

| Setting | Recovery profile |
| --- | --- |
| Layers | 0.28 mm throughout |
| Walls / infill | 5 walls / 25% gyroid |
| Top and bottom | 5 layers |
| Outer / inner walls | 35 / 60 mm/s |
| Infill / top and bottom | 60 / 35 mm/s |
| First layer | 20 mm/s, 300 mm/s2 |
| Travel | 120 mm/s, 1800 mm/s2 |
| Outer / inner wall acceleration | 800 / 1200 mm/s2 |
| Nozzle / bed | 210 C / 60 C |
| Flow ceiling | 8 mm3/s |
| Model brim | 6 mm outside only, 0.1 mm gap |
| Support brim | Enabled, 4 mm |
| Cooling | Off for first layer, full by layer 6 |
| Retraction | 0.5 mm at 35 mm/s |

The brim is restored only for this three-part recovery plate. Its gap is smaller than the previous 0.15 mm brim gap to improve the connection. Some edge cleanup is expected. It is not a raft under the whole model. Let the bed cool, remove the print, and peel the brim outward while supporting the part instead of pulling against the tall walls.

## Before starting

Clean the removable PEI sheet, rinse it thoroughly and dry it fully. Handle it by its edges and remove any debris beneath it before seating it again. For a greasy textured PEI sheet, warm water and plain washing-up liquid followed by thorough rinsing is a reasonable first step; avoid abrasive scrubbing. Keep water away from the printer electronics and heater.

Use the existing working bed mesh and startup setup initially. Watch the first layer across all three parts and the brim: adjacent lines should join without loose round strands or nozzle scraping. If one region remains visibly too high or low after cleaning and reseating, check the Z offset and bed leveling. Do not change flow or Z offset merely because the earlier tall parts detached late in the print.

ELEGOO's adhesion guidance identifies contamination and first-layer setup as checks: https://wiki.elegoo.com/en/neptune/neptune-4-series-firs-layer-not-sticking-to-pei-plate . Its warping guide also lists speed, cooling and contact area as possible contributors: https://wiki.elegoo.com/en/troubleshooting/fdm-printer/edge-warping . These support a sequence of checks, not a confirmed diagnosis of this failure.

Do not reuse the previous Faster 030 profile for this recovery attempt. Inspect the first layers and check again as the tall sections build. A clean first layer alone cannot guarantee that a part will not detach later.

## Assembly stays the same

The femur bridge takes one M3 insert and the tibia bridge takes two. Use your confirmed 4 mm outside diameter, 5 mm long inserts. The pockets remain 3.5 mm pilot diameter with a short 4 mm entry. Fit inserts flush, then allow them to cool before attaching the matching cheeks with M3x10 screws and one 0.5 mm flat washer each. Do not substitute the former M3x30 bridge screws into these inserts.

Other horn, servo-clamp and hub connections are unchanged. Your existing spacers are enough; none are on this plate.

## Verification

The three part meshes match the previous release by hash. Added support solids have no geometric intersection with the parts. Sliced motion fits inside the conservative 225 by 225 mm bed envelope. Checks found no sampled support inside the defined fastener openings. Actual extrusion paths were found at the tops of every added support group, including the previously missed upper femur lip.

These checks do not prove physical adhesion, support release force or insert retention. The prior fast process failed and this is the first physical trial of the recovery support arrangement. It does not establish full-robot load capacity.
