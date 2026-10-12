R5 strength review focuses on the longer inward hip mounting and the straight 105 mm lower leg. Actual mesh sections and the available final load data are used below. The result is a conditional engineering screen, not printed-strength validation or anisotropic finite element analysis. R4 geometry and results were not edited.

The current assembly mass is 2.756961897 kg (toolpath-estimated assembly); the full-solid comparison is 2.936135 kg. All 34 production SKUs, covering 76 pieces, are included. Model deposition contributes 1.056056 kg; 55.83 g of removable support and all bed adhesion are excluded from assembly mass. Source CAD, exported meshes, slice coverage, printed-manifest provenance and simulation input hashes are checked by reassess_r5.py and recorded in r5_strength_results.json. These masses are toolpath and hardware estimates, not weighed parts.

The same provisional assumptions are retained: 12 MPa in-plane tension, 4 MPa layer-normal tension, 3 MPa shear and 8 MPa projected bearing; notch factor 2 and effective section factor 0.5. Reported demand is four times nominal solid-section stress. The assumptions apply to short-duration loading near room temperature. They are not certified values for the user's PLA spool or an automatic conversion of 35% gyroid to strength.

Prusa's PLA data sheet distinguishes 17 +/- 3 MPa interlayer adhesion from 51 +/- 3 MPa horizontal printed tensile yield. Its printed specimens used 0.20 mm layers and 100% rectilinear infill, so those values cannot directly qualify this printer and infill profile. [Prusament PLA technical data sheet](https://prusament.com/wp-content/uploads/2022/10/PLA_Prusament_TDS_2021_10_EN.pdf).

The yaw-to-hip distance is now 70.0 mm. The old 18 mm post eccentricity is therefore not reused. Every horizontal post section uses its own centroid, with lever equal to hip X minus section-centroid X. The vertical-load equation is 4 times F times (1/A plus lever/Z), including axial force as well as bending. It deliberately assigns the full leg vertical force to the post; the direct hip-saddle-to-upper-plate route is not credited as a fixed load share.

The candidate review found a local weakness where a nut window and opposite cap-access scallop met below the first flange termination at z=-34. The existing triangular inward flange was extended to z=-44, onto the lower arm, rather than moving the case or fasteners. The final ordinary-reference governing section has area 170.00 mm2 and bending modulus about Y of 229.04 mm3 at z=-23.00. Its hip-to-centroid lever is 42.04 mm. This preserves a continuous load path past the lower windows, subject to the separate fit and motion checks.

The tibia's second printed part is a short auxiliary bearing cheek, not another serial leg segment. The main load-bearing shank remains centred on the straight knee-to-toe axis. The transverse bridge lies at x=32..48, z=-7..7 with bolts at x=36 and 44, z=0. Its actual net bending modulus is 493.56 mm3, including the two screw passages and corner chamfers. Each bolt retains a 4 mm centre-to-edge distance and 2.3 mm nominal material beyond its 3.4 mm hole. The full 4 mm cheek remains under the external washer and nut. No additional fillet benefit is assumed.

At x=80 the straight shank has area 224.26 mm2, sagittal section modulus 598.72 mm3 and lateral modulus 523.27 mm3. The centred, 14 mm wide taper avoids the former curved-shank eccentricity. It does not make the thin root cheek or its joint connections immune to lateral load.

Ordinary-load results are shown separately from disturbance and torque-allocation bounds:

| Screen | Demand MPa | Assumed allowable MPa | Conditional margin |
| --- | ---: | ---: | ---: |
| Post equal 4-foot vertical support | 5.12 | 12 | 2.34 |
| Post equal 3-foot vertical support | 6.83 | 12 | 1.76 |
| femur sampled sagittal root | 4.45 | 12 | 2.70 |
| tibia sampled sagittal root | 7.06 | 12 | 1.70 |
| Post sampled vertical and axial envelope | 10.09 | 12 | 1.19 |
| Straight shank normal-contact beam screen | 1.06 | 12 | 11.28 |

