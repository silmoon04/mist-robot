"""Comparative static shaft/link screen; not material or fatigue qualification."""
from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parent

def shaft(d_mm, torque_nm, radial_n, span_mm, overhang_mm=0):
    if min(d_mm, span_mm) <= 0 or min(radial_n, torque_nm, overhang_mm) < 0:
        raise ValueError('Positive dimensions and nonnegative loads required')
    torque = torque_nm * 1000
    moment = radial_n * overhang_mm if overhang_mm else radial_n * span_mm / 4
    bending = 32 * moment / (math.pi * d_mm**3)
    shear = 16 * torque / (math.pi * d_mm**3)
    stress = math.sqrt(bending*bending + 3*shear*shear)
    inertia = math.pi * d_mm**4 / 64
    if overhang_mm:
        reactions = [-radial_n * overhang_mm/span_mm, radial_n * (1+overhang_mm/span_mm)]
        deflection = radial_n * overhang_mm**2 * (span_mm+overhang_mm) / (3*200000*inertia)
    else:
        reactions = [radial_n/2, radial_n/2]
        deflection = radial_n * span_mm**3 / (48*200000*inertia)
    return dict(diameter_mm=d_mm, torque_nm=torque_nm, radial_force_n=radial_n,
                bearing_span_mm=span_mm, overhang_mm=overhang_mm,
                bending_mpa=bending, torsion_mpa=shear, von_mises_mpa=stress,
                bearing_reactions_n=reactions, elastic_deflection_mm=deflection,
                margin_to_assumed_100mpa=100/stress if stress else None)

def belt(torque_nm, pitch_radius_mm, pretension_n):
    difference = torque_nm*1000/pitch_radius_mm
    tight, slack = pretension_n+difference/2, pretension_n-difference/2
    return dict(torque_nm=torque_nm, pitch_radius_mm=pitch_radius_mm,
                tension_difference_n=difference, initial_per_span_tension_n=pretension_n,
                tight_span_n=tight, slack_span_n=slack,
                both_spans_taut=slack>0,
                parallel_span_radial_load_n=2*pretension_n if slack>=0 else None)

def rectangular_beam(name,b_mm,h_mm,length_mm,force_n,wall_mm=None,cheeks=1):
    inertia=b_mm*h_mm**3/12
    area=b_mm*h_mm
    if wall_mm:
        bi,hi=b_mm-2*wall_mm,h_mm-2*wall_mm
        if min(bi,hi)<=0: raise ValueError('Invalid box wall')
        inertia-=bi*hi**3/12;area-=bi*hi
    inertia*=cheeks;area*=cheeks
    stress=force_n*length_mm*(h_mm/2)/inertia
    # E is a sensitivity assumption, deliberately not a supplier claim.
    deflection=force_n*length_mm**3/(3*1500*inertia)
    return dict(section=name,b_mm=b_mm,h_mm=h_mm,length_mm=length_mm,force_n=force_n,
                I_mm4=inertia,area_mm2=area,bending_mpa=stress,
                deflection_at_assumed_E1500mpa_mm=deflection,
                stress_with_assumed_Kt2_mpa=2*stress,
                margin_to_assumed_10mpa_with_Kt2=10/(2*stress))

