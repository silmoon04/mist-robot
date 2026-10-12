"""Meaningful offline math/contract tests. These are not Fusion solver tests."""
import copy
import math
import tempfile
import unittest
from pathlib import Path
import json
from types import SimpleNamespace
import motion as m


def transform(rotation=None, at=(0,0,0)):
    rotation=rotation or [[1,0,0],[0,1,0],[0,0,1]]
    return [list(rotation[i])+[at[i]] for i in range(3)]+[[0,0,0,1]]


def fixtures():
    parameters=dict(geometry=dict(leg_names=['FL'],joint_limits_deg=[[-100,100],[-40,125],[-150,-15]]),
                    transmission=dict(topology='proximal_femur_relative_knee',ratios=[2,2,2]))
    body=dict(parts=[dict(name='deck')])
    leg=dict(leg_name='FL',pose_deg=dict(yaw=-45,hip=58,knee=-84,heading=0),
             joint_centers_world_mm=dict(yaw=[70,70,0],hip=[105,100,0],knee=[170,100,-100],wheel=[140,100,-190]),
             parts=[dict(name=link,link=link,rigid_group=link) for link in ['body','yaw','femur','tibia','wheel']]+[
                 dict(name='input_gear',link='femur',rigid_group='knee_input_rotor')])
    return parameters,body,[leg]


class MotionTests(unittest.TestCase):
    def test_limits_offset_not_absolute(self):
        self.assertEqual(m.map_limits(.2,58,[-40,125],1),[.2+math.radians(-98),.2+math.radians(67)])

    def test_limits_reverse_sign_sorted(self):
        self.assertEqual(m.map_limits(-.1,-84,[-150,-15],-1),[-.1-math.radians(69),-.1+math.radians(66)])

    def test_unverified_sign_rejected(self):
        with self.assertRaises(ValueError):m.map_limits(0,58,[-40,125],0)

    def test_all_four_joint_axes_and_wheel_unlimited(self):
        p=m.build_motion_plan(*fixtures())
        self.assertEqual(len(p['joints']),4)
        self.assertEqual(p['joints'][1]['axis_world'],[0,-1,0])
        self.assertIsNone(p['joints'][3]['physical_limits_deg'])
        self.assertEqual(p['joints'][2]['built_physical_deg'],-84)

    def test_rotors_are_explicit_fixed_phase_approximations(self):
        p=m.build_motion_plan(*fixtures())
        self.assertEqual(p['fixed_phase_rotor_attachments'],{'FL/knee_input_rotor':'FL/femur'})
        self.assertNotIn('FL/input_gear',p['groups']['FL/femur'])
        self.assertFalse(p['transmission_mates_created'])

    def test_rotor_housing_mass_group_overrides_geometry_frame(self):
        args=fixtures()
        rotor=args[2][0]['parts'][-1]
        rotor['link']='pod'
        rotor['mass_group']='femur'
        p=m.build_motion_plan(*args)
        self.assertEqual(p['fixed_phase_rotor_attachments'],{'FL/knee_input_rotor':'FL/femur'})

    def test_geometry_link_is_not_silently_rigid_group(self):
        args=fixtures();del args[2][0]['parts'][1]['rigid_group']
        with self.assertRaisesRegex(ValueError,'explicit rigid_group'):m.build_motion_plan(*args)

    def test_missing_link_rejected(self):
        args=fixtures();args[2][0]['parts']=[p for p in args[2][0]['parts'] if p['name']!='tibia']
        with self.assertRaisesRegex(ValueError,'missing rigid group'):m.build_motion_plan(*args)

    def test_invalid_built_pose_rejected(self):
        args=fixtures();args[2][0]['pose_deg']['hip']=130
        with self.assertRaisesRegex(ValueError,'outside physical limits'):m.build_motion_plan(*args)

    def test_duplicate_part_rejected(self):
        args=fixtures();args[2][0]['parts'].append(copy.deepcopy(args[2][0]['parts'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate'):m.build_motion_plan(*args)

    def test_unused_override_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unused'):m.build_motion_plan(*fixtures(),group_overrides={'FL/unknown':'body'})

    def probe_case(self,sign=1,offset=0):
        parent=transform(m.rotation_about([1,0,0],.35),[3,4,5])
        local_centre=[2,0,-1]
        local_axis=[0,-1,0]
        centre=m.point(parent,local_centre);axis=m.direction(parent,local_axis)
        child=m.mmul(parent,transform(at=[1,2,3]))
        r=m.rotation_about(local_axis,sign*.001)
        delta=transform(r,[local_centre[i]-m.dot(r[i],local_centre) for i in range(3)])
        after=m.mmul(parent,m.mmul(delta,m.mmul(m.inverse_rigid(parent),child)))
        return m.verify_probe(parent,child,parent,after,[centre[0]+offset,*centre[1:]],axis,.001)

    def test_probe_measures_positive_relative_rotation(self):
        self.assertEqual(self.probe_case()['sign'],1)

    def test_probe_measures_negative_relative_rotation(self):
        self.assertEqual(self.probe_case(-1)['sign'],-1)

    def test_probe_wrong_centre_fails(self):
        with self.assertRaisesRegex(RuntimeError,'different axis or joint centre'):self.probe_case(offset=1)

    def test_ambiguous_occurrence_fails(self):
        root=SimpleNamespace(allOccurrencesByComponent=lambda c:SimpleNamespace(count=2))
        with self.assertRaisesRegex(ValueError,'expected one root occurrence'):
            m.resolve_occurrences(root,{'components':{'deck':object()}},[])

    def test_grounding_uses_root_proxies_for_nested_ancestors(self):
        root=SimpleNamespace()
        parent=SimpleNamespace(fullPathName='leg:1',sourceComponent=root)
        leaf=SimpleNamespace(fullPathName='leg:1+part:1',sourceComponent=root)
        unrelated=SimpleNamespace(fullPathName='unrelated:1',sourceComponent=root)
        root.allOccurrences=[parent,leaf,unrelated]
        stale=SimpleNamespace(fullPathName=leaf.fullPathName,sourceComponent=object(),
                              assemblyContext=SimpleNamespace(fullPathName='leg:1',sourceComponent=object()))
        resolved,nodes=m.root_context_grounding_nodes(root,{'FL/part':stale})
        self.assertIs(resolved['FL/part'],leaf)
        self.assertEqual(nodes,[leaf,parent])

    def test_grounding_rejects_native_local_context(self):
        root=SimpleNamespace()
        native=SimpleNamespace(fullPathName='part:1',sourceComponent=object())
        root.allOccurrences=[native]
        with self.assertRaisesRegex(ValueError,'root source context'):
            m.root_context_grounding_nodes(root,{'FL/part':native})

    def test_missing_native_api_writes_failure_report(self):
        # Deliberately outside Fusion: native import must fail without pretending
        # that static declarations create a real joint.
        with tempfile.TemporaryDirectory() as temporary:
            target=Path(temporary)/'report.json'
            with self.assertRaises(ModuleNotFoundError):
                m.apply_motion_plan(None,m.build_motion_plan(*fixtures()),{},target)
            report=json.loads(target.read_text())
            self.assertFalse(report['native_execution'])
            self.assertFalse(report['native_joint_creation_complete'])
            self.assertTrue(report['errors'])


if __name__=='__main__':unittest.main(verbosity=2)