The femur root screen is governed by FL at 50.85 s, x=11.0 mm, with 0.57929 Nm and 11.64 N. The tibia root screen is governed by FR at 40.10 s, x=17.5 mm, with 0.48362 Nm and 12.82 N. The post vertical envelope uses 13.31 N at 54.40 s on RR; its governing cut is z=-23.00 mm. The normal-contact shank screen is governed at x=71.0 mm on RR at 58.00 s.

For the root cheeks, the same-frame sampled hip or knee torque is applied without attenuation across the scanned root sections, and full foot normal is added as axial force. The equation is 4 times (1000 times absolute torque/Z plus absolute normal force/A). This is a sagittal-demand proxy, not a reconstruction of complete joint stress. The auxiliary cheek is not treated as perfectly bonded to the main part.

For the centred shank beyond x=51, the normal-contact force is rotated into the actual tibia frame using the sampled base orientation and joint angles. Moments are calculated about each section from the 105 mm toe point, then axial and two bending contributions are screened. Tangential friction forces, distal self-inertia and bead damage are not included. The shank result therefore has a narrower meaning than a complete dynamic stress solution.

The following remain independent reference cases. A conditional margin below one means that the assumed limit is exceeded in that reference case; it is not proof that the complete robot fails at a reported section stress:

| Screen | Demand MPa | Assumed allowable MPa | Conditional margin |
| --- | ---: | ---: | ---: |
| Post entire torque-cap allocation | 10.27 | 12 | 1.17 |
| femur one-cheek disturbance | 46.18 | 12 | 0.26 |
| tibia one-cheek disturbance | 43.24 | 12 | 0.28 |
| femur_bridge transverse bending | 2.34 | 4 | 1.71 |
| tibia_bridge transverse bending | 2.08 | 4 | 1.92 |
| Post vertical shock reference | 20.49 | 12 | 0.59 |

The 5 N side-force case assigns 500 Nmm lateral moment and 588 Nmm sagittal moment to a single main cheek throughout the root scan. It is not an observed force from the walking trajectory and is not a whole-leg allowable. The separate post torque row hypothetically assigns the entire 0.588 Nm to the post. In the real frame the upper yaw plate and lower arm also carry reaction, so that allocation needs a fixture measurement. Do not add these independent rows and present the sum as measured robot stress. The two-leg 2g rows are retained as proof-test references; equal two-foot support is not a stable gait.

Broad-cheek printing places the long XZ bending fibres within the layer plane. The integral transverse bridge runs along assembly Y and can develop layer-normal bending tension, so the weaker 4 MPa assumption remains appropriate for that screen. The centred shank starts above the main cheek's bed plane and needs verified support. Inspect the bridge root, support-removal surface, washer lands and hole contours in the actual slice. Five perimeters alone do not fill the cheek through build Z; solid top and bottom skins still matter. Deposited mass fraction is not substituted for stiffness or layer adhesion.

Keep physical validation focused. Test the full production coxa with upper plate, lower arm, extended flange, clamp fasteners and both nut windows present. Load the hip vertically at its actual X location, then test reversing torque separately to measure frame sharing. Test the short tibia fork with the real auxiliary disc, bridge bolts and spacers retained, first in sagittal bending and then in both lateral directions. Use captured sacrificial parts, incremental force and a dummy payload; record deflection, twist, cracking and residual set. A cropped fit coupon cannot qualify a load path it omits.

The phone, cover, deck and other structures outside this focused leg assessment are not newly qualified. The final deck clearance relief is included in mass and provenance, but no global deck stress analysis is claimed. Existing marginal phone-spine and bearing cases remain relevant unless separately resolved. Check screw engagement and clamp retention without a guessed tightening torque. PLA creep and relaxation require sustained-load observations and testing at measured servo-adjacent temperature before prolonged standing. [Stress Relaxation Behavior of Additively Manufactured PLA](https://www.mdpi.com/1996-1944/15/10/3509) and [Effect of physical aging on flexural creep in printed thermoplastic](https://arxiv.org/abs/2302.11240) provide experimental context. No warm allowable, fatigue life or global printed-strength pass is established here.
