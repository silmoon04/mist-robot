"""Compare analytic COM to frozen PyBullet links; no simulation steps or hardware."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
import pybullet as pb

HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parent / 'runtime_snapshot'
sys.path.insert(0, str(RUNTIME))
import model
from run_sim import base_link_pose, load_world, world_com
# Load the revised helper directly; the frozen helper remains unchanged.
sys.path.insert(0, str(HERE))
import geometry_study as geometry


def true_base_link_pose(robot):
    inertial_position, inertial_rotation = pb.getBasePositionAndOrientation(robot)
    info = pb.getDynamicsInfo(robot, -1)
    inverse = pb.invertTransform(info[3], info[4])
    return pb.multiplyTransforms(inertial_position, inertial_rotation, *inverse)


def main():
    source = HERE.parents[1] / 'proximal_knee_20260907/parameters_same_mass.json'
    original = model.load_parameters(source)
    parameters = copy.deepcopy(original)
    with tempfile.TemporaryDirectory(prefix='mist_com_validation_') as temp:
        path = model.build_urdf(original, Path(temp)/'original.urdf')
        links = ET.parse(path).getroot().findall('link')
    properties = {}
    rotation = np.array(pb.getMatrixFromQuaternion(pb.getQuaternionFromEuler([.23, -.31, .19]))).reshape(3, 3)
    for index, link in enumerate(links):
        name = link.get('name')
        old = link.find('inertial')
        mass = float(old.find('mass').get('value')) * (1 + .01 * index)
        center = np.array([float(x) for x in old.find('origin').get('xyz').split()])
        # Every moving link has nonzero local X/Y/Z offset, including the wheels.
        center += [.003 + .0002*index, -.005 + .0001*index, .004 - .0001*index]
        tensor = rotation @ np.diag(np.array([.0002, .0003, .0004])*(1+.02*index)) @ rotation.T
        properties[name] = {'mass_kg': mass, 'com_m': center.tolist(), 'inertia_kg_m2': tensor.tolist()}
    parameters['link_mass_properties'] = properties
    parameters['status'] = 'synthetic_COM_verification_fixture_not_robot_mass_estimate'
    model.validate_link_mass_properties(parameters)
    cases = []
    for label, p in [('original_diagonal', original), ('synthetic_full_inertia', parameters)]:
        cid, robot, legids, wheelids, names, q0, dt, base0, terrain = load_world(p, 'crawl')
        try:
            for state_index in range(3):
                q = q0 + np.radians(np.array([[8,-6,9],[-5,4,-8],[3,5,-5],[-7,-4,8]])*state_index)
                wheels = np.array([.4,-.7,1.1,-1.4])*state_index
                for i in range(4):
                    for j, joint in enumerate(legids[i]):
                        pb.resetJointState(robot, joint, q[i,j])
                    pb.resetJointState(robot, wheelids[i], wheels[i])
                desired_body_position = [.11*state_index, -.04*state_index, .24+.02*state_index]
                desired_body_rotation = pb.getQuaternionFromEuler([.08*state_index,-.055*state_index,.17*state_index])
                inertial = pb.getDynamicsInfo(robot,-1)
                desired_inertial_pose = pb.multiplyTransforms(desired_body_position, desired_body_rotation, inertial[3], inertial[4])
                pb.resetBasePositionAndOrientation(robot, *desired_inertial_pose)
                for j in range(pb.getNumJoints(robot)):
                    pb.getLinkState(robot,j,computeForwardKinematics=True)
                actual_com = np.asarray(world_com(robot))
                body_position, body_rotation = true_base_link_pose(robot)
                body_matrix = np.array(pb.getMatrixFromQuaternion(body_rotation)).reshape(3,3)
                analytic_body_com = geometry.com(p,q,wheels)
                analytic_world_com = np.asarray(body_position) + body_matrix @ analytic_body_com
                packed_com = geometry.com(p,np.column_stack([q,wheels]))
                existing_position, existing_rotation = base_link_pose(robot)
                existing_matrix = np.array(pb.getMatrixFromQuaternion(existing_rotation)).reshape(3,3)
                existing_projection = np.asarray(existing_position) + existing_matrix @ analytic_body_com
                cases.append({'fixture':label,'state_index':state_index,
                              'analytic_world_com_m':analytic_world_com.tolist(),'pybullet_world_com_m':actual_com.tolist(),
                              'com_error_m':float(np.linalg.norm(analytic_world_com-actual_com)),
                              'packed_q_error_m':float(np.linalg.norm(packed_com-analytic_body_com)),
                              'existing_base_link_pose_projection_error_m':float(np.linalg.norm(existing_projection-actual_com)),
                              'base_local_inertial_quaternion_xyzw':list(inertial[4]),
                              'true_base_position_m':list(body_position),'existing_base_position_m':list(existing_position)})
        finally:
            pb.disconnect(cid)
    output={'scope':'Kinematic fixture verification only. No physics steps, dynamic success claims or hardware.',
            'model_source':str(model.__file__),'model_sha256':hashlib.sha256(Path(model.__file__).read_bytes()).hexdigest(),
            'helper_sha256':hashlib.sha256(Path(geometry.__file__).read_bytes()).hexdigest(),
            'synthetic_parameters':parameters,'cases':cases,
            'analytic_COM_pass_1micrometre':all(c['com_error_m']<1e-6 and c['packed_q_error_m']<1e-12 for c in cases)}
    (HERE/'link_com_verification.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in output.items() if k!='synthetic_parameters'},indent=2))
    if not output['analytic_COM_pass_1micrometre']:
        raise SystemExit('COM mismatch')


if __name__=='__main__':
    main()
