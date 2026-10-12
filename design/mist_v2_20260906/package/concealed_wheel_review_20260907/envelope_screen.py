"""Arithmetic envelope and load screens for the concealed wheel-drive contract.

No CAD or hardware action. Dimensions are millimetres. Housing allowances and
bevel pitch radii below are comparison variables, not a selected gear rating.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    wall, clearance = 1.6, 1.0
    motor_case, shaft_projection, motor_diameter = 61, 12, 25
    module = dict(
        status="proposed_envelope_not_final_CAD_or_purchase",
        coordinates="u down tibia from knee; X in leg plane; Y along wheel axle",
        leading_contract=dict(motor_case_u_mm=[20,81],motor_shaft_u_mm=[81,93],
                              motor_axis_XY_mm=[0,20],wheel_axis_u_mm=130,
                              proposed_shell_X_mm=40,proposed_shell_Y_mm=[65,70]),
        bare_motor_with_shaft_mm=motor_case+shaft_projection,
        longitudinal_section_with_2mm_wall_1mm_gap_mm=motor_diameter+2*(2+1),
        transverse_motor_extent_with_2mm_wall_1mm_gap_mm=motor_case+shaft_projection+2*(2+1),
        encoder_cable_and_bend_envelope_included=False,
        longitudinal_motor_X_mm=[-12.5,12.5],longitudinal_motor_Y_mm=[7.5,32.5],
        existing_tibia_inner_Y_mm=[-16,26],existing_tibia_internal_width_mm=42,
        motor_intrusion_past_existing_positive_inner_wall_mm=32.5-26,
        positive_inner_wall_required_for_1mm_motor_gap_mm=33.5,
        upper_motor_bay_width_with_6mm_cheek_and_1p6mm_covers_mm=(33.5+6+clearance+wall)-(-22-clearance-wall),
        extension_to_wheel_from_motor_shaft_tip_mm=130-93,
        existing_cross_tie_station_u_mm=[48,75],existing_cross_tie_X_mm=[-9,9],
        existing_cross_ties_intersect_motor=True,
        old_wheel_bearing_faces_Y_mm=[[-22,-16],[26,32]],
        old_wheel_bearing_center_span_mm=48,
        tire_faces_Y_mm=[-12,12],old_side_gaps_beside_tire_mm=[4,14],
        example_commercial_pulley_length_mm=[20.6,22],
        pulley_shortfall_in_14mm_side_gap_mm=[20.6-14,22-14],
        example_positive_bearing_center_Y_mm=40,
        example_total_width_with_outward_keeper_head_and_covers_mm=(40+3+2.4+3+clearance+wall)-(-22-clearance-wall),
        cover_pair_mass_g_110x40x1p6_PETG=2*110*40*1.6/1000*1.27,
        removed_old_foot_cradle_print_mass_g=32.19304351829885,
        motor_mass_retained_g=98,
        motor_purchase_confirmed=False,
    )
    # Bevel tangential load and 20-degree, 45-degree-miter force components.
    # Actual vendor geometry/rating remains authoritative.
    rows=[]
    for torque,label in ((.1719,"previous_current_limited_reference"),(1.1768,"stall_reference_not_continuous")):
        for radius in (8,10,12):
            tangential=torque*1000/radius
            side=tangential*math.tan(math.radians(20))/math.sqrt(2)
            rows.append(dict(case=label,torque_Nm=torque,mean_pitch_radius_mm=radius,
                             tangential_N=tangential,radial_N=side,axial_N=side))
    module["illustrative_1to1_miter_loads"]=rows
    module["miter_load_assumptions"]="Straight 20-degree pressure-angle gears with 45-degree pitch cones, using mean pitch radius; no dynamic factors or bearing rating applied."
    module["rough_motor_copper_loss_at_1A_W_from_12V_5p5A_stall"]=12/5.5
    module["thermal_note"]="A rough resistance-derived heat allowance, not a continuous-duty or temperature prediction; brush drop, temperature and gear loss are omitted."
    (HERE/"envelope_screen.json").write_text(json.dumps(module,indent=2)+"\n")
    print(json.dumps(module,indent=2))


if __name__=="__main__":main()
