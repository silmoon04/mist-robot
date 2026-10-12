# Native manufacturer gear check

Fusion imported the actual KHK `SM1-20_On.stp` as one supplier solid inside two nested component wrappers. The file SHA-256 is `c4aebaa418f6955130f9bf4f4a798dc478b181fea47327865db2d7aedb386a98`. The CAD describes the plain SM1-20 geometry. The proposed hardened SM1-20H variant has separate material and load assumptions; importing this file does not establish its strength or duty rating.

The native check found **13.8656 mm³ of interference at input/output phase 0°/0°**. With the output shifted by 9°, there were no reported intersections at input phases 0°, 3°, 6°, 9°, 12°, 15° and 18°, with output phase `9° − input phase`. These are seven sampled positions over one tooth pitch, not continuous mesh or load validation.

The wrong rotation direction produced a null Fusion interference result at 3°/12°. That is a failed Boolean calculation, not zero intersection; the original failure is retained in `verification_with_wrong_sign_failure.json`. The successful counter-rotation run includes the unphased collision as a control. Its native F3D and screenshot are in this folder.

Both importers agree on the bounding box: X/Z ±10.705 mm and Y −20 to −6.06 mm, with the origin at the pitch apex. They disagree on integrated volume: OCP reports 2,332.5320 mm³ and Fusion reports 2,339.2692 mm³ at its very-high calculation setting, a 0.289% difference. Volume equivalence is therefore **unverified**. The initial native single-gear import test deliberately failed that comparison. OCP's zero-overlap results with self-intersection warnings must not be used to claim clearance; the unphased native collision demonstrates the risk.

The supplier's nominal 19 g mass per gear remains the mass assumption, independent of the small integration difference. Bearings, thrust retention, hub-to-shaft torque transfer, lubrication, backlash and enclosure heat are separate assembly requirements.
