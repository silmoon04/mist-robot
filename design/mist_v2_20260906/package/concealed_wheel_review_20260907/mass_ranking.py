"""Rank actual CAD masses and preserve the scope of torque-reserve screens."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from audit_candidate import inventory, BASE

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
LOAD=ROOT/'simulation/proximal_cad_20260907/load_three_contacts.json'


def rank(path):
    raw=path.read_bytes(); report=json.loads(raw)
    rows=inventory(report)
    prints=defaultdict(lambda:dict(mass_g=0,count=0))
    for row in rows:
        if row['category']=='print':
            entry=prints[row['name']]
            entry['mass_g']+=row['mass_g'] or 0
            entry['count']+=1
    ordered=sorted((dict(name=name,**data) for name,data in prints.items()),key=lambda r:r['mass_g'],reverse=True)
    physics=report.get('physical_mass_properties') or {}
    return dict(source=str(path.resolve()),source_sha256=hashlib.sha256(raw).hexdigest(),
                part_count=len(rows),assigned_total_kg=physics.get('assigned_mass_kg'),
                printed_total_kg=sum(r['mass_g'] for r in ordered)/1000,
                largest_printed_families=ordered[:25],
                FL_printed_parts=sorted([r for r in rows if r['group']=='FL' and r['category']=='print'],
                                        key=lambda r:r['mass_g'] or 0,reverse=True)[:15],
                body_printed_parts=sorted([r for r in rows if r['group']=='body' and r['category']=='print'],
                                          key=lambda r:r['mass_g'] or 0,reverse=True)[:12])


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--candidate',type=Path)
    p.add_argument('--label',default='mass_ranking')
    a=p.parse_args()
    if not a.label.replace('_','').replace('-','').isalnum():raise ValueError('Unsafe label')
    baseline=rank(BASE)
    load=json.loads(LOAD.read_bytes())
    mass=baseline['assigned_total_kg']
    available=.7281437625
    target=.8*available
    measured_rms=load['hold_servo_rms_nm'][2]
    uniform=mass*target/measured_rms
    # Rounded coefficients independently reconstructed from the saved loaded
    # posture, fixed limb self-weight and 2:1 x .85 transmission efficiency.
    slope=.116285; constant=-.098698
    base_only=(target-constant)/slope
    peak_target=.8*1.33493023125
    two_contact_slope=2.25*slope
    two_contact_at_baseline=two_contact_slope*mass+constant
    peak_uniform=mass*peak_target/two_contact_at_baseline
    peak_base=(peak_target-constant)/two_contact_slope
    fixed=dict(two_155g_phones_kg=.310,battery_kg=.174,twelve_55g_servos_kg=.660,four_98g_motors_kg=.392)
    result=dict(status='mass_and_quasi_static_reserve_review_not_dynamic_release',
                fixed_components_in_selected_layout=fixed,fixed_component_sum_kg=sum(fixed.values()),
                current_electronics_harness_extras_allowance_kg=.450,baseline=baseline,
                saved_three_contact_fixture=dict(source=str(LOAD),source_sha256=hashlib.sha256(LOAD.read_bytes()).hexdigest(),
                    actual_mass_kg=mass,knee_rms_Nm=measured_rms,continuous_cap_Nm=available,
                    reserve_definition='Demand <=80%ofassumedtorquecap',target_Nm=target,
                    uniform_mass_target_kg=uniform,uniform_reduction_kg=mass-uniform,
                    base_only_mass_target_kg=base_only,base_only_reduction_kg=mass-base_only,
                    affine_knee_motor_torque_Nm=f'{slope}*M{constant:+}',
                    limitation='Old130mm tibia and recorded loaded stance. New140mm tibia and relocated motors require new coefficients.'),
                unrun_two_contact_1p5_counterfactual=dict(force_multiplier_relative_three_contacts=2.25,
                    peak_cap_Nm=1.33493023125,target_Nm=peak_target,
                    uniform_mass_target_kg=peak_uniform,base_only_mass_target_kg=peak_base,
                    unchanged_limb_mass_kg=4.659,
                    base_only_feasible=peak_base>=4.659,
                    limitation='Same old pose and limb self-weight. This is not a dynamic run or stair test.'))
    result['baseline']['reduction_needed_as_fraction_of_all_printed_mass']=(mass-uniform)/baseline['printed_total_kg']
    if a.candidate:
        result['candidate']=rank(a.candidate)
        total=result['candidate']['assigned_total_kg']
        if total is not None:
            result['candidate']['mass_delta_vs_baseline_kg']=total-mass
            result['candidate']['gap_to_old_stance_uniform_target_kg']=total-uniform
            result['candidate']['gap_note']='Gap is a bookkeeping comparison; old torque coefficients are not validated for the new leg.'
    (HERE/(a.label+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    compact={k:v for k,v in result.items() if k not in ('baseline','candidate')}
    print(json.dumps(compact,indent=2))
    for label in ('baseline','candidate'):
        if label in result:
            data=result[label]
            print(label,data['assigned_total_kg'],'kg; printed',data['printed_total_kg'],'kg')
            for row in data['largest_printed_families'][:12]:print(f"{row['mass_g']:8.2f} g / {row['count']}  {row['name']}")


if __name__=='__main__':main()
