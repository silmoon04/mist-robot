# MIST rebuild requirements and evidence

This package develops the 6 September 2026 request. It preserves older CAD, physical calibration and inventory records. It is a new design candidate until the checks below are completed.

## Requested behavior

- Recognizable MIST appearance from the original show: white upper barrel, grey lower drum, stepped lid and handle, cyan face on black projecting screen, smaller black panel below, four angular pale legs and dark wheels.
- Three positioning actuators per leg concentrated at the hip where practical. Investigate the torque, transmission and moving-mass cost of alternatives. A separate wheel drive may sit at the foot.
- Fast rolling, walking, height adjustment, obstacle avoidance, and ascent and descent of the intended stairs.
- Native Fusion components and assembly, correct load paths, accessible wiring, assembly order, and printed parts designed for layer strength.
- Use existing servos, battery, electronics, bearings, inserts, belts and printer where suitable. No new PCB required.
- First fit bed covering the relevant interfaces with few handled parts. A second bed follows actual user measurements. Only then propagate fit changes to the first loaded leg and the remaining assembly.
- Improve the existing MIST brain's expression, prompts, tool behavior and tests.

## Working assumptions awaiting measurements

The initial rolling target is approximately 1 m/s; this is an engineering assumption, not a user-confirmed maximum. Stairs are evaluated over a range, with an illustrative 180 mm rise and 270 mm tread. The second phone model and insert geometry remain unconfirmed. The known Mi 9 SE envelope is used provisionally where needed.

On 7 September the user clarified that timing belts have not been ordered and the design may choose them freely. The selected candidate is a reinforced Gates 375-3MGT-09 with matched 32-tooth metal pulleys and 139.5 mm centres; see `package/belt_selection_20260907`. No belt purchase or physical fit is claimed.

The user also requested a complete parallel brain/face repair and then chose fast conversation with Astra background work after experiencing the slower live UI. The current profile is Spark low/standard for chat, Astra low/priority for background tasks, and the existing refined MIST ElevenLabs voice. Latency and playback repairs remain tracked under `brain_v2_20260907`.

The eight bearing codes are recovered from the actual purchase description: 693ZZ, 623ZZ, 685ZZ, 624ZZ, 687ZZ, 627ZZ, 626ZZ and 608ZZ, approximately ten each. Catalog sizes do not establish the delivered fit. The earlier 13.25 mm 624ZZ seat worked in one coupon but needed hammering in a thicker part; print orientation and wall stiffness must be represented in the new test.

## Evidence boundaries

Datasheet endpoints, assumed control dynamics, calculated results, rigid-body simulations, native CAD checks and physical measurements are different kinds of evidence. Each output must state which it contains. A passing kinematic test cannot establish bearing fit, servo temperature, printed fatigue strength or reliable stair climbing.

The old all-direct master geometry and bench calibration describe older hardware. They remain unchanged. The fictional Holodeck task packages in job-finder are not hardware measurements or order evidence.

## Completion checks

| Work | Evidence required |
|---|---|
| References and inventory | Original images viewed; thread/source index; owned versus proposed parts distinguished |
| Transmission choice | Correct coupled motor/joint equations; torque-speed, backlash, travel and packaging checks |
| Single leg simulation | Force/Jacobian checks and finite, reproducible contact simulation with stated actuator assumptions |
| Full robot simulation | Four-leg support and contact tests; rolling, walking and step results reported even when they fail |
| Fusion assembly | Actual native build run, document and component export, computed geometry and interference report |
| First coupon bed | Closed solids, fit layout on printer bed, labels, removal access, orientation and feedback form |
| Refined fit bed | User measurements applied; no invented feedback or automatic acceptance |
| First loaded leg | Assembly interfaces checked, fasteners/shafts/BOM defined, fit feedback incorporated, structural/thermal limits assessed |
| Complete robot | Four-leg assembly clearances, wiring, mass/CoM and revised simulations reconciled with CAD |
| Brain | Passing deterministic checks plus a bounded live model evaluation when configured access is available |

Full completion depends on native Fusion execution and two physical feedback rounds. These dependencies do not prevent completing the calculations, code, candidate geometry and first coupon package now.
