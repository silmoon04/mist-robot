"""Render the R4 analytical review from exact recorded results."""
from pathlib import Path
import json

OUT=Path(__file__).resolve().parent
r=json.loads((OUT/'r4_strength_results.json').read_text())
r3=json.loads((OUT/'r3_strength_results.json').read_text())
w=r['sampled_walking_screen']
e=r['sliced_mass_evidence']
def result(name,case):
    return next(v for v in r['results'] if v['check']==name and v['case']==case)
def table_row(name,case,label=None):
    v=result(name,case)
    return f"| {label or name} | {v['demand_MPa']:.2f} | {v['allowable_MPa']:.0f} | {v['conditional_margin']:.2f} |"
ordinary='\n'.join(table_row(n,c,l) for n,c,l in [
    ('femur ordinary-walk sagittal envelope','sampled R4 walking','Femur, sampled sagittal envelope'),
    ('tibia ordinary-walk sagittal envelope','sampled R4 walking','Tibia, sampled sagittal envelope'),
    ('Post vertical-only equal 4-foot support','ordinary 1g reference','Post, equal four-foot vertical 1g'),
    ('Post vertical-only equal 3-foot support','ordinary 1g reference','Post, equal three-foot vertical 1g'),
    ('Post sampled vertical-only envelope','sampled R4 walking','Post, maximum sampled vertical force'),
    ('Post entire torque-cap allocation','separate torque allocation bound','Post, entire 0.588 Nm hypothetically allocated'),
    ('Post sampled entire hip-torque allocation','sampled torque allocation bound','Post, entire sampled hip torque hypothetically allocated')])
shock='\n'.join(table_row(n,'R4 sliced mass 2g') for n in ['Yaw lower arm','femur_bridge','tibia_bridge','Coxa post scanned','Horn group bearing','External washer face punching shear','Auxiliary access-hole ligament reference shear'])
comparison=[]
for label in ('femur','tibia'):
    a=r3['sections'][label]['section_modulus_transverse_mm3']
    b=r['sections'][label]['section_modulus_transverse_mm3']
    comparison.append(f"| {label} at x={r['sections'][label]['cut_mm']:.0f} | {a[0]:.1f} | {b[0]:.1f} | {a[1]:.1f} | {b[1]:.1f} |")
