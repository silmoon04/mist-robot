"""Nominal vertical-load moment screen using actual CAD part COMs.

No physics run or CAD mutation. Geometry, contact distribution, efficiency and
torque caps remain explicit assumptions. Source report hashes are recorded.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from audit_candidate import BASE, inventory

HERE=Path(__file__).resolve().parent
G=9.81
GAIN=2*.85
CONTINUOUS=.7281437625
PEAK=1.33493023125


def data(path):
    raw=path.read_bytes(); report=json.loads(raw)
    fl=report['specifications']['FL']
    masses={(r['group'],r['name']):r['mass_g'] for r in inventory(report)}
    parts=[dict(p,mass_kg=masses[(p['group'],p['name'])]/1000) for p in report['parts'] if p['group']=='FL']
    heading=math.radians(fl['pose_deg']['heading'])
    along=(math.cos(heading),math.sin(heading),0)
    joints=fl['joint_centers_world_mm']
    def arm(point,origin):return sum((point[i]-origin[i])*along[i] for i in range(3))/1000
    coefficients={}
    for name,links in (('hip',('femur','tibia','wheel')),('knee',('tibia','wheel'))):
        origin=joints[name]
        a=-G*arm(joints['wheel'],origin)/(3*GAIN)
        b=sum(p['mass_kg']*G*arm(p['center_hipplane_mm'],origin)/GAIN for p in parts if p['link'] in links)
        coefficients[name]=dict(slope_Nm_per_kg=a,constant_selfweight_Nm=b)
    return dict(path=str(path.resolve()),sha256=hashlib.sha256(raw).hexdigest(),
                assigned_total_kg=(report.get('physical_mass_properties') or {}).get('assigned_mass_kg'),
                FL_mass_kg=sum(p['mass_kg'] for p in parts),
                moving_limb_mass_kg_four_legs=4*sum(p['mass_kg'] for p in parts if p['link']!='body'),
                pose_deg=fl['pose_deg'],coefficients=coefficients)


def screen(candidate,mass):
    result=[]
    for label,multiplier,cap in (('three_contact_continuous',1,.8*CONTINUOUS),
                                 ('unrun_two_contact_1p5_peak',2.25,.8*PEAK)):
        rows=[]
        for joint,co in candidate['coefficients'].items():
            a=co['slope_Nm_per_kg']*multiplier;b=co['constant_selfweight_Nm']
            torque=a*mass+b
            base_bound=((cap-b)/a if a>0 else (-cap-b)/a)
            rows.append(dict(joint=joint,torque_Nm_at_current_mass=torque,
                             uniform_all_mass_target_kg=mass*cap/abs(torque),
                             fixed_limb_base_change_target_kg=base_bound))
        bound=min(r['fixed_limb_base_change_target_kg'] for r in rows)
        result.append(dict(case=label,target_motor_torque_Nm=cap,axes=rows,
                           governing_uniform_target_kg=min(r['uniform_all_mass_target_kg'] for r in rows),
                           governing_base_change_target_kg=bound,
                           implied_base_mass_kg=bound-candidate['moving_limb_mass_kg_four_legs']))
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('candidate',type=Path)
    p.add_argument('--label',default='static_reserve')
    args=p.parse_args()
    if not args.label.replace('_','').replace('-','').isalnum():raise ValueError('Unsafe label')
    old=data(BASE);new=data(args.candidate)
    mass=new['assigned_total_kg']
    projected=mass is None
    if projected:mass=old['assigned_total_kg']+4*(new['FL_mass_kg']-old['FL_mass_kg'])
    result=dict(status='nominal_pose_static_screen_not_runtime_or_release',baseline=old,candidate=new,
                candidate_total_mass_used_kg=mass,candidate_total_is_FL_projection=projected,
                assumed_motor_to_joint_gain=GAIN,gravity_m_s2=G,
                continuous_motor_cap_Nm=CONTINUOUS,peak_motor_cap_Nm=PEAK,
                reserve_definition='Demand no greater than80%ofassumedcap',
                old_nominal=screen(old,old['assigned_total_kg']),new_nominal=screen(new,mass),
                limitations=['Vertical wheel forces only; three equivalent contacts, or unrun two contacts with1.5 multiplier.',
                             'Nominal CAD pose, without compliance, inertia, terrain, uneven contact loads or measured motor behaviour.',
                             'Uniform targets hypothetically scale every mass; fixed-limb targets change only base mass.',
                             'Symmetric coaxial rotor COMs are treated as their declared link; internal rotor inertias are irrelevant to this static screen.',
                             'Candidate still contains assembly interferences and incomplete interfaces.'])
    (HERE/(args.label+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