def calculate():
    p=json.loads((ROOT/'simulation/parameters.json').read_text())
    m=p['mass']
    total=sum(m[k] for k in ['shell_kg','battery_kg','brain_phone_kg','face_phone_with_frame_kg','electronics_kg','harness_kg'])
    total+=4*(3*m['proximal_servo_kg']+sum(m[k] for k in ['yaw_carriage_without_servos_kg','femur_with_pulleys_kg','tibia_with_carrier_kg','wheel_motor_with_mount_kg','wheel_hub_and_tire_kg']))
    force=total*9.81/2*1.5
    belts=[belt(t,r,t*1000/r*.75) for t in [1,1.5,2.27,3] for r in [12,15,20]]
    shafts=[shaft(d,t,f,L,a) for d in [4,5,6,7,8] for t,f in [(1.5,150),(2.27,227),(3,300),(4.815,147)]
            for L,a in [(16,0),(24,0),(24,12)]]
    beams=[rectangular_beam('solid24x18',24,18,140,force),
           rectangular_beam('closed24x18_wall2.4',24,18,140,force,wall_mm=2.4),
           rectangular_beam('two4.2x20_cheeks_ideal_equal_share',4.2,20,140,force,cheeks=2),
           rectangular_beam('two4.2x28_cheeks_ideal_equal_share',4.2,28,140,force,cheeks=2)]
    # Spur mesh radial result includes tangential drive and pressure-angle force.
    gears=[dict(ratio=r,servo_torque_nm=t,efficiency=.85,output_torque_nm=t*r*.85,
                module_mm=1,driver_teeth=20,driven_teeth=20*r,face_width_mm=8,
                mesh_resultant_n=(t*r*.85*1000/(10*r))/math.cos(math.radians(20)))
           for r in [2,3.5] for t in [.980665,1.61809725]]
    return dict(status='comparative_static_screen_no_print_release',mass_kg=total,force_per_leg_n=force,
                assumptions={'metal_E_mpa':200000,'metal_comparison_allowance_mpa':100,
                             'printed_E_mpa':1500,'printed_comparison_allowance_mpa':10,
                             'illustrative_stress_concentration_factor':2,
                             'material_limits_measured':False,'fatigue_or_creep_modeled':False},
                belt_cases=belts,shaft_cases=shafts,beam_cases=beams,gear_cases=gears)

