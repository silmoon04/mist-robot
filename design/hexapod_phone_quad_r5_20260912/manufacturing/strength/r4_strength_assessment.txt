R4's sampled walking loads remain below the provisional sagittal-section limits in this calculation. The corresponding conditional margins are 3.19 for the femur and 1.35 for the tibia. Ordinary vertical post loads also have a margin above one. The independent 5 N lateral disturbance, full motor-torque allocation to the post and combined 2g disturbance remain unresolved or below the assumed limit. This supports a controlled fixture and prototype programme, not a printed-strength qualification.

The assessment uses the final R4 inward-knee meshes, 34 production SKU slices covering 76 pieces, and the R4 nominal trajectory. The assembled toolpath-estimated mass is 2.748543714 kg: 1.047638 kg of printed model material and 1.700905 kg of nonprinted parts and allowances. Removable support, estimated at 50.96 g, and adhesion material are excluded. The full-solid comparison is 2.911449 kg. These are calculated masses, not weighed parts.

reassess_r4.py checks that the CAD sources match the export, that all slice SKUs and the solid-manifest hash match, and that the printed manifest and simulation refer to the same inputs. Exact source, mesh, deposition, printed-manifest and trajectory hashes are recorded in r4_strength_results.json. R3 results are preserved separately. The old R2 load envelope is retained for comparison; it is not silently replaced with a new acceptance criterion.

The method is polygon integration on actual STL sections, followed by beam bending, net-area, projected bearing and reference shear calculations. It includes section holes, cable scallops and product inertia. It is not anisotropic finite element analysis, an extrusion-road failure model or a simulation of delamination. The material assumptions remain 12 MPa in-plane tension, 4 MPa layer-normal tension, 3 MPa shear and 8 MPa projected bearing, with a notch factor of 2 and effective section factor of 0.5. Thus the reported demand is four times nominal solid-section stress. These are empirical-data-informed engineering assumptions for short-duration room-temperature loading, not measured allowables for this spool.

