"""Write the R3 review from the recorded analytical results."""
from pathlib import Path
import json

OUT=Path(__file__).resolve().parent
r=json.loads((OUT/'r3_strength_results.json').read_text())
b=json.loads((OUT/'baseline_r2/strength_results.json').read_text())
sections=r['sections']
mass_text=(f"The complete sliced assembly mass used here is {r['sliced_total_mass_kg']:.6f} kg. "
           if r['sliced_total_mass_kg'] is not None else
           "A complete sliced assembly mass has not yet been supplied to this report. ")
if r.get('sliced_mass_evidence'):
    e=r['sliced_mass_evidence']
    mass_text+=(f"All {e['production_sku_count']} production SKUs and {e['production_piece_count']} pieces are represented: "
                f"{e['deposited_model_mass_kg']:.6f} kg of deposited model material plus "
                f"{e['retained_nonprinted_mass_kg']:.6f} kg of nonprinted parts and allowances. "
                f"The {e['support_mass_excluded_kg']*1000:.2f} g support estimate and all adhesion material are excluded from assembly mass. "
                "The script verifies the slice source manifest hash and exact SKU coverage before accepting the mass. ")
def row(name,case):
    return next(x for x in r['results'] if x['check']==name and x['case']==case)
def compare(label,old_name,new_name):
    old=next(x for x in b['results'] if x['check']==old_name)
    new=row(new_name,'frozen R2 2g')
    return f"| {label} | {old['screening_demand_MPa']:.2f} | {new['demand_MPa']:.2f} | {new['conditional_margin']:.2f} |"
table='\n'.join(compare(*x) for x in [
    ('Yaw lower arm','Yaw lower arm bending','Yaw lower arm'),
    ('Femur cross bridge','Femur cross bridge across layers','femur_bridge'),
    ('Tibia cross bridge','Tibia cross bridge across layers','tibia_bridge'),
    ('Coxa post','Coxa post z-38 combined bending','Coxa post scanned'),
    ('Nut or washer face shear','Nut pocket remaining face punching shear','External washer face punching shear')])
all_rows='\n'.join(f"| {x['check']} | {x['case']} | {x['demand_MPa']:.2f} | {x['allowable_MPa']:.0f} | {x['conditional_margin']:.2f} |" for x in r['results'])
walking_text=''
if r.get('sampled_walking_screen'):
    w=r['sampled_walking_screen']
    walking_text=('The final R3 trajectory also supplies a separate ordinary-walk section screen. '
                  'For every sampled frame and leg, the measured hip or knee torque is applied without attenuation '
                  'to every corresponding scanned main-cheek section. The same-frame foot normal is conservatively '
                  'added as a full axial force. This is a sagittal-demand proxy, not a reconstruction of three-dimensional '
                  'joint reactions. It includes no invented auxiliary load sharing and no assumed 5 N push.\n\n')
    walking_text+=('The screening equation is demand = 4 times (1000 times absolute joint torque divided by '
                   'sagittal section modulus plus absolute foot normal divided by section area), in N, mm and MPa. '
                   'The factor of four is the unchanged notch factor divided by the effective-section factor.\n\n')
    for label,d in w.items():
        walking_text+=(f"The {label} maximum is {d['demand_MPa']:.2f} MPa, conditional margin {d['conditional_margin']:.2f}, "
                       f"at x={d['cut_x_mm']:.1f} on {d['leg']} at {d['time_s']:.2f} s. "
                       f"That frame supplies {d['joint_torque_Nm']:.4f} Nm joint torque and {d['foot_normal_N']:.2f} N foot normal. ")
    walking_text+=('The numerical difference from the fixed disturbance envelope is expected: the 5 N side load was '
                   'an independent design assumption, not an observed force in this trajectory. Neither result supplies '
                   'a whole-leg allowable. Off-axis moments, torsion, bolt preload, layer strength and contact compliance '
                   'remain outside this ordinary-walk proxy.\n\n')
