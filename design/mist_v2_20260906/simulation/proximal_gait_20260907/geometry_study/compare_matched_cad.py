"""Static mass/COM/joint-axis inertia comparison; no physics connection or steps."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

HERE=Path(__file__).resolve().parent
SIM=HERE.parents[1]
RUNTIME=HERE.parent/'runtime_cad'
sys.path.insert(0,str(RUNTIME))
import model
sys.path.insert(0,str(HERE))
import geometry_study as geo


def explicit_properties(p):
    if p.get('link_mass_properties'):
        return copy.deepcopy(p['link_mass_properties'])
    with tempfile.TemporaryDirectory(prefix='mist_static_mass_') as temp:
        root=ET.parse(model.build_urdf(p,Path(temp)/'model.urdf')).getroot()
    result={}
    for link in root.findall('link'):
        inertial=link.find('inertial');tensor=inertial.find('inertia')
        a={key:float(tensor.get(key)) for key in ['ixx','iyy','izz','ixy','ixz','iyz']}
        result[link.get('name')]={'mass_kg':float(inertial.find('mass').get('value')),
             'com_m':[float(x) for x in inertial.find('origin').get('xyz').split()],
             'inertia_kg_m2':[[a['ixx'],a['ixy'],a['ixz']],[a['ixy'],a['iyy'],a['iyz']],[a['ixz'],a['iyz'],a['izz']]]}
    return result


def leg_parts(p,q,i):
    name=p['geometry']['leg_names'][i];f=model.fk(p,i,q[i]);r=model.rotation_z(f['heading'])
    output=[]
    for suffix,origin,rot in [('_yaw',f['hip'],r),('_femur',f['pitch'],r@geo.ryminus(q[i,1])),
                              ('_tibia',f['knee'],r@geo.ryminus(q[i,1]+q[i,2])),
                              ('_wheel',f['axle'],r@geo.ryminus(q[i,1]+q[i,2]))]:
        item=p['link_mass_properties'][name+suffix]
        output.append((item['mass_kg'],origin+rot@np.array(item['com_m']),rot@np.array(item['inertia_kg_m2'])@rot.T))
    return output


def joint_inertia(p,q,i):
    f=model.fk(p,i,q[i]);r=model.rotation_z(f['heading'])
    axes=[np.array([0,0,1]),r@np.array([0,-1,0]),r@np.array([0,-1,0])]
    origins=[f['hip'],f['pitch'],f['knee']]
    matrix=np.zeros((3,3))
    for part_index,(mass,center,tensor) in enumerate(leg_parts(p,q,i)):
        jv=np.zeros((3,3));jw=np.zeros((3,3))
        for j in range(min(2,part_index)+1):
            jv[:,j]=np.cross(axes[j],center-origins[j]);jw[:,j]=axes[j]
        matrix += mass*jv.T@jv+jw.T@tensor@jw
    return matrix


def static_load(p,q,feet,body,stance):
    gravity=p['environment']['gravity_m_s2'];mass=model.total_mass(p);center=body+geo.com(p,q)
    contacts=feet[stance,:2]
    # Three contacts: unique barycentric vertical reactions. Four contacts:
    # minimum-norm solution, since the static load split is otherwise indeterminate.
    matrix=np.vstack([np.ones(len(stance)),contacts.T])
    normal=np.linalg.lstsq(matrix,mass*gravity*np.array([1,center[0],center[1]]),rcond=None)[0]
    own=np.zeros((4,3));contact=np.zeros((4,3));h=1e-6
    for i in range(4):
        for j in range(3):
            qp,qm=q.copy(),q.copy();qp[i,j]+=h;qm[i,j]-=h
            own[i,j]=mass*gravity*(geo.com(p,qp)[2]-geo.com(p,qm)[2])/(2*h)
            jac=(model.fk(p,i,qp[i])['axle'][2]-model.fk(p,i,qm[i])['axle'][2])/(2*h)
            contact[i,j]=normal[stance.index(i)]*jac if i in stance else 0
    net=own-contact
    shaft=np.array([np.linalg.solve(model.coupling(p).T,row)/np.array(p['transmission']['efficiency']) for row in net])
    inertia=np.array([joint_inertia(p,q,i) for i in range(4)])
    return {'robot_com_body_m':geo.com(p,q).tolist(),'robot_com_world_m':center.tolist(),
            'support_margin_m':geo.margin(feet[stance],center),'stance_legs':stance,'normal_forces_n':normal.tolist(),
            'all_normal_forces_positive':bool((normal>=0).all()),'gravity_joint_torque_nm':own.tolist(),
            'contact_joint_torque_nm':contact.tolist(),'net_joint_torque_nm':net.tolist(),'net_shaft_torque_nm':shaft.tolist(),
            'max_abs_shaft_torque_nm':float(abs(shaft).max()),'locked_leg_joint_mass_matrix_kg_m2':inertia.tolist(),
            'locked_leg_joint_axis_inertia_kg_m2':np.diagonal(inertia,axis1=1,axis2=2).tolist()}


def main():
    old_path=SIM/'proximal_knee_20260907/parameters_same_mass.json'
    cad_path=SIM/'proximal_cad_20260907/parameters_cad_inertials.json'
    old=model.load_parameters(old_path);cad=model.load_parameters(cad_path)
    old['link_mass_properties']=explicit_properties(old)
    model.validate_link_mass_properties(old);model.validate_link_mass_properties(cad)
    assert old['geometry']==cad['geometry']
    q0=model.neutral(old)
    feet=np.array([model.fk(old,i,q0[i])['axle'] for i in range(4)]);feet[:,2]=.0425
    inputs=[('neutral_four_support',q0,feet.copy(),np.array([0.,0.,.2325]),[0,1,2,3])]
    highbody=np.array([0.,0.,.2435]);highq,valid=geo.joint_pose(old,feet,highbody);assert valid
    inputs.append(('raised_four_support',highq,feet.copy(),highbody,[0,1,2,3]))
    target=geo.closest_inset(feet[[0,1,3]],geo.com(old,q0)[:2],.03)
    for label,u in [('RL_support_start',0.),('RL_mid_swing',.5)]:
        sample=feet.copy();sample[2]+=[.08*u*u*(3-2*u),0,.04*np.sin(np.pi*u)**2]
        body,q,valid=geo.body_for_com(old,sample,[0,0],.2435,target);assert valid
        inputs.append((label,q,sample,body,[0,1,3]))
    cases=[]
    for name,q,sample,body,stance in inputs:
        result={'case':name,'q_deg':np.degrees(q).tolist(),'body_position_m':body.tolist(),'feet_world_m':sample.tolist(),
                'same_mass':static_load(old,q,sample,body,stance),'matched_cad_at_same_pose':static_load(cad,q,sample,body,stance)}
        if len(stance)==3:
            new_target=geo.closest_inset(sample[stance],geo.com(cad,q0)[:2],.03)
            new_body,new_q,valid=geo.body_for_com(cad,sample,body[:2],.2435,new_target);assert valid
            result['matched_cad_replanned_body_m']=new_body.tolist()
            result['matched_cad_replanned_q_deg']=np.degrees(new_q).tolist()
            result['matched_cad_replanned']=static_load(cad,new_q,sample,new_body,stance)
        cases.append(result)
    links=[]
    for name,a in old['link_mass_properties'].items():
        b=cad['link_mass_properties'][name]
        links.append({'name':name,'same_mass':a,'matched_cad':b,'mass_change_kg':b['mass_kg']-a['mass_kg']})
    femur_axis={}
    for label,p in [('same_mass',old),('matched_cad',cad)]:
        item=p['link_mass_properties']['FL_femur'];c=np.array(item['com_m']);tensor=np.array(item['inertia_kg_m2'])
        femur_axis[label]={'femur_only_pitch_axis_about_hip_kg_m2':float(tensor[1,1]+item['mass_kg']*(c[0]**2+c[2]**2)),
                           'femur_pitch_com_inertia_kg_m2':float(tensor[1,1]),
                           'parallel_axis_term_kg_m2':float(item['mass_kg']*(c[0]**2+c[2]**2))}
    out={'scope':'Quasistatic vertical-force and rigid-link joint-axis inertia comparison. No physics steps or dynamic success claim.',
         'parameter_files_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [old_path,cad_path]},
         'runtime_model_sha256':hashlib.sha256(Path(model.__file__).read_bytes()).hexdigest(),
         'helper_sha256':hashlib.sha256(Path(geo.__file__).read_bytes()).hexdigest(),
         'masses_kg':{'same_mass':model.total_mass(old),'matched_cad':model.total_mass(cad)},
         'per_link_comparison':links,'femur_pitch_axis':femur_axis,'cases':cases,
         'assumptions':['Same joint geometry, nominal vertical ground reactions, level body, zero acceleration.',
             'Four-contact reaction forces use the minimum-norm equilibrium split; three-contact forces are uniquely determined.',
             'Joint-axis inertia includes all descendant links with other leg joints and wheel spin locked; full 3x3 per-leg joint mass matrices are saved.',
             'These are link inertias, not independent rotor/gearbox inertia, and omit other-leg/body free-base coupling.',
             'No horizontal contact forces, friction, compliance, thermal dynamics, impacts or controller saturation simulation.',
             'Wheel COMs are on their spin axes; the nominal zero wheel-angle choice does not alter their mass distribution.']}
    (HERE/'matched_cad_mass_comparison.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps({'mass':out['masses_kg'],'femur_axis':femur_axis},indent=2))
    for case in cases:
        print(case['case'])
        for label in ['same_mass','matched_cad_at_same_pose','matched_cad_replanned']:
            if label not in case:continue
            r=case[label]
            print(label,'COMmm',np.array(r['robot_com_body_m'])*1000,'marginmm',1000*r['support_margin_m'],
                  'F',r['normal_forces_n'],'peakshaft',r['max_abs_shaft_torque_nm'],
                  'FL I',r['locked_leg_joint_axis_inertia_kg_m2'][0],
                  'gravityFL',r['gravity_joint_torque_nm'][0], 'shaftFL',r['net_shaft_torque_nm'][0])


if __name__=='__main__':main()
