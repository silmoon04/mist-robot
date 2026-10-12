"""Check reaction-frame coupling and conserve physical motor inventory."""
import copy
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import numpy as np
from model import build_urdf, coupling, load_parameters, total_mass


class ProximalKneeTests(unittest.TestCase):
    def setUp(self):
        self.original=load_parameters()
        self.p=copy.deepcopy(self.original)
        self.p['transmission'].update(topology='proximal_femur_relative_knee',knee_motor_mount='femur')
        self.p['mass']['knee_servo_com_m']=[0,0,-.04]

    def test_motor_housing_reaction_is_explicit(self):
        del self.p['transmission']['knee_motor_mount']
        with self.assertRaises(ValueError):
            coupling(self.p)

    def test_relative_knee_eliminates_cross_reaction(self):
        load=np.array([0,3.,-2.])
        old=np.linalg.solve(coupling(self.original).T,load)
        new=np.linalg.solve(coupling(self.p).T,load)
        np.testing.assert_allclose(old,[0,2.5,-1])
        np.testing.assert_allclose(new,[0,1.5,-1])
        for qd in (np.array([.3,-.4,.7]),np.array([0,.6,-.2])):
            self.assertAlmostEqual(float(new@(coupling(self.p)@qd)),float(load@qd),places=12)

    def test_misspelled_topology_does_not_silently_decouple_motors(self):
        self.p['transmission']['topology']='proximal_reduction_absolute_tibi'
        with self.assertRaises(ValueError):
            coupling(self.p)

    def test_same_servo_mass_moves_to_femur_with_shifted_com(self):
        with tempfile.TemporaryDirectory() as directory:
            old=ET.parse(build_urdf(self.original,Path(directory)/'old.urdf'))
            new=ET.parse(build_urdf(self.p,Path(directory)/'new.urdf'))
        def mass(root,name):
            return float(root.find(f".//link[@name='{name}']/inertial/mass").attrib['value'])
        self.assertAlmostEqual(total_mass(self.p),total_mass(self.original),places=12)
        self.assertAlmostEqual(sum(float(x.attrib['value']) for x in new.findall('.//mass')),total_mass(self.p),places=12)
        servo=self.p['mass']['proximal_servo_kg']
        for leg in self.p['geometry']['leg_names']:
            self.assertAlmostEqual(mass(old,leg+'_yaw')-mass(new,leg+'_yaw'),servo,places=12)
            self.assertAlmostEqual(mass(new,leg+'_femur')-mass(old,leg+'_femur'),servo,places=12)
            com=np.fromstring(new.find(f".//link[@name='{leg}_femur']/inertial/origin").attrib['xyz'],sep=' ')
            expected=(-.5*self.p['geometry']['femur_m']*self.p['mass']['femur_with_pulleys_kg']-.04*servo)/(self.p['mass']['femur_with_pulleys_kg']+servo)
            self.assertAlmostEqual(com[2],expected,places=9)


if __name__=='__main__':
    unittest.main()
