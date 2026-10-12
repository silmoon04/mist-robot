"""Concealed motion contract and shared-component/root-proxy regression tests."""
from pathlib import Path
import copy
import importlib.util
import json
import math
import sys
import unittest
from types import SimpleNamespace
import motion_groups as adapter

HERE=Path(__file__).resolve().parent
CAD=HERE.parent
ROOT=CAD.parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
    return module


class Matrix:
    def __init__(self,rows):self.rows=rows
    def getCell(self,i,j):return self.rows[i][j]


class Collection:
    def __init__(self,items):self.items=items;self.count=len(items)
    def item(self,index):return self.items[index]
    def __iter__(self):return iter(self.items)


def component(name):
    return SimpleNamespace(name=name,occurrences=Collection([]),bRepBodies=Collection([SimpleNamespace(isSolid=True,volume=1.)]))


def transform(heading=0):
    c,s=math.cos(math.radians(heading)),math.sin(math.radians(heading))
    return [[c,-s,0,0],[s,c,0,0],[0,0,1,0],[0,0,0,1]]


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for directory in (CAD,CAD/'leg_proximal_20260907',HERE):
            if str(directory) not in sys.path:sys.path.insert(0,str(directory))
        # Capture current source imports in explicit dependency order.
        load('leg_gears',CAD/'leg_gears.py');load('leg_native',CAD/'leg_native.py')
        load('retention_recipe',CAD/'leg_proximal_20260907/retention_recipe.py')
        load('proximal_leg',CAD/'leg_proximal_20260907/proximal_leg.py')
        load('thermal_shell',HERE/'thermal_shell.py')
        leg=load('concealed_leg',HERE/'concealed_leg.py')
        body=load('body_native',CAD/'body_native.py')
        cls.helper=load('mist_concealed_test_helper',CAD/'fusion_motion_20260907/motion.py')
        cls.params=json.loads((ROOT/'simulation/design_parameters_20260907.json').read_text())
        cls.params['geometry']['tibia_m']=.140
        cls.params['transmission'].update(topology='proximal_femur_relative_knee',knee_motor_mount='femur')
        cls.specs=[leg.leg_spec(cls.params,name) for name in cls.params['geometry']['leg_names']]
        cls.body=body.body_spec(cls.params)
        cls.plan,cls.contract=adapter.build_concealed_motion_plan(cls.params,cls.body,cls.specs,motion_helper=cls.helper)

    def bindings(self,plan=None):
        plan=plan or self.plan
        specs={s['leg_name']:s for s in self.specs}
        parts={s['leg_name']+'/'+p['name']:p for s in self.specs for p in s['parts']}
        shared={};bindings={};root=SimpleNamespace(allOccurrences=None)
        for key in plan['parts']:
            prefix,name=key.split('/',1)
            # Each part name uses one component definition across four legs,
            # exactly the native cache contract. Occurrence paths stay distinct.
            shared.setdefault(name,component(name))
            frame=copy.deepcopy(parts[key]['transform']) if key in parts else transform()
            for i in range(3):frame[i][3]/=10
            path=prefix+':1+'+name+'_wrapper:1+supplier_import:1+leaf:1'
            bindings[key]=SimpleNamespace(fullPathName=path,component=shared[name],isValid=True,
                transform2=Matrix(frame),assemblyContext=SimpleNamespace(name='wrapper'),sourceComponent=root)
        root.allOccurrences=Collection(list(bindings.values()))
        return root,bindings

    def test_complete_concealed_plan(self):
        expected=len(self.body['parts'])+sum(len(spec['parts']) for spec in self.specs)
        self.assertEqual(len(self.plan['parts']),expected)
        self.assertEqual(len(self.plan['joints']),16)
        for leg in self.params['geometry']['leg_names']:
            self.assertEqual(self.plan['fixed_phase_rotor_attachments'][leg+'/wheel_drive_rotor'],leg+'/tibia')
        self.assertFalse(self.plan['transmission_mates_created'])

    def test_wheel_output_gear_rotates_with_wheel(self):
        for leg in self.params['geometry']['leg_names']:
            members=self.plan['groups'][leg+'/wheel']
            self.assertIn(leg+'/CW08_miter_output_OEM',members)
            self.assertIn(leg+'/W02_6mm_wheel_axle',members)
            self.assertNotIn(leg+'/CW07_miter_driver_OEM',members)
            self.assertIn(leg+'/CW07_miter_driver_OEM',self.plan['groups'][leg+'/wheel_drive_rotor'])

    def test_moved_case_and_shell_stay_with_tibia(self):
        for leg in self.params['geometry']['leg_names']:
            members=self.plan['groups'][leg+'/tibia']
            for name in ['CW01_FIT0493_upper_tibia_CASE','CW12_wheel_bearing_keeper','TH03_white_faceted_cover_front','TH03_white_faceted_cover_rear']:
                self.assertIn(leg+'/'+name,members)

    def test_critical_bad_group_rejected(self):
        specs=copy.deepcopy(self.specs)
        next(p for p in specs[0]['parts'] if p['name']=='CW08_miter_output_OEM')['rigid_group']='tibia'
        with self.assertRaisesRegex(ValueError,'conflicts with reviewed physical group'):adapter.concealed_group_contract(specs)

    def test_wheel_output_mass_cannot_stay_on_housing(self):
        specs=copy.deepcopy(self.specs)
        next(p for p in specs[0]['parts'] if p['name']=='CW08_miter_output_OEM')['mass_group']='tibia'
        with self.assertRaisesRegex(ValueError,'wheel output mass must follow'):adapter.concealed_group_contract(specs)

    def test_missing_rigid_group_is_not_inferred(self):
        specs=copy.deepcopy(self.specs);del specs[0]['parts'][0]['rigid_group']
        with self.assertRaisesRegex(ValueError,'explicit rigid_group'):adapter.concealed_group_contract(specs)

    def test_stale_tibia_parameters_rejected(self):
        params=copy.deepcopy(self.params);params['geometry']['tibia_m']=.130
        with self.assertRaisesRegex(ValueError,'tibia length'):adapter.build_concealed_motion_plan(params,self.body,self.specs,motion_helper=self.helper)

    def test_partial_robot_is_not_accepted_as_full_adapter(self):
        with self.assertRaisesRegex(ValueError,'each configured leg exactly once'):
            adapter.build_concealed_motion_plan(self.params,self.body,self.specs[:1],motion_helper=self.helper)

    def test_nonfinite_or_negative_lengths_are_rejected(self):
        for parameter,recipe in [(float('nan'),140.),(float('inf'),float('inf')),(-.140,-140.)]:
            with self.subTest(parameter=parameter,recipe=recipe):
                params=copy.deepcopy(self.params);specs=copy.deepcopy(self.specs)
                params['geometry']['tibia_m']=parameter
                for spec in specs:spec['wheel_drive']['tibia_mm']=recipe
                with self.assertRaisesRegex(ValueError,'finite and positive'):
                    adapter.build_concealed_motion_plan(params,self.body,specs,motion_helper=self.helper)

    def test_shared_component_definitions_and_nested_paths_accepted(self):
        root,bindings=self.bindings()
        self.assertIs(bindings['FL/CW08_miter_output_OEM'].component,bindings['FR/CW08_miter_output_OEM'].component)
        prepared,bound,audit=adapter.prepare_root_bindings(root,self.plan,bindings,motion_helper=self.helper)
        self.assertEqual(len(bound),len(self.plan['parts']))
        self.assertFalse(audit['component_definition_uniqueness_required'])
        self.assertEqual(prepared['plan_sha256'],adapter._hash_plan(prepared))
        self.assertEqual(self.plan['native_binding_verified'],False)

    def test_native_container_cannot_replace_leaf(self):
        root,bindings=self.bindings()
        bindings['FL/CW08_miter_output_OEM'].component=SimpleNamespace(name='container',occurrences=Collection([object()]),bRepBodies=Collection([]))
        with self.assertRaisesRegex(ValueError,'bind its body leaf'):adapter.prepare_root_bindings(root,self.plan,bindings,motion_helper=self.helper)

    def test_nonfinite_import_volume_rejected(self):
        root,bindings=self.bindings()
        bindings['FL/CW08_miter_output_OEM'].component.bRepBodies.item(0).volume=float('nan')
        with self.assertRaisesRegex(ValueError,'positive-volume solid'):adapter.prepare_root_bindings(root,self.plan,bindings,motion_helper=self.helper)

    def test_duplicate_root_path_rejected(self):
        root,bindings=self.bindings();bindings['FR/CW08_miter_output_OEM']=bindings['FL/CW08_miter_output_OEM']
        with self.assertRaisesRegex(ValueError,'assigned to two physical parts'):adapter.prepare_root_bindings(root,self.plan,bindings,motion_helper=self.helper)

    def test_native_contextless_leaf_path_rejected(self):
        root,bindings=self.bindings();bindings['FL/CW08_miter_output_OEM']='leaf:1'
        with self.assertRaisesRegex(ValueError,'not a full occurrence path'):adapter.prepare_root_bindings(root,self.plan,bindings,motion_helper=self.helper)

    def test_non_root_source_context_rejected(self):
        root,bindings=self.bindings()
        bindings['FL/CW08_miter_output_OEM'].sourceComponent=object()
        with self.assertRaisesRegex(ValueError,'root source context'):adapter.prepare_root_bindings(root,self.plan,bindings,motion_helper=self.helper)

    def test_representative_selection_uses_actual_transform(self):
        root,bindings=self.bindings()
        # A misoriented first candidate must not be silently used as the datum.
        bindings['FL/Y05_metal_yaw_shaft'].transform2=Matrix(transform(45))
        prepared,bound,audit=adapter.prepare_root_bindings(root,self.plan,bindings,motion_helper=self.helper)
        self.assertEqual(prepared['groups']['FL/yaw'][0],'FL/PF01_hip_only_coxa')

    def test_all_baked_non_cardinal_representatives_fail(self):
        root,bindings=self.bindings()
        for key in self.plan['groups']['FL/yaw']:bindings[key].transform2=Matrix(transform(45))
        with self.assertRaisesRegex(ValueError,'no representative'):adapter.prepare_root_bindings(root,self.plan,bindings,motion_helper=self.helper)

    def test_reflected_import_transform_rejected(self):
        root,bindings=self.bindings();frame=transform();frame[0][0]=-1
        bindings['FL/CW08_miter_output_OEM'].transform2=Matrix(frame)
        with self.assertRaisesRegex(ValueError,'without scale or reflection'):adapter.prepare_root_bindings(root,self.plan,bindings,motion_helper=self.helper)

    def test_flatten_maps_keeps_reused_instances(self):
        root,bindings=self.bindings()
        body=dict(part_occurrences={key.split('/',1)[1]:occ for key,occ in bindings.items() if key.startswith('body/')})
        legs=[dict(spec=spec,part_occurrences={key.split('/',1)[1]:occ for key,occ in bindings.items() if key.startswith(spec['leg_name']+'/')}) for spec in self.specs]
        self.assertEqual(adapter.flatten_part_occurrences(body,legs),bindings)


if __name__=='__main__':unittest.main(verbosity=2)
