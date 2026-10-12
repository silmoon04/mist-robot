"""Reviewed motion ownership for legacy parts retained by the proximal recipe.

This table assigns physical motion by part identity. It deliberately does not
fall back to the placement link for an unknown retained part.
"""

RETAINED_GROUPS = {
    'body': (
        'Y01_fixed_mount_bridge',
        'Y12_deck_M4_-25_-22', 'Y13_deck_washer_-25_-22', 'Y14_deck_M4_nut_-25_-22',
        'Y12_deck_M4_-25_22', 'Y13_deck_washer_-25_22', 'Y14_deck_M4_nut_-25_22',
        'Y12_deck_M4_-5_-22', 'Y13_deck_washer_-5_-22', 'Y14_deck_M4_nut_-5_-22',
        'Y12_deck_M4_-5_22', 'Y13_deck_washer_-5_22', 'Y14_deck_M4_nut_-5_22',
        'Y02_608_housing_lower', 'Y03_608_lower', 'Y02_608_housing_upper', 'Y03_608_upper',
        'Y04_fixed_standoff_-11_-8', 'Y04_fixed_standoff_-11_8',
        'Y04_fixed_standoff_11_-8', 'Y04_fixed_standoff_11_8',
        'S01_C018_yaw_CASE', 'Y09_servo_clamp_cap', 'Y10_captured_TPU_pad',
        'Y11_cap_M3_13.6_-25.5', 'Y11_cap_M3_13.6_25.5',
        'Y11_cap_M3_64.73_-12', 'Y11_cap_M3_64.73_12',
    ),
    'yaw': (
        'Y05_metal_yaw_shaft', 'Y06_yaw_output_40T',
        'H01_687_0', 'H02_bearing_tower_0', 'H14_tower_to_coxa_M3_0', 'H15_tower_M3_nut_0',
        'H03_bearing_keeper_0', 'H04_keeper_bolt_0_-9.1', 'H04_keeper_bolt_0_9.1',
        'H01_687_1', 'H02_bearing_tower_1', 'H14_tower_to_coxa_M3_1', 'H15_tower_M3_nut_1',
        'H03_bearing_keeper_1', 'H04_keeper_bolt_1_-9.1', 'H04_keeper_bolt_1_9.1',
        'S02_C018_H_CASE', 'H08_servo_saddle',
        'H11_saddle_to_coxa_M3_-31', 'H11_saddle_to_coxa_M3_-24',
        'H10_servo_clamp_cap', 'H12_captured_TPU_pad',
        'H13_cap_M3_15.5_-95', 'H13_cap_M3_15.5_-67',
        'H13_cap_M3_64.73_-95', 'H13_cap_M3_64.73_-67',
    ),
    'femur': (
        'H05_hip_metal_trunnion', 'H06_output_40T',
        'F01_femur_cheek_drive', 'F01_femur_cheek_belt',
        'F02_femur_cross_spacer_-9_-85', 'F03_femur_tie_-9_-85',
        'F02_femur_cross_spacer_9_-85', 'F03_femur_tie_9_-85',
        'F05_purchased_belt_PITCH_RIBBON',
        'F06_knee_608_0', 'F07_knee_bearing_keeper_0',
        'F08_knee_keeper_M3_0_-13.5', 'F08_knee_keeper_M3_0_13.5',
        'F06_knee_608_1', 'F07_knee_bearing_keeper_1',
        'F08_knee_keeper_M3_1_-13.5', 'F08_knee_keeper_M3_1_13.5',
    ),
    'tibia': (
        'T01_knee_metal_shaft', 'T02_tibia_main_cheek', 'T03_tibia_outer_cheek',
        'T04_tibia_cross_spacer_-9_-48', 'T05_tibia_tie_-9_-48',
        'T04_tibia_cross_spacer_9_-48', 'T05_tibia_tie_9_-48',
        'T04_tibia_cross_spacer_-9_-75', 'T05_tibia_tie_-9_-75',
        'T04_tibia_cross_spacer_9_-75', 'T05_tibia_tie_9_-75',
        'W01_wheel_626_0', 'W01_wheel_626_1', 'W05_FIT0493_motor_CASE',
        'W07_motor_mount_cradle', 'W08_motor_brace_M3_-9', 'W08_motor_brace_M3_9',
    ),
    'wheel': (
        'W02_6mm_wheel_axle', 'W03_wheel_hub', 'W04_tire_ENVELOPE',
        'W06_FIT0493_4mmD_SHAFT', 'W09_6to4mm_coupling_ENVELOPE',
    ),
    'yaw_motor_rotor': ('Y07_yaw_input_20T', 'Y08_factory_horn'),
    'hip_motor_rotor': ('H07_input_20T', 'H09_factory_horn'),
}

