"""Dimensional sensitivities for review, not a strength or print release."""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def cheek(width, thickness=6, web=2.4, rail_width=5):
    extra = thickness-web
    offset = (width-rail_width)/2
    original_area = width*thickness
    original_i = thickness*width**3/12
    revised_area = width*web+2*rail_width*extra
    revised_i = web*width**3/12+2*(extra*rail_width**3/12+rail_width*extra*offset**2)
    return dict(original_area_mm2=original_area,revised_area_mm2=revised_area,
                area_fraction=revised_area/original_area,original_I_mm4=original_i,
                revised_I_mm4=revised_i,I_fraction=revised_i/original_i)


def main():
    femur, tibia = cheek(26), cheek(28)
    saving = (2*70*(femur["original_area_mm2"]-femur["revised_area_mm2"])
              +2*60*(tibia["original_area_mm2"]-tibia["revised_area_mm2"]))*1.27/1000
    m = .055
    results = dict(
        status="ideal_section_and_volume_comparison_not_final_geometry",
        femur_section=femur,tibia_section=tibia,
        cheek_saving_g_if_70mm_femur_and_60mm_tibia_are_modified=saving,
        servo_base_saving_g_53p23x39_from_6_to_3mm=53.23*39*3*1.27/1000,
        servo_cap_saving_g_full_53p23x39x4_to_two_8x39x4_bars=(53.23-16)*39*4*1.27/1000,
        motor_max_added_gravity_moment_Nm_at_40mm=m*9.81*.04,
        motor_added_hip_axis_inertia_kgm2_at_40mm=m*.04**2,
        steel_8mm_shaft_saving_g_per_mm=math.pi*4**2*7.85/1000,
        steel_7mm_shaft_saving_g_per_mm=math.pi*3.5**2*7.85/1000,
        selected_contract=dict(belt_length_mm=375,belt_center_mm=(375-32*3)/2,
                               belt_input_station_down_femur_mm=0,
                               knee_motor_axis_down_femur_mm=30,
                               knee_motor_COM_down_femur_mm=40.115,
                               reducer_teeth=[20,40],remote_pulley_teeth=[32,32],
                               completed_CAD_reviewed=False),
        initial_nonoverlapping_saving_targets_g_per_leg=dict(
            replace_K_subsystem_143p52g_with_105_to_130g=[13.52,38.52],
            remaining_H_servo_mount=[10,14],
            cheek_windows_and_rails=[16,20],
            wheel_cradle=[12,16],
            hub=[5,8],
            root_and_coxa_shorter_load_path=[8,12]))
    targets=results["initial_nonoverlapping_saving_targets_g_per_leg"]
    results["total_target_saving_g_per_leg"]=[sum(v[i] for v in targets.values()) for i in (0,1)]
    (HERE/"section_screen.json").write_text(json.dumps(results,indent=2)+"\n")
    print(json.dumps(results,indent=2))


if __name__ == "__main__":
    main()
