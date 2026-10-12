# MIST Fusion guide — research and verification record

Checked 2026-07-12 against Autodesk Fusion `v2704.1.23`, released 2026-07-09.
This file records why the guide deliberately differs from the six AI posters and
from older MIST CAD notes.

## Authority order

1. Physical caliper measurements and coupon results.
2. `../MIST_FUSION_MASTER_DIMENSIONS.md`.
3. `../../../sim/js/kin.js` for coordinate frames and joint-axis convention.
4. Current inventory, material, print-test, and build-phase documents.
5. Older variant/CAD reports for failure lessons only.
6. AI images for appearance and chapter orientation only.

## Version-sensitive decisions

- The product name in current Help is **Autodesk Fusion** (formerly Fusion 360).
- New files distinguish Part, Assembly, and Hybrid designs. The beginner route
  uses **File > New > Hybrid Design** so internal components share one parameter
  table and skeleton. The advanced distributed route uses Part + Assembly.
- Use **Parametric Modeling Mode**, not the old “Capture Design History” wording.
- Generic **Ground** is now **Pin**. **Ground To Parent** is a distinct
  child-to-parent relationship.
- Use **Assemble > Drive Joints** or a joint's context menu. Section Analysis is
  a visibility tool; Interference is the current-pose overlap check.
- July 2026 added construction-geometry mirroring and new configuration features,
  but Configurations are not a dependency because Personal Use cannot edit the
  Configuration Table.

## Primary Autodesk sources

- [July 2026 update and v2704.1.23 hotfix](https://www.autodesk.com/products/fusion-360/blog/july-2026-major-product-update-whats-new/)
- [Create Part, Assembly, or Hybrid designs](https://help.autodesk.com/view/fusion360/ENU/?guid=ASM-CREATE-DESIGN)
- [Fusion desktop interface](https://help.autodesk.com/view/fusion360/ENU/?guid=GS-THE-FUSION-INTERFACE)
- [Modeling modes](https://help.autodesk.com/view/fusion360/ENU/?contextId=DESIGN_HISTORY)
- [Components](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-COMPONENTS.htm)
- [Bodies](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/GUID-C1AB4941-D7AD-4D27-A035-2FA9208635B6.htm)
- [Parameters](https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-MODIFY-PARAMETERS.htm)
- [Fully constrain sketches](https://help.autodesk.com/cloudhelp/ENU/Fusion-Sketch/files/SKT-FULLY-DEFINE-CONSTRAIN-SKETCH.htm)
- [Project geometry](https://help.autodesk.com/cloudhelp/ENU/Fusion-Sketch/files/GUID-850061C4-71F5-4418-AF9C-F0D232022F9C.htm)
- [Assembly relationships](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-JOINTS.htm)
- [Joint origins](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-JOINT-ORIGIN.htm)
- [Joint limits](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/GUID-543C82D9-F1E8-42B3-9C34-31BB108AFAA3.htm)
- [Duplicate With Joints](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-DUPLICATE-WITH-JOINTS.htm)
- [Ground To Parent and Pin](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-GROUND-TO-PARENT.htm)
- [Contact Sets](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-CONTACT-SETS.htm)
- [Interference](https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/GUID-A6629113-B137-4EDE-B3B2-C9F1F3BA83D1.htm)
- [3D Print / 3MF, STL, OBJ](https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-3D-PRINT.htm)
- [Drawing From Design](https://help.autodesk.com/cloudhelp/ENU/Fusion-Drawing/files/DWG-CREATE-FROM-DESIGN.htm)
- [Personal Use comparison](https://www.autodesk.com/products/fusion-360/personal/compare)

Autodesk Help pages commonly state CC BY-NC-SA 3.0 in their footer. The HTML
guide links rather than republishing most UI media, and attributes every linked
Autodesk illustration. Re-check licensing before commercial redistribution.

## Poster corrections

| Poster claim | Current guide position |
|---|---|
| Body diameter 220 mm | `body_dia = 180 mm` |
| 110/130 or 90/70 mm two-link leg | q1 offset 32, femur 110, tibia 70, plus driven wheel |
| Four equal 90° mounts | explicit +25, -25, +109, -109 degree origins |
| Foot blocks | 70 mm driven wheels in v1 |
| Hip limits about ±35° | q1 ±60; q2 -35…110; q3 ±135 degrees |
| Sketch directly on cylinder front | create a tangent or origin-derived datum plane |
| Generic Ground | Pin base to world; Ground To Parent only for fixed children |
| Inspect > Drive Joint | Assemble > Drive Joints or right-click a joint |
| Section Analysis finds collisions | Section reveals interiors; Interference reports overlap |

## Open engineering decisions

- Exact servo ear, output-axis, auxiliary shaft, horn, bolt-circle, and cable
  dimensions require the received STS3215 and calipers.
- Shell wall, deck/rib strategy, lid interface, handle section, fasteners,
  wheel/tire width, hub stem, bearings, and cable slots are provisional.
- The four fixed radial wheel headings cannot provide ordinary no-slip driving.
  Select scrub/skid, omni/caster, added steering, or adjustable pods before
  freezing wheel and chassis interfaces.
- Rear-leg servo ID order previously conflicted; resolved 2026-07-13 by making
  the hardware export order FL, FR, RR, RL to match the build-phase map.
- The four leg-root signal/power tap topology is not physically resolved.
- Several generator scripts and native CAD artifacts cited by older documents
  are absent from this workspace.
