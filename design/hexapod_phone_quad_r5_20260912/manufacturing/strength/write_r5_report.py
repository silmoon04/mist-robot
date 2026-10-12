"""Render the focused R5 structural screening report."""
from pathlib import Path
import json

OUT=Path(__file__).resolve().parent
r=json.loads((OUT/'r5_strength_results.json').read_text())
rows=r['results']
def find(name):return next(x for x in rows if x['check']==name)
def line(x):return f"| {x['check']} | {x['demand_MPa']:.2f} | {x['allowable_MPa']:.0f} | {x['conditional_margin']:.2f} |"
ordinary='\n'.join(line(x) for x in rows if x['case'] in ('sampled R5 walking','1g reference'))
bounds='\n'.join(line(x) for x in rows if x['case'] not in ('sampled R5 walking','1g reference'))
slice_text='Final slicing has not yet been included.'
if r['slicing']:
    s=r['slicing']
    slice_text=(f"All {s['sku_count']} production SKUs, covering {s['pieces']} pieces, are included. "
                f"Model deposition contributes {s['model_mass_kg']:.6f} kg; "
                f"{s['support_excluded_g']:.2f} g of removable support and all bed adhesion are excluded from assembly mass.")
walking_text='Final R5 walking data have not yet been included; these results are preliminary reference-load calculations.'
if r['walking']:
    parts=[]
    for label in ('femur','tibia'):
        q=r['walking'][label]
        parts.append(f"The {label} root screen is governed by {q['leg']} at {q['time_s']:.2f} s, "
                     f"x={q['section']['cut_mm']:.1f} mm, with {q['torque_Nm']:.5f} Nm and {q['force_N']:.2f} N.")
    q=r['walking']['post']
    parts.append(f"The post vertical envelope uses {q['force_N']:.2f} N at {q['time_s']:.2f} s on {q['leg']}; "
                 f"its governing cut is z={q['section']['cut_mm']:.2f} mm.")
    q=r['walking']['shank']
    parts.append(f"The normal-contact shank screen is governed at x={q['section']['cut_mm']:.1f} mm "
                 f"on {q['leg']} at {q['time_s']:.2f} s.")
    walking_text=' '.join(parts)