comparison='\n'.join(comparison)
text=f"""R4's sampled walking loads remain below the provisional sagittal-section limits in this calculation. The corresponding conditional margins are {w['femur']['conditional_margin']:.2f} for the femur and {w['tibia']['conditional_margin']:.2f} for the tibia. Ordinary vertical post loads also have a margin above one. The independent 5 N lateral disturbance, full motor-torque allocation to the post and combined 2g disturbance remain unresolved or below the assumed limit. This supports a controlled fixture and prototype programme, not a printed-strength qualification.

The assessment uses the final R4 inward-knee meshes, {e['production_sku_count']} production SKU slices covering {e['production_piece_count']} pieces, and the R4 nominal trajectory. The assembled toolpath-estimated mass is {r['sliced_total_mass_kg']:.9f} kg: {e['deposited_model_mass_kg']:.6f} kg of printed model material and {e['retained_nonprinted_mass_kg']:.6f} kg of nonprinted parts and allowances. Removable support, estimated at {e['support_mass_excluded_kg']*1000:.2f} g, and adhesion material are excluded. The full-solid comparison is {r['solid_total_mass_kg']:.6f} kg. These are calculated masses, not weighed parts.

reassess_r4.py checks that the CAD sources match the export, that all slice SKUs and the solid-manifest hash match, and that the printed manifest and simulation refer to the same inputs. Exact source, mesh, deposition, printed-manifest and trajectory hashes are recorded in r4_strength_results.json. R3 results are preserved separately. The old R2 load envelope is retained for comparison; it is not silently replaced with a new acceptance criterion.

The method is polygon integration on actual STL sections, followed by beam bending, net-area, projected bearing and reference shear calculations. It includes section holes, cable scallops and product inertia. It is not anisotropic finite element analysis, an extrusion-road failure model or a simulation of delamination. The material assumptions remain 12 MPa in-plane tension, 4 MPa layer-normal tension, 3 MPa shear and 8 MPa projected bearing, with a notch factor of 2 and effective section factor of 0.5. Thus the reported demand is four times nominal solid-section stress. These are empirical-data-informed engineering assumptions for short-duration room-temperature loading, not measured allowables for this spool.

Prusa reports 17 +/- 3 MPa interlayer adhesion using its own method and 51 +/- 3 MPa horizontal tensile yield for its printed PLA specimens. Those specimens used 0.20 mm layers and 100% rectilinear infill. They do not directly characterize Neptune 4 Pro prints with 35% gyroid. Its 55 C heat-deflection result is also not a service-temperature rating for the robot. [Prusament PLA technical data sheet](https://prusament.com/wp-content/uploads/2022/10/PLA_Prusament_TDS_2021_10_EN.pdf).

The ordinary-walk screen applies each sampled hip or knee torque without attenuation to every scanned main-cheek section and conservatively adds the same-frame foot normal as a full axial force. Its equation is demand = 4 times (1000 times absolute torque divided by sagittal section modulus plus absolute foot normal divided by section area), using N, mm and MPa. This is a sagittal load proxy, not reconstructed three-dimensional joint stress. No auxiliary load sharing is invented. Femur demand peaks on {w['femur']['leg']} at {w['femur']['time_s']:.2f} s, x={w['femur']['cut_x_mm']:.1f}, using {w['femur']['joint_torque_Nm']:.5f} Nm and {w['femur']['foot_normal_N']:.2f} N. Tibia demand peaks on {w['tibia']['leg']} at {w['tibia']['time_s']:.2f} s, x={w['tibia']['cut_x_mm']:.1f}, using {w['tibia']['joint_torque_Nm']:.5f} Nm and {w['tibia']['foot_normal_N']:.2f} N.

| Screen | Demand MPa | Assumed allowable MPa | Conditional margin |
| --- | ---: | ---: | ---: |
{ordinary}

The last two rows deliberately ask a different question from the vertical-only rows. They assign the entire hip reaction torque to post bending. The actual hip saddle also connects directly to the upper yaw plate, above the low post section. That parallel path makes a full-post torque allocation an unvalidated bound. It must not be added to the vertical result and presented as measured post stress. Conversely, the vertical-only result does not establish the real frame's combined strength. The fixture must determine how the upper plate, lower arm, post, horn and auxiliary disc share reversing loads.

The corrected clamp datum and reopened screw access remove real material from the continuous post near z=-25. The net section there is 124.53 mm2, with section modulus about Y of 140.70 mm3. This is not a disconnected rib remnant. The image below shows an exact mesh projection and section, with no stress heatmap or invented reactions.

![R4 post projection and actual access-cut section]({(OUT/'r4_post_section.png').as_posix()})

The current staggered-nut coupon stops at z=-28 and misses this access cut. Treat it as a nut-window and assembly specimen only. The load fixture must include the complete production coxa, its upper yaw plate, lower arm, actual spacers and fasteners. Apply vertical force at the hip saddle near x=50 relative to the post near x=32, then independently apply reversing reaction torque about Y. Compare an isolated post bound with the assembled frame response. No geometry change was made during this assessment: the ordinary vertical-load margin does not by itself justify redesigning the assembly for the separate unrequired shock case.

The femur bridge is now above the inward-facing knee case, within x=58..72 and z=13.5..27.5. Its extracted bending section modulus is {r['sections']['femur_bridge']['section_modulus_transverse_mm3'][0]:.1f} mm3, including chamfers and its screw passage. The R3 value was {r3['sections']['femur_bridge']['section_modulus_transverse_mm3'][0]:.1f} mm3. The bridge remains a 38 mm clear transverse span for this calculation. The tibia bridge geometry retains the reinforced 16 by 13 mm envelope. The 9 mm yaw lower arm, external bridge nuts and full 4 mm washer-bearing cheeks remain in place.

Cable and servo clearance removes some inward rib depth. Selected-section comparisons show why the R3 stiffness improvement cannot simply be carried forward:

| Section | R3 sagittal modulus mm3 | R4 sagittal modulus mm3 | R3 lateral modulus mm3 | R4 lateral modulus mm3 |
| --- | ---: | ---: | ---: | ---: |
{comparison}

Under the independent one-cheek bound of 588 Nmm sagittal plus 500 Nmm lateral moment, the longitudinal scan reaches {r['worst_cheek_sections']['femur']['screening_demand_MPa']:.2f} MPa at femur x={r['worst_cheek_sections']['femur']['cut_mm']:.1f} and {r['worst_cheek_sections']['tibia']['screening_demand_MPa']:.2f} MPa at tibia x={r['worst_cheek_sections']['tibia']['cut_mm']:.1f}. The new asymmetric rib remnants amplify these section-extreme values. Evaluating the original 4 mm cheek-core corners under the same section centroid and inertia gives approximately {r['worst_cheek_sections']['femur']['core_corner_frozen_envelope_MPa']:.2f} and {r['worst_cheek_sections']['tibia']['core_corner_frozen_envelope_MPa']:.2f} MPa. Therefore the maxima are not proof that the entire section breaks at a rib-tip stress, but the independent one-cheek bound remains unmet even on core material. This 5 N disturbance is not an observed force in the nominal trajectory and is not a whole-leg allowable.

The auxiliary cable scallops were scanned separately. Outside the horn load-introduction region, the smallest net auxiliary areas are {r['worst_auxiliary_sections']['femur']['area_mm2']:.2f} mm2 at femur x={r['worst_auxiliary_sections']['femur']['cut_mm']:.1f} and {r['worst_auxiliary_sections']['tibia']['area_mm2']:.2f} mm2 at tibia x={r['worst_auxiliary_sections']['tibia']['cut_mm']:.1f}. Full per-leg axial-force screens remain below the assumed in-plane limit, but that does not check local bending, torsion or contact. The 7.8 mm centre access leaves a nominal 1.4 mm web to each adjacent 3.4 mm hole on the 14 mm PCD. A reference shear calculation uses one quarter of the leg force on two such webs; no actuator torque is assigned to the auxiliary disc. The actual hole-edge force direction, printed standoff compression and screw preload still need testing. Do not tighten against a guessed torque.

The independent printed-mass two-leg 2g case applies {r['sliced_total_mass_kg']*9.81:.2f} N per leg. Where stated in the JSON, it also adds the fixed 5 N side-force term. The resulting checks are:

| Screen | Demand MPa | Assumed allowable MPa | Conditional margin |
| --- | ---: | ---: | ---: |
{shock}

The post and horn bearing do not pass that combined disturbance screen. The lower arm and phone spine have little reserve against the provisional assumptions. These findings belong in the prototype limitations; a gait pass cannot erase them. Complete frozen-R2, full-solid and printed-mass cases remain in the JSON.

The phone's moving rear frame still has actual 6 by 8 mm USB spines. A 5 N top push split between two columns gives a scanned maximum of 10.99 MPa near z=44.2, conditional margin 1.09. The 12 by 8 mm rear top bridge gives 3.87 MPa for the horizontal midpoint push, and the two short lower corner clips give 7.45 MPa under a distributed pane push. No centre load is applied to the absent front bar. R4's fixed pan clamp now follows the corrected supplier envelope and has revised retaining ledges and cable access. The cover receives a matching cable opening and improved support geometry under its fixing bosses. Fit and printability improvements are not plate-strength validation: the fixed clamp lips, cover opening, deck ligaments, battery tabs and pan mounting group still require an assembled fixture check. No new global body or phone-mount strength pass is claimed.

Printing orientation remains mechanically relevant. Main and auxiliary cheeks place long XZ bending fibres in the bed plane. Assembly-Y cross bridges can develop tension normal to layers, so the weaker 4 MPa assumption is retained there. Main rib clearance and auxiliary scallops must be inspected in the slice; their thin residual features should not be counted as a perfectly bonded box. Five walls alone do not fill a flat cheek through build Z. Check the intended solid top and bottom skins, support interfaces, bridge roots and hole contours in the actual toolpaths. The deposition-derived mass is not substituted for effective section stiffness or interlayer strength.

Prioritise three fixture observations before changing geometry again: post load sharing with the access cut present, reversing side-load compliance of the assembled two-cheek leg, and the phone frame's USB-spine response with a dummy phone. Begin below the relevant bound, record applied force or moment, displacement, twist, cracking and residual set, and increase load only on captured sacrificial specimens. The upper bridge must be tested in its production layer orientation with the real auxiliary fastener retained. Separate vertical and torque tests before attempting combined load. The hardware fixture guide explicitly distinguishes the cropped nut coupon from the full coxa needed for the critical access section.

PLA creep and clamp relaxation are still unvalidated. Hold working load for an hour and a day, inspect nut movement and permanent set, and repeat at the measured servo-adjacent temperature before sustained standing. [Stress Relaxation Behavior of Additively Manufactured PLA](https://www.mdpi.com/1996-1944/15/10/3509) and [Effect of physical aging on flexural creep in printed thermoplastic](https://arxiv.org/abs/2302.11240) provide primary experimental context. No warm allowable, fatigue life, buckling qualification or long-term robot load rating has been established.

Keep future lightening away from bridges, rib transitions, the access-cut post and fastener lands until those observations exist. Larger panel regions might later be pocketed or ribbed, but the cover carries the phone and the deck carries yaw reactions around openings. Compare mass saved, centre of mass, actuator torque and measured fixture stiffness together. The current result is an analytical basis for controlled physical validation, not permission to treat the robot as structurally qualified.
"""
(OUT/'r4_strength_assessment.md').write_text(text,encoding='utf-8')
(OUT/'r4_strength_assessment.txt').write_text(text,encoding='utf-8')
print('Wrote R4 report and text companion.')
