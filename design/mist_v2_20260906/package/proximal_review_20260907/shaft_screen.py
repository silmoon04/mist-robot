"""Smooth 7 mm shaft, discrete pulley/gear loads, elastic static comparison."""
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent


def beam(loads):
    left,right=8.5,45.825
    span=right-left
    reactions_left=[-sum(f[j]*(right-y)/span for y,f in loads) for j in range(2)]
    reactions_right=[-sum(f[j]*(y-left)/span for y,f in loads) for j in range(2)]
    samples=[]
    for point in [left]+[y for y,f in loads]+[right]:
        moments=[reactions_left[j]*(point-left)+sum(f[j]*(point-y) for y,f in loads if y<=point) for j in range(2)]
        samples.append(dict(y_mm=point,moment_Nmm=math.hypot(*moments)))
    peak=max(samples,key=lambda r:r["moment_Nmm"])
    stress=32*peak["moment_Nmm"]/(math.pi*7**3)
    return dict(reaction_left_XZ_N=reactions_left,reaction_right_XZ_N=reactions_right,
                peak=peak,bending_stress_MPa=stress,
                if_shaft_carries_3Nm_von_mises_MPa=math.hypot(stress,math.sqrt(3)*16*3000/(math.pi*7**3)))


def main():
    torque=2.75
    ft=torque*1000/20
    fr=ft*math.tan(math.radians(20))
    result=dict(status="static_smooth_shaft_screen_no_notches_fatigue_or_measured_material",
                supports_mm=[8.5,45.825],shaft_diameter_mm=7,
                pulley_load_N=300,pulley_load_Y_mm=21.125,
                gear_torque_Nm=torque,gear_force_plane_Y_mm=32.125,
                gear_force_tangential_N=ft,gear_force_radial_N=fr,
                pulley_only=beam([(21.125,(0,-300))]),
                radial_mesh_force_opposes_belt_pull=beam([(21.125,(0,-300)),(32.125,(ft,fr))]),
                radial_mesh_force_adds_to_belt_pull=beam([(21.125,(0,-300)),(32.125,(ft,-fr))]))
    a,b=21.125-8.5,45.825-21.125
    result["pulley_only"]["load_point_deflection_mm_E200GPa"]=300*a*a*b*b/(3*200000*(math.pi*7**4/64)*(a+b))
    (HERE/"shaft_screen.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
