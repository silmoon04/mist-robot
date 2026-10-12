# Fusion joint axis verification

Fusion 2705.1.11 accepted the custom axis input for an as-built revolute joint but moved the femur around world Z. Both a parent construction-axis proxy and a root-owned world axis produced the same result. The one-degree test measured the wrong rotation and restored the assembly's neutral pose.

A March 2025 [Autodesk Community report](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/asbuiltjoints-add-seems-to-disrespect-jointdirections/td-p/13360610) describes this behavior and a workaround: orient `JointGeometry` using a sketch whose normal follows the intended hinge, then select the geometry's Z direction. This is a firsthand community report, not an Autodesk release note.

The importer now creates a parent-owned plane and circle for each joint before enabling history. The circle center defines the hinge position, and its plane normal defines the joint frame's Z axis. `JointGeometry.createByCurve` and `ZAxisJointDirection` replace the custom-axis path. Their signatures were checked against the installed API declarations.

Revision `hex_quad_r5_inward_hip_straight_tibia` passed native execution on 12 September 2026. Fusion imported 14 links containing 133 closed solids. All 13 joints passed the one-degree world-motion and datum-displacement checks, and every neutral pose was restored. The native interference analysis found no positive-volume intersections in that pose. The source hashes and final F3D, STEP and PNG hashes are recorded in `output/fusion/native_report.json` and `output/fusion/tooling_provenance.json`.

This verification uses final manifest `67f0d5e3bfb633414722b17305cef4212ca7f8fa753aa922a252bc383306ad3d`, with the corrected deck reliefs and all four coxa yaw limits set from -19 to 19 degrees. A read-only native audit confirmed that the actual getters for all 13 joint limits match the manifest; its record is `output/fusion/native_limits.json`. Earlier native exports remain under `manufacturing/interim_native_ce504f86` and `manufacturing/interim_native_a0a035fb`. Full-range collision results belong to the separate motion audit.

The largest measured datum error was 2.56e-13 mm. This confirms the native kinematic transformation used by the test; it does not measure printed fit, physical stiffness or walking performance. Each geometry revision still needs its own motion and interference receipts.

The R5 runtime loads verified source bytes from its own directory under a dedicated module namespace and document attribute group. Its output paths remain within the R5 directory. R4 source helpers and its exported native archive retained their recorded hashes throughout this build.