def main():
    result=calculate()
    (ROOT/'structural_screen.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    lines=['# Preliminary shaft, belt and printed-link screen',
           '', 'Calculated 7 September 2026. This is a comparative static screen, not a strength certification or a print release.',
           '', f"The current {result['mass_kg']:.5f} kg estimate gives {result['force_per_leg_n']:.2f} N per supporting leg for two contacts and a 1.5 load multiplier. The robot mass still contains estimated leg components. These calculations must be repeated using the complete CAD mass and actual load locations.",
           '', '## Belt load and shaft support',
           '', 'At 3 N m and a 15 mm pitch radius, the tension difference is 200 N. An illustrative 150 N initial tension in each span gives 250 N in the tight span and 50 N in the slack span, for about 300 N resultant pulley pull when the spans are parallel. This is a load case, not an installation tension recommendation. Actual allowable tension, minimum pulley size and tooth engagement depend on the chosen belt.',
           '', 'Gates treats belt tension, sprocket size and precision/backlash as coupled design choices. Its rated reinforced belts and matched metal sprockets do not establish the strength or accuracy of an unknown belt and printed tooth profile. [Gates precision-drive design manual](https://www.gates.com/content/dam/documents-library/catalogs/light-power-and-precision-manual.pdf).',
           '', '| Smooth shaft diameter | 3 N m / 300 N, centred in 24 mm span | Same load, 12 mm outside 24 mm span |',
           '|---|---:|---:|']
    for d in [4,5,6,7,8]:
        a=shaft(d,3,300,24);b=shaft(d,3,300,24,12)
        lines.append(f"| {d} mm | {a['von_mises_mpa']:.1f} MPa | {b['von_mises_mpa']:.1f} MPa |")
    lines+=['', 'The shaft result combines bending and torsion with von Mises stress. It assumes a smooth solid circular shaft, simple bearing supports, static loading and a nominal steel elastic modulus of 200 GPa. It omits flats, holes, threads, clamp notches, stress concentrations, fatigue and fit wear. The 100 MPa comparison threshold in the JSON is an analyst-selected screen, not the strength of owned hardware.',
            '', 'For the overhung case, bearing reactions are -150 N and +450 N. The reversed reaction means both bearings and retainers must carry load in both directions. Merely adding a second bearing on the same side of the pulley does not provide the benefit of placing the pulley between its supports. A 5 mm knee-input trunnion deserves particular scrutiny; choose support spacing and material before committing it to the current bearing inventory.',
            '', 'The 3.5:1 hip gear can reach about 4.81 N m at the chosen 12 V short-peak shaft torque and 85% assumed efficiency. An 8 mm-face, module-1 20/70 pair has a 35 mm driven pitch radius and approximately 146 N resultant mesh force at that load. Tooth stress, mesh phase, wear and the servo horn still require separate checks. Raising ratio does not remove the need to transmit output torque through a real shaft and hub.',
            '', '## Printed link comparisons',
            '', 'These are ideal 140 mm cantilevers under the same transverse force. They compare simple uninterrupted sections. The real linkage and motor coupling need their own free-body diagrams; this deliberately conservative section screen does not replace them.',
            '', '| Section | Nominal bending stress | Illustrative stress with factor 2 | Deflection at assumed E = 1.5 GPa |',
            '|---|---:|---:|---:|']
    for b in result['beam_cases']:
        lines.append(f"| {b['section']} | {b['bending_mpa']:.2f} MPa | {b['stress_with_assumed_Kt2_mpa']:.2f} MPa | {b['deflection_at_assumed_E1500mpa_mm']:.2f} mm |")
    lines+=['', 'The two-cheek cases assume equal load sharing and adequate bolted spacers. Without cross ties, one cheek may carry most of the force or the assembly may twist. The closed box result assumes continuous walls and bonded corners. Bearing holes, belt openings, seams and sparse infill reduce the useful section; a nominal infill percentage cannot simply be substituted for the section modulus.',
            '', 'Print the long cheeks broad-face down so roads run along the main bending path. Carry joint loads through smooth metal shafts, inner-race spacers and through-fasteners. A narrow upright printed spindle repeats the prior layer-splitting failure. Keep screws and caps from peeling a short Z-layer stack away from a bearing boss. The 10 MPa comparison threshold and 1.5 GPa modulus are sensitivity assumptions; no PETG strength, layer adhesion, creep or fatigue property has been measured for this printer/profile.',
            '', '## Bearing and fastener implications',
            '', 'At a 30 mm transverse offset, the selected 29.09 N leg force alone adds 0.873 N m bending at the yaw support. A 24 mm bearing separation reacts that moment through a 36.4 N force couple, before other offsets, gear forces or impacts. Nominal bearing dimensions do not establish capacity for the purchased unbranded assortment. The final BOM must count two supports, spacers and retainers for every shaft; ten of a single bearing type can disappear quickly across four hips.',
            '', 'Do not make the two M3 coupon-clamp bolts proof of a torque-carrying hub. The test measures fit and assembly. Clamping friction depends on preload, material, contact radius and creep; none is known here. Positive torque transfer, metal clamping hardware or a tested interface remains necessary. Heat inserts are for measured retention loads, not journals or an assumed substitute for a through-bolt load path.',
            '', 'Run `python structural_screen.py` to regenerate the JSON and this table. The script checks nonphysical inputs; scaling checks confirm that doubling shaft diameter reduces stress by eight and bending deflection by sixteen at fixed load/span. No finite-element, fatigue, creep or physical test is claimed.']
    (ROOT/'structural_screen.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    a=shaft(4,3,300,24);b=shaft(8,3,300,24)
    assert math.isclose(a['von_mises_mpa']/b['von_mises_mpa'],8)
    assert math.isclose(a['elastic_deflection_mm']/b['elastic_deflection_mm'],16)
    assert belt(3,15,150)['tension_difference_n']==200
    assert math.isclose(sum(shaft(8,3,300,24,12)['bearing_reactions_n']),300)
    print(json.dumps({'mass_kg':result['mass_kg'],'force_n':result['force_per_leg_n'],'cases':len(result['shaft_cases']),'scaling_checks':'pass'}))

if __name__=='__main__': main()