post=find('Post equal 3-foot vertical support')['evidence']
body=f"""R5 strength review focuses on the longer inward hip mounting and the straight 105 mm lower leg. Actual mesh sections and the available final load data are used below. The result is a conditional engineering screen, not printed-strength validation or anisotropic finite element analysis. R4 geometry and results were not edited.

The current assembly mass is {r['mass_kg']:.9f} kg ({r['mass_kind']}); the full-solid comparison is {r['solid_mass_kg']:.6f} kg. {slice_text} Source CAD, exported meshes, slice coverage, printed-manifest provenance and simulation input hashes are checked by reassess_r5.py and recorded in r5_strength_results.json. These masses are toolpath and hardware estimates, not weighed parts.

The same provisional assumptions are retained: 12 MPa in-plane tension, 4 MPa layer-normal tension, 3 MPa shear and 8 MPa projected bearing; notch factor 2 and effective section factor 0.5. Reported demand is four times nominal solid-section stress. The assumptions apply to short-duration loading near room temperature. They are not certified values for the user's PLA spool or an automatic conversion of 35% gyroid to strength.

Prusa's PLA data sheet distinguishes 17 +/- 3 MPa interlayer adhesion from 51 +/- 3 MPa horizontal printed tensile yield. Its printed specimens used 0.20 mm layers and 100% rectilinear infill, so those values cannot directly qualify this printer and infill profile. [Prusament PLA technical data sheet](https://prusament.com/wp-content/uploads/2022/10/PLA_Prusament_TDS_2021_10_EN.pdf).

The yaw-to-hip distance is now {r['hip_x_mm']:.1f} mm. The old 18 mm post eccentricity is therefore not reused. Every horizontal post section uses its own centroid, with lever equal to hip X minus section-centroid X. The vertical-load equation is 4 times F times (1/A plus lever/Z), including axial force as well as bending. It deliberately assigns the full leg vertical force to the post; the direct hip-saddle-to-upper-plate route is not credited as a fixed load share.

The candidate review found a local weakness where a nut window and opposite cap-access scallop met below the first flange termination at z=-34. The existing triangular inward flange was extended to z=-44, onto the lower arm, rather than moving the case or fasteners. The final ordinary-reference governing section has area {post['area_mm2']:.2f} mm2 and bending modulus about Y of {post['section_modulus_transverse_mm3'][1]:.2f} mm3 at z={post['cut_mm']:.2f}. Its hip-to-centroid lever is {r['hip_x_mm']-post['centroid_transverse_mm'][0]:.2f} mm. This preserves a continuous load path past the lower windows, subject to the separate fit and motion checks.

The tibia's second printed part is a short auxiliary bearing cheek, not another serial leg segment. The main load-bearing shank remains centred on the straight knee-to-toe axis. The transverse bridge lies at x=32..48, z=-7..7 with bolts at x=36 and 44, z=0. Its actual net bending modulus is {r['sections']['tibia_bridge']['section_modulus_transverse_mm3'][0]:.2f} mm3, including the two screw passages and corner chamfers. Each bolt retains a 4 mm centre-to-edge distance and 2.3 mm nominal material beyond its 3.4 mm hole. The full 4 mm cheek remains under the external washer and nut. No additional fillet benefit is assumed.

At x=80 the straight shank has area {r['sections']['tibia_shank_80']['area_mm2']:.2f} mm2, sagittal section modulus {r['sections']['tibia_shank_80']['section_modulus_transverse_mm3'][0]:.2f} mm3 and lateral modulus {r['sections']['tibia_shank_80']['section_modulus_transverse_mm3'][1]:.2f} mm3. The centred, 14 mm wide taper avoids the former curved-shank eccentricity. It does not make the thin root cheek or its joint connections immune to lateral load.

Ordinary-load results are shown separately from disturbance and torque-allocation bounds:

| Screen | Demand MPa | Assumed allowable MPa | Conditional margin |
| --- | ---: | ---: | ---: |
{ordinary}

{walking_text}

For the root cheeks, the same-frame sampled hip or knee torque is applied without attenuation across the scanned root sections, and full foot normal is added as axial force. The equation is 4 times (1000 times absolute torque/Z plus absolute normal force/A). This is a sagittal-demand proxy, not a reconstruction of complete joint stress. The auxiliary cheek is not treated as perfectly bonded to the main part.

For the centred shank beyond x=51, the normal-contact force is rotated into the actual tibia frame using the sampled base orientation and joint angles. Moments are calculated about each section from the 105 mm toe point, then axial and two bending contributions are screened. Tangential friction forces, distal self-inertia and bead damage are not included. The shank result therefore has a narrower meaning than a complete dynamic stress solution.

The following remain independent reference cases. A conditional margin below one means that the assumed limit is exceeded in that reference case; it is not proof that the complete robot fails at a reported section stress:

| Screen | Demand MPa | Assumed allowable MPa | Conditional margin |
| --- | ---: | ---: | ---: |
{bounds}

The 5 N side-force case assigns 500 Nmm lateral moment and 588 Nmm sagittal moment to a single main cheek throughout the root scan. It is not an observed force from the walking trajectory and is not a whole-leg allowable. The separate post torque row hypothetically assigns the entire 0.588 Nm to the post. In the real frame the upper yaw plate and lower arm also carry reaction, so that allocation needs a fixture measurement. Do not add these independent rows and present the sum as measured robot stress. The two-leg 2g rows are retained as proof-test references; equal two-foot support is not a stable gait.

Broad-cheek printing places the long XZ bending fibres within the layer plane. The integral transverse bridge runs along assembly Y and can develop layer-normal bending tension, so the weaker 4 MPa assumption remains appropriate for that screen. The centred shank starts above the main cheek's bed plane and needs verified support. Inspect the bridge root, support-removal surface, washer lands and hole contours in the actual slice. Five perimeters alone do not fill the cheek through build Z; solid top and bottom skins still matter. Deposited mass fraction is not substituted for stiffness or layer adhesion.

Keep physical validation focused. Test the full production coxa with upper plate, lower arm, extended flange, clamp fasteners and both nut windows present. Load the hip vertically at its actual X location, then test reversing torque separately to measure frame sharing. Test the short tibia fork with the real auxiliary disc, bridge bolts and spacers retained, first in sagittal bending and then in both lateral directions. Use captured sacrificial parts, incremental force and a dummy payload; record deflection, twist, cracking and residual set. A cropped fit coupon cannot qualify a load path it omits.

The phone, cover, deck and other structures outside this focused leg assessment are not newly qualified. The final deck clearance relief is included in mass and provenance, but no global deck stress analysis is claimed. Existing marginal phone-spine and bearing cases remain relevant unless separately resolved. Check screw engagement and clamp retention without a guessed tightening torque. PLA creep and relaxation require sustained-load observations and testing at measured servo-adjacent temperature before prolonged standing. [Stress Relaxation Behavior of Additively Manufactured PLA](https://www.mdpi.com/1996-1944/15/10/3509) and [Effect of physical aging on flexural creep in printed thermoplastic](https://arxiv.org/abs/2302.11240) provide experimental context. No warm allowable, fatigue life or global printed-strength pass is established here.
"""
(OUT/'r5_strength_assessment.md').write_text(body,encoding='utf-8')
(OUT/'r5_strength_assessment.txt').write_text(body,encoding='utf-8')
print('Wrote focused R5 strength report.')