RATIONALE = {
    'body':'Fixed deck attachment, yaw bearing outer-race envelope, yaw motor case and case clamping hardware.',
    'yaw':'Yaw output shaft/gear and carriage-side hip bearings, housing and hip motor case.',
    'femur':'Hip output shaft/gear, femur cheeks/ties and knee bearing outer-race envelopes. Belt pitch ribbon follows its supporting femur; circulation is omitted.',
    'tibia':'Knee output shaft, tibia yoke/ties and stationary wheel motor case/cradle/brace/bearing envelopes.',
    'wheel':'Wheel output shaft, hub, tyre, FIT0493 output shaft and direct 1:1 coupler rotate together.',
    'yaw_motor_rotor':'Yaw servo horn and input pinion are an internal rotor, separate from the stationary case.',
    'hip_motor_rotor':'Hip servo horn and input pinion are an internal rotor, separate from the yaw carriage and case.',
    'knee_input_rotor':'PF06 is a rotating shaft, confirmed by its design owner; its input gear, pulley, inner spacers and end retention form one rotor.',
}


def proximal_group_overrides(leg_specs):
    table = {}
    for group,names in RETAINED_GROUPS.items():
        for name in names:
            if name in table:
                raise ValueError('Duplicate reviewed part: '+name)
            table[name] = group
    result = {}
    for spec in leg_specs:
        leg = spec['leg_name']
        by = {part['name']:part for part in spec['parts']}
        if len(by) != len(spec['parts']):
            raise ValueError(leg+': duplicate part names')
        missing = set(table)-set(by)
        if missing:
            raise ValueError(leg+': retained recipe changed; review missing names '+str(sorted(missing)))
        unknown_retained = [name for name in by if name.startswith(('Y','H','F','T','W','S')) and name not in table]
        if unknown_retained:
            raise ValueError(leg+': unreviewed retained parts '+str(unknown_retained))
        for name,group in table.items():
            result[leg+'/'+name] = group
        if 'PF06_input_shaft' not in by:
            raise ValueError(leg+': expected rotating proximal input shaft missing')
        result[leg+'/PF06_input_shaft'] = 'knee_input_rotor'
        for part in spec['parts']:
            if part['name'] not in table and part['name'] != 'PF06_input_shaft' and not part.get('rigid_group'):
                raise ValueError(leg+'/'+part['name']+': new part needs explicit rigid_group')
    return result


def assignment_audit(leg_specs, overrides):
    rows = []
    for spec in leg_specs:
        for part in spec['parts']:
            key = spec['leg_name']+'/'+part['name']
            group = overrides.get(key,part.get('rigid_group'))
            rows.append(dict(part=key,rigid_group=group,placement_or_mass_link=part.get('link'),
                             recipe_rigid_group=part.get('rigid_group'),
                             basis='explicit_identity_override' if key in overrides else 'explicit_new_recipe_group',
                             rationale=RATIONALE.get(group,'New proximal/retention recipe explicitly assigns this physical group.')))
    return rows
