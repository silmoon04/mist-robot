import unittest
import numpy as np
import pybullet as pb
from model import load_parameters, coupling, fk, ik, neutral, total_mass
from run_sim import load_world, support_margin, ActuatorBank, base_link_pose


class MechanicsTests(unittest.TestCase):
    def setUp(self):
        self.p=load_parameters()

    def test_coupled_transmission_preserves_virtual_work(self):
        a=coupling(self.p)
        qd=np.array([.3,-.4,.7]);tm=np.array([.2,.3,-.6])
        self.assertAlmostEqual(float(tm @ (a @ qd)),float((a.T @ tm) @ qd),places=12)

    def test_fk_ik_all_four_drive_headings(self):
        q=neutral(self.p)
        foot=[]
        for i in range(4):
            f=fk(self.p,i,q[i]);qi,valid=ik(self.p,i,f["axle"])
            self.assertTrue(valid);np.testing.assert_allclose(qi,q[i],atol=1e-10)
            self.assertAlmostEqual(abs(f["wheel_axis"][1]),1,places=10)
            foot.append(f["axle"])
        self.assertAlmostEqual(foot[0][1]-foot[1][1],2*(.103/np.sqrt(2)+.030),places=10)

    def test_urdf_fk_matches_analytic_and_base_frame(self):
        cid,robot,legs,wheels,names,q,dt,base,terrain=load_world(self.p,"stand")
        try:
            actual,quat=base_link_pose(robot)
            np.testing.assert_allclose(actual,base,atol=1e-9)
            mass=sum(pb.getDynamicsInfo(robot,j)[0] for j in range(-1,pb.getNumJoints(robot)))
            self.assertAlmostEqual(mass,total_mass(self.p),places=10)
            for i,w in enumerate(wheels):
                xyz=pb.getLinkState(robot,w)[4]
                np.testing.assert_allclose(xyz,fk(self.p,i,q[i])["axle"]+base,atol=2e-8)
        finally:pb.disconnect(cid)

    def test_unreachable_target_rejected(self):
        _,valid=ik(self.p,0,[1,0,-1]);self.assertFalse(valid)

    def test_support_triangle_boundary_and_outside(self):
        triangle=[[0,0],[1,0],[0,1]]
        self.assertGreater(support_margin(triangle,[.2,.2]),0)
        self.assertLess(support_margin(triangle,[1,1]),0)
        self.assertIsNone(support_margin([[0,0],[1,0]],[.5,0]))

    def test_actuator_torque_speed_and_delay(self):
        q=neutral(self.p);bank=ActuatorBank(self.p,q,.001);target=q.copy();target[:,1]+=.4
        joint,tm=bank.update(q,np.zeros_like(q),target)
        np.testing.assert_allclose(tm,0,atol=1e-12)
        for _ in range(400):joint,tm=bank.update(q,np.zeros_like(q),target)
        self.assertLessEqual(float(np.max(abs(tm))),bank.peak+1e-12)
        self.assertGreater(float(np.max(abs(tm))),.1)
        qd=np.tile(np.linalg.solve(bank.A,[0,bank.speed*1.2,0]),(4,1))
        for _ in range(100):joint,tm=bank.update(q,qd,target)
        # A demanded braking torque remains possible; torque cannot exceed peak.
        self.assertLessEqual(float(np.max(abs(tm))),bank.peak+1e-12)


if __name__=="__main__":unittest.main()
