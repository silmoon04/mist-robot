"""Regression checks for the reviewed real recipe and repeat-run source loading."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
import motion
import reviewed_groups

HERE=Path(__file__).resolve().parent


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest=json.loads((HERE/'current_integration.json').read_text())
        directory=Path(manifest['directory'])
        cls.params=json.loads((directory/'parameters.json').read_text())
        cls.body=json.loads((directory/'body_spec.json').read_text())
        cls.specs=json.loads((directory/'leg_specs.json').read_text())

    def test_all_657_parts_are_assigned_once(self):
        overrides=reviewed_groups.proximal_group_overrides(self.specs)
        plan=motion.build_motion_plan(self.params,self.body,self.specs,group_overrides=overrides)
        keys=[key for group in plan['groups'].values() for key in group]
        self.assertEqual(len(keys),657)
        self.assertEqual(len(set(keys)),657)
        self.assertEqual(len(plan['joints']),16)
        self.assertEqual(len(plan['groups']),33)
        self.assertEqual(len(plan['fixed_phase_rotor_attachments']),16)

    def test_wheel_output_is_one_to_one_and_case_is_stationary(self):
        overrides=reviewed_groups.proximal_group_overrides(self.specs)
        plan=motion.build_motion_plan(self.params,self.body,self.specs,group_overrides=overrides)
        for leg in ['FL','FR','RL','RR']:
            self.assertEqual(set(plan['groups'][leg+'/wheel']),{leg+'/'+name for name in
                ['W02_6mm_wheel_axle','W03_wheel_hub','W04_tire_ENVELOPE','W06_FIT0493_4mmD_SHAFT','W09_6to4mm_coupling_ENVELOPE']})
            self.assertIn(leg+'/W05_FIT0493_motor_CASE',plan['groups'][leg+'/tibia'])
            self.assertIn(leg+'/W07_motor_mount_cradle',plan['groups'][leg+'/tibia'])

    def test_yaw_and_hip_inputs_are_not_grouped_with_outputs(self):
        overrides=reviewed_groups.proximal_group_overrides(self.specs)
        for leg in ['FL','FR','RL','RR']:
            self.assertEqual(overrides[leg+'/Y06_yaw_output_40T'],'yaw')
            self.assertEqual(overrides[leg+'/Y07_yaw_input_20T'],'yaw_motor_rotor')
            self.assertEqual(overrides[leg+'/Y08_factory_horn'],'yaw_motor_rotor')
            self.assertEqual(overrides[leg+'/H06_output_40T'],'femur')
            self.assertEqual(overrides[leg+'/H07_input_20T'],'hip_motor_rotor')
            self.assertEqual(overrides[leg+'/H09_factory_horn'],'hip_motor_rotor')
            self.assertEqual(overrides[leg+'/PF06_input_shaft'],'knee_input_rotor')

    def test_unknown_retained_part_requires_review(self):
        specs=copy.deepcopy(self.specs)
        specs[0]['parts'].append(dict(name='Y99_unreviewed',link='body',rigid_group='body'))
        with self.assertRaisesRegex(ValueError,'unreviewed retained'):reviewed_groups.proximal_group_overrides(specs)

    def test_missing_retained_part_requires_review(self):
        specs=copy.deepcopy(self.specs)
        specs[0]['parts']=[p for p in specs[0]['parts'] if p['name']!='Y07_yaw_input_20T']
        with self.assertRaisesRegex(ValueError,'retained recipe changed'):reviewed_groups.proximal_group_overrides(specs)

    def test_runner_reloads_changed_same_size_same_timestamp_source(self):
        path=HERE.parent/'leg_proximal_20260907/fusion_run.py'
        spec=importlib.util.spec_from_file_location('mist_runner_test',path)
        runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        with tempfile.TemporaryDirectory() as temporary:
            helper=Path(temporary)/'helper.py';helper.write_text('value = 1\n')
            stamp=helper.stat().st_mtime
            first=runner._load('mist_repeat_load_regression',helper)
            helper.write_text('value = 2\n');os.utime(helper,(stamp,stamp))
            second=runner._load('mist_repeat_load_regression',helper)
            self.assertEqual(first.value,1);self.assertEqual(second.value,2)
            self.assertEqual(second.__mist_source_sha256__,hashlib.sha256(helper.read_bytes()).hexdigest())
        sys.modules.pop('mist_repeat_load_regression',None)


if __name__=='__main__':unittest.main(verbosity=2)