text=f"""R3 reinforces the lower yaw arm, transverse leg bridges, nut-bearing faces and phone frame. Actual mesh section calculations confirm those improvements. The result remains a conditional structural screen: the complete robot has not passed printed strength qualification. Lateral bending near the unreinforced cheek roots, connection compliance and PLA creep still require fixture evidence.

This report evaluates the exported R3 geometry identified by the source hashes in r3_strength_results.json. The R2 files remain unchanged in baseline_r2. {mass_text}The R3 full-solid assembly comparison is {r['solid_total_mass_kg']:.6f} kg, including the current fastener and wiring allowances. Slicer-derived mass affects gravity and inertial loading; it does not establish printed strength or turn gyroid into a homogeneous material.

The frozen R2 envelope remains visible: 2.410992 kg assembly mass, 23.652 N vertical load per leg for two-leg support at 2g, a 5 N side force and a separate 5 N phone push. The recorded R2 trajectory supplied a maximum 11.953 N foot normal and 0.529199 Nm joint torque. A new mass envelope applies F = mass times 9.81 N to each of two legs at 2g. Equal two-leg support is a structural load case, not a stable gait. The rigid-body simulation and its motor limits need their own R3 evaluation.

The calculation uses polygon integration on planes through actual exported STL meshes, with holes and product inertia retained. It applies beam bending, projected bearing and approximate punching shear. It scans the coxa post through both staggered nut windows, the phone spine through the rounded USB opening, and the main cheeks through rib starts. It does not model individual extrusion roads, bolt preload, nonlinear contact, fatigue or delamination. There is no finite element stress contour or bead-level failure prediction.

The same room-temperature assumptions are retained to make the comparison meaningful: 12 MPa in-plane tension, 4 MPa layer-normal tension, 3 MPa shear and 8 MPa hole bearing, a nominal notch factor of 2 and an effective section factor of 0.5. Demand is therefore four times the solid-section nominal stress. These are provisional engineering assumptions, not measured allowables for this spool. Adequate skins, perimeter continuity and layer bonding must be checked. Mass fraction is not substituted for section stiffness.

Prusa's PLA data sheet distinguishes 17 +/- 3 MPa interlayer adhesion from printed horizontal tensile yield of 51 +/- 3 MPa. Its specimens used 0.20 mm layers and 100% rectilinear infill, so its values cannot directly qualify the proposed 35% gyroid Neptune print. The data sheet also gives a 55 C heat deflection result; that is not an acceptable service-temperature limit for these stressed clamps. [Prusament PLA technical data sheet](https://prusament.com/wp-content/uploads/2022/10/PLA_Prusament_TDS_2021_10_EN.pdf).

The measured changes are specific:

* The yaw lower arm at x=20 is now 23 by 9 mm. Its out-of-plane section modulus is {sections['yaw_lower']['section_modulus_transverse_mm3'][0]:.1f} mm3, compared with 61.3 mm3 for R2. The 2.5 mm screw counterbores leave 6.5 mm of thickness. The horn seating and spacer stack must still be checked with hardware.
* The femur bridge occupies a nominal 14 by 14 mm envelope, with chamfered corners and an M3 passage. Its extracted bending section modulus is {sections['femur_bridge']['section_modulus_transverse_mm3'][0]:.1f} mm3. The tibia bridge is 16 by 13 mm, with two bolt passages, and its extracted modulus is {sections['tibia_bridge']['section_modulus_transverse_mm3'][0]:.1f} mm3. The calculation uses the actual voided sections rather than solid rectangles.
* The post has wider lower shoulders and staggered nut windows. Its worst combined-load scan plane occurs at z=-41.25 mm and retains {r['worst_post_sections']['frozen R2 2g']['area_mm2']:.2f} mm2. R2's selected slot plane retained 69.96 mm2. This is a comparison of the recorded critical regions, not a claim that area alone controls bending.
* External bridge nuts and washers replace the 3.2 mm deep recesses in 4 mm cheeks. The original pocket face was 0.8 mm; the updated cheek retains the full 4 mm behind the washer. Tightening preload, nut engagement and washer outside diameter remain physical checks.
* At femur x=40, the inward ribs increase the sagittal section modulus from 623.6 to {sections['femur']['section_modulus_transverse_mm3'][0]:.1f} mm3 and lateral modulus from 81.6 to {sections['femur']['section_modulus_transverse_mm3'][1]:.1f} mm3. At tibia x=30, these rise from 254.3 to {sections['tibia']['section_modulus_transverse_mm3'][0]:.1f} and from 52.1 to {sections['tibia']['section_modulus_transverse_mm3'][1]:.1f} mm3.

Under the same frozen R2 loads:

| Load path | R2 demand MPa | R3 demand MPa | R3 conditional margin |
| --- | ---: | ---: | ---: |
{table}

The main and auxiliary cheeks still print on their broad outer faces. Longitudinal XZ bending fibres therefore lie in the layer plane, while assembly-Y transverse bridges develop layer-normal bending tension. The bridge section increases help that weaker load direction. The inward ribs keep the outer bed faces flat, but auxiliary relief removes some rib material near the horn. No rigid-box action or fixed share of load between cheeks is credited. Full bolt retention and shear-bearing contact would be needed to transfer reversing loads between them.

Five perimeters alone do not fill a flat cheek through its build-Z thickness. The intended 0.20 mm layers should include the specified solid top and bottom skins, with toolpath continuity inspected around holes, bridge roots and rib starts. Unsupported surfaces and removal scars also affect the result. Section factor 0.5 remains conditional even if the measured deposited mass fraction is much higher.

The reinforced x=40 and x=30 sections improve, but they do not define the whole-leg side-load limit. A scan outside the metal horn radius, holding the conservative full moments of 588 Nmm sagittal and 500 Nmm lateral at every section, finds {r['worst_cheek_sections']['femur']['screening_demand_MPa']:.2f} MPa at femur x={r['worst_cheek_sections']['femur']['cut_mm']:.1f} and {r['worst_cheek_sections']['tibia']['screening_demand_MPa']:.2f} MPa at tibia x={r['worst_cheek_sections']['tibia']['cut_mm']:.1f}. The tibia maximum is just before the ribs start. These exceed the assumed 12 MPa allowable. Constant moments form an upper bound rather than an exact local force diagram: actual foot force, joint angle, bridge contact and auxiliary sharing determine the assembled stress. Nevertheless, the selected-section improvements cannot support a claim that the complete leg now withstands a 5 N side push.

At the reinforced tibia x=30 plane, the conditional allowable lateral moment is about 180 Nmm with the full sagittal envelope present. Across the scanned main cheek, it falls to about 43 Nmm near x=24.5. The latter corresponds to approximately 0.43 N on a 100 mm local lever. This is a fixture-planning bound under the stated assumptions, not a hardware walking rating. Even low lateral load can produce torsion through the offset cheek, so a transverse load test must measure twist as well as tip displacement. The R2 single-cheek Euler comparison was only a mode screen; no R3 global or local buckling proof is claimed.

The phone load paths now differ from R2. The lower spanning front bar is absent and is not assigned a centre force. Two separate short clips transfer a 5 N pane push as 2.5 N per clip, conservatively 8.5 mm from its screw. The actual net section through the M3 clearance hole gives {row('Phone short corner clip','5 N pane push via lower clips')['demand_MPa']:.2f} MPa, with conditional margin {row('Phone short corner clip','5 N pane push via lower clips')['conditional_margin']:.2f}. The rear top bridge is an actual 12 by 8 mm section: under an independent 5 N midpoint load across 148.5 mm, horizontal and vertical demands are {row('Phone rear top bridge horizontal','5 N phone push')['demand_MPa']:.2f} and {row('Phone rear top bridge vertical','5 N alternate direction')['demand_MPa']:.2f} MPa. The rear bridge prints inverted, with its longitudinal bending direction within the layer plane.

Each USB spine now retains 6 by 8 mm at the centre of the opening. A scan with 2.5 N acting at the top of each column gives a maximum {r['worst_phone_section']['screening_demand_MPa']:.2f} MPa near z={r['worst_phone_section']['cut_mm']:.1f}, conditional margin {12/r['worst_phone_section']['screening_demand_MPa']:.2f}. The lower part of the opening governs because its lever arm is longer. The earlier 9.01 MPa estimate applied only to the centre plane. The new scan is the value to use. This narrow reserve is a reason for a dummy-phone fixture test; the frame should not be treated as a handle.

The complete numerical results distinguish the unchanged frozen envelope from each mass-dependent case:

{walking_text}

| Check | Load case | Demand MPa | Assumed allowable MPa | Conditional margin |
| --- | --- | ---: | ---: | ---: |
{all_rows}

A margin just above one is not robust to process variation. In particular, the full-solid mass case makes post and horn bearing marginal, and the phone spine has little assumed reserve. Any sliced-mass improvement reduces gravity load, but leaves the fixed 5 N disturbance, screw preload and creep concerns. The body deck, cover panels, battery-tray tabs, original case-cap edge ligaments and pan mounting screw group have not received a new assembly contact or plate-strength validation. No overall manufacturing-strength pass follows from this table.

No broad lightening is recommended before the remaining load paths are measured. The reinforced bridges and necks directly address observed weak sections. Cosmetic cover panels, tray faces and deck regions away from mounts are possible later candidates, but the cover carries the phone and the deck carries the yaw reactions around openings. Preserve ribs and material around fastener lands, cable-slot corners and structural bosses. Judge any future change with sliced mass, centre of mass, actuator torque and fixture deflection together.

For a controlled prototype, first use the R3 bridge, post and USB-spine coupons in their production orientations. Confirm case fit, horn seating, screw engagement and washer access without applying an assumed tightening torque. Apply incremental forces with the part captured in a fixture and a dummy phone. Start below the conservative side-moment bound and record force, deflection, twist and residual set. Increase vertical load toward the actual standing reaction, then toward the frozen 12 N and 24 N targets on sacrificial specimens only. Do not start with the full 5 N lateral target at the same time as the maximum sagittal load.

The next discriminating test is an assembled two-cheek leg fixture with its real horn, auxiliary disc, spacers and fasteners. Test both lateral directions to determine whether the bridges share load or open in reverse, and compare measured compliance with the isolated-cheek bound. A later orthotropic contact FEA can use those measured joint constraints and coupons; assigning perfect bonding now would hide the unresolved mechanism. Only after these checks should a tethered, low-speed level-floor robot test be considered. Gait simulation alone does not authorize a higher structural load envelope.

PLA also relaxes under constant strain and creeps under sustained load. Record clamp movement and deflection after an hour and a day, and repeat at the measured servo-adjacent operating temperature before prolonged standing. Do not extrapolate the room-temperature margins to a warm enclosure. [Stress Relaxation Behavior of Additively Manufactured PLA](https://www.mdpi.com/1996-1944/15/10/3509) and [Effect of physical aging on flexural creep in printed thermoplastic](https://arxiv.org/abs/2302.11240) provide primary experimental context. No fatigue life, warm allowable or long-term load rating has been established here.
"""
(OUT/'r3_strength_assessment.md').write_text(text,encoding='utf-8')
(OUT/'r3_strength_assessment.txt').write_text(text,encoding='utf-8')
print('Wrote R3 strength report and text companion.')
