"""CAD inertials preserve mass and tensor products in the actual loaded robot."""
import copy
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import numpy as np
import pybullet as pb
from scipy.spatial.transform import Rotation
from model import build_urdf,load_parameters,total_mass,validate_link_mass_properties
from run_sim import base_link_pose,load_world


def baseline_inertials(p):
    with tempfile.TemporaryDirectory() as directory:
        root=ET.parse(build_urdf(p,Path(directory)/'baseline.urdf'))
    result={}
    for link in root.findall('.//link'):
        inertial=link.find('inertial')
        values=inertial.find('inertia').attrib
        tensor=[[float(values['ixx']),float(values['ixy']),float(values['ixz'])],
                [float(values['ixy']),float(values['iyy']),float(values['iyz'])],
                [float(values['ixz']),float(values['iyz']),float(values['izz'])]]
        result[link.attrib['name']]=dict(mass_kg=float(inertial.find('mass').attrib['value']),
            com_m=np.fromstring(inertial.find('origin').attrib['xyz'],sep=' ').tolist(),inertia_kg_m2=tensor)
    return result


class CADInertialTests(unittest.TestCase):
    def setUp(self):
        self.p=load_parameters()
        self.p['link_mass_properties']=baseline_inertials(self.p)

    def test_incomplete_rigid_body_inventory_rejected(self):
        del self.p['link_mass_properties']['FL_wheel']
        with self.assertRaises(ValueError):
            total_mass(self.p)

    def test_invalid_tensor_rejected(self):
        item=self.p['link_mass_properties']['FL_femur']
        for tensor in (np.diag([1.,1.,3.]),np.diag([1.,1.,-1.]),np.array([[1,1,0],[0,1,0],[0,0,1]])):
            with self.subTest(tensor=tensor):
                item['inertia_kg_m2']=tensor.tolist()
                with self.assertRaises(ValueError):
                    validate_link_mass_properties(self.p)

    def test_xml_keeps_off_diagonal_inertia_and_shifted_com(self):
        item=self.p['link_mass_properties']['FL_femur']
        item['mass_kg']=.3
        item['com_m']=[.01,.025,-.06]
        item['inertia_kg_m2']=[[.0007,.0001,-.00005],[.0001,.0006,.00002],[-.00005,.00002,.0003]]
        with tempfile.TemporaryDirectory() as directory:
            root=ET.parse(build_urdf(self.p,Path(directory)/'cad.urdf'))
        inertial=root.find(".//link[@name='FL_femur']/inertial")
        np.testing.assert_allclose(np.fromstring(inertial.find('origin').attrib['xyz'],sep=' '),item['com_m'])
        values=inertial.find('inertia').attrib
        for key,expected in [('ixy',.0001),('ixz',-.00005),('iyz',.00002)]:
            self.assertEqual(float(values[key]),expected)

    def test_pybullet_loads_exact_inventory_mass(self):
        self.p['link_mass_properties']['FL_femur']['mass_kg']+=.02
        before=copy.deepcopy(self.p)
        cid,robot,legs,wheels,names,q,dt,base,terrain=load_world(self.p,'stand')
        try:
            actual=sum(pb.getDynamicsInfo(robot,i)[0] for i in range(-1,pb.getNumJoints(robot)))
            self.assertAlmostEqual(actual,total_mass(self.p),places=10)
            self.assertEqual(before,self.p)
        finally:
            pb.disconnect(cid)

    def test_full_base_inertia_does_not_rotate_reported_body_pose(self):
        item=self.p['link_mass_properties']['base_link']
        principal_rotation=Rotation.from_euler('xyz',[.23,-.31,.19]).as_matrix()
        item['inertia_kg_m2']=(principal_rotation@np.diag([.002,.003,.004])@principal_rotation.T).tolist()
        item['com_m']=[.015,-.008,.08]
        cid,robot,legs,wheels,names,q,dt,base,terrain=load_world(self.p,'stand')
        try:
            info=pb.getDynamicsInfo(robot,-1)
            self.assertGreater(np.linalg.norm(np.array(info[4])[:3]),.01)
            position,orientation=base_link_pose(robot)
            np.testing.assert_allclose(position,base,atol=1e-10)
            np.testing.assert_allclose(Rotation.from_quat(orientation).as_matrix(),np.eye(3),atol=1e-10)
            desired_position=np.array([.11,-.04,.26])
            desired_rotation=Rotation.from_euler('xyz',[.08,-.055,.17])
            com_position=desired_position+desired_rotation.apply(info[3])
            com_rotation=desired_rotation*Rotation.from_quat(info[4])
            pb.resetBasePositionAndOrientation(robot,com_position,com_rotation.as_quat())
            position,orientation=base_link_pose(robot)
            np.testing.assert_allclose(position,desired_position,atol=1e-10)
            np.testing.assert_allclose(Rotation.from_quat(orientation).as_matrix(),desired_rotation.as_matrix(),atol=1e-10)
        finally:
            pb.disconnect(cid)


if __name__=='__main__':
    unittest.main()
