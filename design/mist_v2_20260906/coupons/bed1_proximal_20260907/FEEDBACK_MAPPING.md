# Mapping first-bed feedback to the second round

`feedback_BED1_proximal.csv` has 87 unique feature rows, all `not_tested`, with every measured field blank. Its first 74 rows preserve the original feedback records. The original `coupons/feedback_BED1.csv` is unchanged.

Use the separate `assembly_and_scale_feedback.csv` for raw inside/outside datum spans, keeper rotation/retention, simultaneous face-bolt alignment, sleeve flushness, plate insertion and other assembly observations. Do not invent a mating hardware dimension to make a scale or assembly row pass a scalar parser.

| Rows or families | Existing request parser | Existing `build_refined_bed.py` | Required handling after measurements |
|---|---|---|---|
| Original bearing, shaft, bolt, nut, insert, servo-width and wire-slot rows, 73 total | Supported when complete | Supported with their original sections | Select only unresolved measured groups with the same print profile. |
| Original `clamp_ID8`, one row | Can record a complete scalar result | Deliberately refuses clamp rebuilding | Review jaw stiffness, face gap and actual assembly before changing it. |
| `proximal_carrier_bearing_OD22`, three rows | Can describe measured scalar candidates | Not supported | Rebuild the OD34 plain-seat profile from the new contract; do not rename it `bearing_OD22`. |
| `steel_sleeve_OD6p5`, three rows | Can describe measured scalar candidates | Not supported | Keep the actual 8 mm engagement depth and the face-carrier context. |
| `jack_M4_coupling_nut_AF`, one row | Can describe measured scalar candidates | Not supported | Preserve the long horizontal pocket, side-entry opening and print direction. |
| `jack_load_plate_pocket`, one row | A single width can be recorded | Not supported | Review width, height, thickness and insertion together using the assembly sheet. |
| `slider_M4_slot_width`, one row | A single width can be recorded | Not supported | Keep the 4 mm plate, 8.4 mm total slot length, actual bolt and spreader. |
| `long_datum_X`, `long_datum_Y`, two rows | Do not use for scalar refinement | Not supported | Record raw spans separately and calculate each centre distance. |
| `proximal_carrier_keeper`, one row | Do not use for scalar refinement | Not supported | Review race contact, clearance and retention as an assembly. |
| `face_carrier_PCD`, one row | Do not use for scalar refinement | Not supported | Review four-hole alignment and the full hardware stack; a PCD is not a clearance bore. |

For a legacy-compatible second-bed subset, first create a separate CSV from the real measured rows. The existing builder accepts one to three groups using one shared print profile and verifies the source CSV hash through the request. Its request tool refuses an untouched sheet. Keep the 87-row master as the measurement record.

The new families need matching geometry built from this bed's recipe and fixed contract. The existing generic builder must reject them rather than substitute its older OD30 chamfered bearing boss, shallow nut pocket or thin shaft board. A valid request JSON alone does not mean that the generic CAD builder supports its geometry.

No second-bed request or geometry is generated now. After real feedback, combine the unresolved new and old interfaces into the second physical round with a representative assembled stack. Any generated second-bed files must remain separate from both first-bed directories.