Prusa reports 17 +/- 3 MPa interlayer adhesion using its own method and 51 +/- 3 MPa horizontal tensile yield for its printed PLA specimens. Those specimens used 0.20 mm layers and 100% rectilinear infill. They do not directly characterize Neptune 4 Pro prints with 35% gyroid. Its 55 C heat-deflection result is also not a service-temperature rating for the robot. [Prusament PLA technical data sheet](https://prusament.com/wp-content/uploads/2022/10/PLA_Prusament_TDS_2021_10_EN.pdf).

The ordinary-walk screen applies each sampled hip or knee torque without attenuation to every scanned main-cheek section and conservatively adds the same-frame foot normal as a full axial force. Its equation is demand = 4 times (1000 times absolute torque divided by sagittal section modulus plus absolute foot normal divided by section area), using N, mm and MPa. This is a sagittal load proxy, not reconstructed three-dimensional joint stress. No auxiliary load sharing is invented. Femur demand peaks on FL at 50.95 s, x=11.0, using 0.48042 Nm and 11.71 N. Tibia demand peaks on RR at 47.10 s, x=35.0, using 0.53299 Nm and 12.73 N.

| Screen | Demand MPa | Assumed allowable MPa | Conditional margin |
| --- | ---: | ---: | ---: |
| Femur, sampled sagittal envelope | 3.76 | 12 | 3.19 |
| Tibia, sampled sagittal envelope | 8.91 | 12 | 1.35 |
| Post, equal four-foot vertical 1g | 3.45 | 12 | 3.48 |
| Post, equal three-foot vertical 1g | 4.60 | 12 | 2.61 |
| Post, maximum sampled vertical force | 6.79 | 12 | 1.77 |
| Post, entire 0.588 Nm hypothetically allocated | 16.72 | 12 | 0.72 |
| Post, entire sampled hip torque hypothetically allocated | 13.66 | 12 | 0.88 |

The last two rows deliberately ask a different question from the vertical-only rows. They assign the entire hip reaction torque to post bending. The actual hip saddle also connects directly to the upper yaw plate, above the low post section. That parallel path makes a full-post torque allocation an unvalidated bound. It must not be added to the vertical result and presented as measured post stress. Conversely, the vertical-only result does not establish the real frame's combined strength. The fixture must determine how the upper plate, lower arm, post, horn and auxiliary disc share reversing loads.

The corrected clamp datum and reopened screw access remove real material from the continuous post near z=-25. The net section there is 124.53 mm2, with section modulus about Y of 140.70 mm3. This is not a disconnected rib remnant. The image below shows an exact mesh projection and section, with no stress heatmap or invented reactions.

![R4 post projection and actual access-cut section](/design/hexapod_phone_quad_20260912/manufacturing/strength/r4_post_section.png)

The current staggered-nut coupon stops at z=-28 and misses this access cut. Treat it as a nut-window and assembly specimen only. The load fixture must include the complete production coxa, its upper yaw plate, lower arm, actual spacers and fasteners. Apply vertical force at the hip saddle near x=50 relative to the post near x=32, then independently apply reversing reaction torque about Y. Compare an isolated post bound with the assembled frame response. No geometry change was made during this assessment: the ordinary vertical-load margin does not by itself justify redesigning the assembly for the separate unrequired shock case.

The femur bridge is now above the inward-facing knee case, within x=58..72 and z=13.5..27.5. Its extracted bending section modulus is 438.4 mm3, including chamfers and its screw passage. The R3 value was 409.7 mm3. The bridge remains a 38 mm clear transverse span for this calculation. The tibia bridge geometry retains the reinforced 16 by 13 mm envelope. The 9 mm yaw lower arm, external bridge nuts and full 4 mm washer-bearing cheeks remain in place.

Cable and servo clearance removes some inward rib depth. Selected-section comparisons show why the R3 stiffness improvement cannot simply be carried forward:

| Section | R3 sagittal modulus mm3 | R4 sagittal modulus mm3 | R3 lateral modulus mm3 | R4 lateral modulus mm3 |
| --- | ---: | ---: | ---: | ---: |
| femur at x=40 | 996.1 | 1110.2 | 118.3 | 120.4 |
| tibia at x=30 | 456.3 | 320.0 | 105.4 | 56.9 |

Under the independent one-cheek bound of 588 Nmm sagittal plus 500 Nmm lateral moment, the longitudinal scan reaches 46.18 MPa at femur x=34.5 and 61.78 MPa at tibia x=31.5. The new asymmetric rib remnants amplify these section-extreme values. Evaluating the original 4 mm cheek-core corners under the same section centroid and inertia gives approximately 20.72 and 33.52 MPa. Therefore the maxima are not proof that the entire section breaks at a rib-tip stress, but the independent one-cheek bound remains unmet even on core material. This 5 N disturbance is not an observed force in the nominal trajectory and is not a whole-leg allowable.

The auxiliary cable scallops were scanned separately. Outside the horn load-introduction region, the smallest net auxiliary areas are 61.47 mm2 at femur x=13.0 and 53.79 mm2 at tibia x=56.0. Full per-leg axial-force screens remain below the assumed in-plane limit, but that does not check local bending, torsion or contact. The 7.8 mm centre access leaves a nominal 1.4 mm web to each adjacent 3.4 mm hole on the 14 mm PCD. A reference shear calculation uses one quarter of the leg force on two such webs; no actuator torque is assigned to the auxiliary disc. The actual hole-edge force direction, printed standoff compression and screw preload still need testing. Do not tighten against a guessed torque.

The independent printed-mass two-leg 2g case applies 26.96 N per leg. Where stated in the JSON, it also adds the fixed 5 N side-force term. The resulting checks are:

| Screen | Demand MPa | Assumed allowable MPa | Conditional margin |
| --- | ---: | ---: | ---: |
| Yaw lower arm | 11.12 | 12 | 1.08 |
| femur_bridge | 2.34 | 4 | 1.71 |
| tibia_bridge | 2.42 | 4 | 1.65 |
| Coxa post scanned | 17.29 | 12 | 0.69 |
| Horn group bearing | 8.16 | 8 | 0.98 |
| External washer face punching shear | 1.55 | 3 | 1.94 |
| Auxiliary access-hole ligament reference shear | 2.41 | 3 | 1.25 |

The post and horn bearing do not pass that combined disturbance screen. The lower arm and phone spine have little reserve against the provisional assumptions. These findings belong in the prototype limitations; a gait pass cannot erase them. Complete frozen-R2, full-solid and printed-mass cases remain in the JSON.

The phone's moving rear frame still has actual 6 by 8 mm USB spines. A 5 N top push split between two columns gives a scanned maximum of 10.99 MPa near z=44.2, conditional margin 1.09. The 12 by 8 mm rear top bridge gives 3.87 MPa for the horizontal midpoint push, and the two short lower corner clips give 7.45 MPa under a distributed pane push. No centre load is applied to the absent front bar. R4's fixed pan clamp now follows the corrected supplier envelope and has revised retaining ledges and cable access. The cover receives a matching cable opening and improved support geometry under its fixing bosses. Fit and printability improvements are not plate-strength validation: the fixed clamp lips, cover opening, deck ligaments, battery tabs and pan mounting group still require an assembled fixture check. No new global body or phone-mount strength pass is claimed.

Printing orientation remains mechanically relevant. Main and auxiliary cheeks place long XZ bending fibres in the bed plane. Assembly-Y cross bridges can develop tension normal to layers, so the weaker 4 MPa assumption is retained there. Main rib clearance and auxiliary scallops must be inspected in the slice; their thin residual features should not be counted as a perfectly bonded box. Five walls alone do not fill a flat cheek through build Z. Check the intended solid top and bottom skins, support interfaces, bridge roots and hole contours in the actual toolpaths. The deposition-derived mass is not substituted for effective section stiffness or interlayer strength.

Prioritise three fixture observations before changing geometry again: post load sharing with the access cut present, reversing side-load compliance of the assembled two-cheek leg, and the phone frame's USB-spine response with a dummy phone. Begin below the relevant bound, record applied force or moment, displacement, twist, cracking and residual set, and increase load only on captured sacrificial specimens. The upper bridge must be tested in its production layer orientation with the real auxiliary fastener retained. Separate vertical and torque tests before attempting combined load. The hardware fixture guide explicitly distinguishes the cropped nut coupon from the full coxa needed for the critical access section.

PLA creep and clamp relaxation are still unvalidated. Hold working load for an hour and a day, inspect nut movement and permanent set, and repeat at the measured servo-adjacent temperature before sustained standing. [Stress Relaxation Behavior of Additively Manufactured PLA](https://www.mdpi.com/1996-1944/15/10/3509) and [Effect of physical aging on flexural creep in printed thermoplastic](https://arxiv.org/abs/2302.11240) provide primary experimental context. No warm allowable, fatigue life, buckling qualification or long-term robot load rating has been established.

Keep future lightening away from bridges, rib transitions, the access-cut post and fastener lands until those observations exist. Larger panel regions might later be pocketed or ribbed, but the cover carries the phone and the deck carries yaw reactions around openings. Compare mass saved, centre of mass, actuator torque and measured fixture stiffness together. The current result is an analytical basis for controlled physical validation, not permission to treat the robot as structurally qualified.
