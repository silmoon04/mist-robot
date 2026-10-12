"""Explicit concealed-drive motion groups and root-context occurrence adapter.

No Fusion call is made until rig_native_results is invoked by the root owner.
Reused native component definitions are allowed; part identity is the complete
root occurrence path. The old 657-part grouping evidence is read, never edited.
"""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import traceback

HERE=Path(__file__).resolve().parent
CAD=HERE.parent


def _load_local(name,path):
    raw=path.read_bytes()
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module,hashlib.sha256(raw).hexdigest()


_old,_OLD_SHA=_load_local('mist_concealed_reviewed_proximal_groups',CAD/'fusion_motion_20260907/reviewed_groups.py')

# These parts were physically removed when the motor moved inside the tibia.
REMOVED_LEGACY = frozenset({
    'W05_FIT0493_motor_CASE','W06_FIT0493_4mmD_SHAFT','W07_motor_mount_cradle',
    'W08_motor_brace_M3_-9','W08_motor_brace_M3_9','W09_6to4mm_coupling_ENVELOPE',
    'T03_tibia_outer_cheek',
    'T04_tibia_cross_spacer_-9_-48','T05_tibia_tie_-9_-48',
    'T04_tibia_cross_spacer_9_-48','T05_tibia_tie_9_-48',
    'T04_tibia_cross_spacer_-9_-75','T05_tibia_tie_-9_-75',
    'T04_tibia_cross_spacer_9_-75','T05_tibia_tie_9_-75',
})

# Complete stable roles for parts whose placement frame could mislead grouping.
CRITICAL_GROUPS = {
    'Y06_yaw_output_40T':'yaw','Y07_yaw_input_20T':'yaw_motor_rotor',
    'Y08_factory_horn':'yaw_motor_rotor','H06_output_40T':'femur',
    'H07_input_20T':'hip_motor_rotor','H09_factory_horn':'hip_motor_rotor',
    'PF06_input_shaft':'knee_input_rotor',
    'W01_wheel_626_0':'tibia','W01_wheel_626_1':'tibia',
    'W02_6mm_wheel_axle':'wheel','W03_wheel_hub':'wheel','W04_tire_ENVELOPE':'wheel',
    'CW01_FIT0493_upper_tibia_CASE':'tibia',
    'CW02_motor_4mm_D_output':'wheel_drive_rotor',
    'CW03_4D_to_6mm_coupling_ENVELOPE':'wheel_drive_rotor',
    'CW04_supported_6mm_longitudinal_shaft':'wheel_drive_rotor',
    'CW05_shaft_626_bearing_0':'tibia','CW05_shaft_626_bearing_1':'tibia',
    'CW07_miter_driver_OEM':'wheel_drive_rotor',
    'CW08_miter_output_OEM':'wheel',
    'CW09_positive_tibia_frame':'tibia','CW12_wheel_bearing_keeper':'tibia',
    'CW13_wheel_keeper_M3_-14':'tibia','CW13_wheel_keeper_M3_14':'tibia',
}

PREFERRED_REPRESENTATIVES = {
    'body':('body/B01_structural_lower_deck',),
    'yaw':('Y05_metal_yaw_shaft','PF01_hip_only_coxa'),
    'femur':('H05_hip_metal_trunnion','F01_femur_cheek_drive'),
    'tibia':('T01_knee_metal_shaft','T02_tibia_main_cheek','CW09_positive_tibia_frame'),
    'wheel':('W02_6mm_wheel_axle','W03_wheel_hub'),
    'wheel_drive_rotor':('CW04_supported_6mm_longitudinal_shaft','CW02_motor_4mm_D_output'),
}


def _hash_plan(plan):
    payload={k:v for k,v in plan.items() if k!='plan_sha256'}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,allow_nan=False).encode()).hexdigest()


def concealed_group_contract(leg_specs):
    """Return every leg part's explicit group, with critical roles checked.

    New supplier part names must preserve their stable assembly name or be
    reviewed here. Geometry placement links never provide an implicit group.
    """
    old={name:group for group,names in _old.RETAINED_GROUPS.items() for name in names}
    retained={name:group for name,group in old.items() if name not in REMOVED_LEGACY}
    overrides={};audit=[]
    for spec in leg_specs:
        leg=spec['leg_name'];by={p['name']:p for p in spec['parts']}
        if len(by)!=len(spec['parts']):raise ValueError(leg+': duplicate part names')
        obsolete=REMOVED_LEGACY.intersection(by)
        if obsolete:raise ValueError(leg+': obsolete foot-drive parts remain: '+str(sorted(obsolete)))
        missing=(set(retained)|set(CRITICAL_GROUPS))-set(by)
        if missing:raise ValueError(leg+': expected reviewed parts missing: '+str(sorted(missing)))
        unknown=[name for name in by if name.startswith(('Y','H','F','T','W','S')) and not name.startswith('TH') and name not in retained]
        if unknown:raise ValueError(leg+': unreviewed legacy identity: '+str(unknown))
        for name,part in by.items():
            declared=part.get('rigid_group')
            if declared is None:raise ValueError(leg+'/'+name+': explicit rigid_group required')
            declared='yaw' if declared=='pod' else declared
            expected=CRITICAL_GROUPS.get(name,retained.get(name,declared))
            if declared!=expected:
                raise ValueError(leg+'/'+name+': rigid_group '+str(declared)+' conflicts with reviewed physical group '+expected)
            if name.startswith('TH') and declared!='tibia':
                raise ValueError(leg+'/'+name+': fixed thermal shell must follow tibia')
            housing=part.get('motion_housing_link',part.get('mass_group',part.get('link')))
            if declared=='wheel_drive_rotor' and housing not in ('tibia',leg+'/tibia',leg+'_tibia'):
                raise ValueError(leg+'/'+name+': wheel drive rotor housing must be tibia')
            mass_group=part.get('mass_group',part.get('link'))
            if declared=='wheel' and mass_group not in ('wheel',leg+'/wheel',leg+'_wheel'):
                raise ValueError(leg+'/'+name+': wheel output mass must follow the wheel, not the fixed housing')
            key=leg+'/'+name;overrides[key]=expected
            audit.append(dict(part=key,rigid_group=expected,housing_or_mass_group=housing,
                              source='reviewed_identity' if name in retained or name in CRITICAL_GROUPS else 'explicit_new_recipe_group',
                              nominal_component_transform_mm=part.get('transform')))
        drive=spec.get('wheel_drive',{})
        if float(drive.get('declared_ratio',0))!=1:
            raise ValueError(leg+': concealed preview assumes the declared 1:1 wheel turn')
    return dict(overrides=overrides,assignment_audit=audit,old_reviewed_groups_sha256=_OLD_SHA,
                wheel_drive_preview='Input shaft/coupling/driver are separate rotor members with phase fixed to tibia. Output gear/axle/hub/tyre follow the wheel.',
                gear_mates_created=False,belt_mates_created=False)


def build_concealed_motion_plan(parameters,body_spec,leg_specs,*,motion_helper=None):
    helper=motion_helper or _load_local('mist_concealed_motion_helper',CAD/'fusion_motion_20260907/motion.py')[0]
    names=[spec['leg_name'] for spec in leg_specs]
    expected=parameters['geometry']['leg_names']
    if len(names)!=len(set(names)) or set(names)!=set(expected):
        raise ValueError('The full concealed adapter requires each configured leg exactly once')
    contract=concealed_group_contract(leg_specs)
    lengths={float(spec['wheel_drive']['tibia_mm']) for spec in leg_specs}
    parameter_length=float(parameters['geometry']['tibia_m'])*1000
    if not all(math.isfinite(value) and value>0 for value in [parameter_length,*lengths]):
        raise ValueError('Parameter and concealed recipe tibia lengths must be finite and positive')
    if len(lengths)!=1 or abs(next(iter(lengths))-parameter_length)>1e-6:
        raise ValueError('Parameter tibia length must match all concealed recipe lengths before motion planning')
    plan=helper.build_motion_plan(parameters,body_spec,leg_specs,group_overrides=contract['overrides'])
    plan['concealed_motion_contract']={k:v for k,v in contract.items() if k!='assignment_audit'}
    plan['native_binding_verified']=False
    plan['plan_sha256']=_hash_plan(plan)
    return plan,contract


def flatten_part_occurrences(body_result,leg_results):
    """Use caller-retained occurrence instances; do not deduplicate components."""
    flat={}
    for prefix,result in [('body',body_result)]+[(r['spec']['leg_name'],r) for r in leg_results]:
        bindings=result.get('part_occurrences',result.get('occurrences'))
        if bindings is None:
            raise ValueError(prefix+': provide part_occurrences containing full root-context leaves, not a components-only map')
        for name,occurrence in bindings.items():
            key=prefix+'/'+name
            if key in flat:raise ValueError('Duplicate part key '+key)
            flat[key]=occurrence
    return flat


def _rigid_matrix(matrix):
    if len(matrix)!=4 or any(len(row)!=4 for row in matrix):raise ValueError('Occurrence transform must be 4x4')
    if any(not math.isfinite(float(x)) for row in matrix for x in row):raise ValueError('Nonfinite occurrence transform')
    if max(abs(matrix[3][i]-(1 if i==3 else 0)) for i in range(4))>1e-8:raise ValueError('Invalid homogeneous transform')
    r=[row[:3] for row in matrix[:3]]
    err=max(abs(sum(r[k][i]*r[k][j] for k in range(3))-(1 if i==j else 0)) for i in range(3) for j in range(3))
    det=(r[0][0]*(r[1][1]*r[2][2]-r[1][2]*r[2][1])-r[0][1]*(r[1][0]*r[2][2]-r[1][2]*r[2][0])+r[0][2]*(r[1][0]*r[2][1]-r[1][1]*r[2][0]))
    if err>1e-6 or abs(det-1)>1e-6:raise ValueError('Occurrence rotation must be proper rigid geometry, without scale or reflection')


def prepare_root_bindings(root,plan,supplied_occurrences,*,motion_helper=None):
    """Validate leaf proxy paths, permit shared components and select datums.

    Imported STEP wrappers are not accepted as a part binding. Pass the actual
    one-body leaf in root context, including all wrapper ancestors in its path.
    """
    helper=motion_helper or _load_local('mist_concealed_binding_helper',CAD/'fusion_motion_20260907/motion.py')[0]
    if _hash_plan(plan)!=plan.get('plan_sha256'):raise ValueError('Input plan hash mismatch')
    if set(supplied_occurrences)!=set(plan['parts']):
        raise ValueError('Part bindings must match plan exactly; missing='+str(sorted(set(plan['parts'])-set(supplied_occurrences)))+
                         ', extra='+str(sorted(set(supplied_occurrences)-set(plan['parts']))))
    index={}
    for occurrence in root.allOccurrences:
        path=occurrence.fullPathName
        if path in index:raise ValueError('Root occurrence enumeration has duplicate full paths')
        index[path]=occurrence
    bound={};paths=set();matrices={};records=[]
    for key,supplied in supplied_occurrences.items():
        path=supplied if isinstance(supplied,str) else supplied.fullPathName
        if path not in index:raise ValueError(key+': not a full occurrence path in this root assembly')
        occurrence=index[path]
        if not occurrence.isValid:raise ValueError(key+': invalid occurrence')
        if occurrence.sourceComponent!=root:raise ValueError(key+': occurrence must use root source context before native placement/pinning')
        if occurrence.component.occurrences.count:raise ValueError(key+': imported/container wrapper supplied; bind its body leaf')
        if occurrence.component.bRepBodies.count!=1:raise ValueError(key+': expected one solid body leaf')
        body=occurrence.component.bRepBodies.item(0)
        volume=float(body.volume)
        if not body.isSolid or not math.isfinite(volume) or volume<=0:raise ValueError(key+': leaf body is not a positive-volume solid')
        if path in paths:raise ValueError('One occurrence path was assigned to two physical parts: '+path)
        paths.add(path);bound[key]=occurrence
        matrix=helper.as_matrix(occurrence.transform2);_rigid_matrix(matrix);matrices[key]=matrix
        records.append(dict(part=key,root_path=path,has_assembly_context=occurrence.assemblyContext is not None,
                            component_label=occurrence.component.name,world_transform_cm=matrix))
    prepared=copy.deepcopy(plan);choices=[]
    for group,keys in prepared['groups'].items():
        axes=[j['axis_world'] for j in prepared['joints'] if j['parent_group']==group]
        short=group if group=='body' else group.split('/',1)[1]
        leg=None if group=='body' else group.split('/',1)[0]
        preferred=[name if group=='body' else leg+'/'+name for name in PREFERRED_REPRESENTATIVES.get(short,())]
        scores=[]
        for key in keys:
            inv=helper.inverse_rigid(matrices[key]);local=[helper.unit(helper.direction(inv,axis)) for axis in axes]
            deviation=max((1-max(abs(x) for x in axis) for axis in local),default=0.)
            rank=preferred.index(key) if key in preferred else len(preferred)
            scores.append((deviation>1e-7,rank,deviation,key,local))
        failed,rank,deviation,chosen,local=min(scores)
        if failed:
            raise ValueError(group+': no representative can use the current helper principal-plane normal; STEP may have baked a non-cardinal world pose into all local geometries')
        prepared['groups'][group]=[chosen]+[key for key in keys if key!=chosen]
        choices.append(dict(group=group,representative=chosen,root_path=bound[chosen].fullPathName,
                            local_required_axes=local,max_principal_axis_deviation=deviation))
    audit=dict(part_bindings=records,representatives=choices,component_definition_uniqueness_required=False,
               occurrence_path_uniqueness_required=True,native_constraints_created=False,
               imported_leaf_volume_agreement_checked=False,
               limit='Binding and datum-frame eligibility only; no native solver or gear fit validation.')
    prepared['native_binding_verified']=True
    prepared['native_binding_scope']='Leaf identity and principal-axis eligibility in current supplied root; no joint solver execution.'
    prepared['representative_choices']=choices
    prepared['plan_sha256']=_hash_plan(prepared)
    return prepared,bound,audit


def rig_native_results(design,parameters,body_result,leg_results,output_directory,*,namespace='MIST_concealed_motion_v1'):
    """Root-owned native call after native construction/STEP import has finished."""
    output=Path(output_directory);output.mkdir(parents=True,exist_ok=True)
    report=dict(status='preflight',native_motion_created=False,errors=[],gear_mates_created=False)
    write=lambda name,value:(output/name).write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
    write('concealed_motion_integration.json',report)
    try:
        helper,helper_sha=_load_local('mist_concealed_live_motion_helper',CAD/'fusion_motion_20260907/motion.py')
        plan,contract=build_concealed_motion_plan(parameters,body_result['spec'],[r['spec'] for r in leg_results],motion_helper=helper)
        supplied=flatten_part_occurrences(body_result,leg_results)
        prepared,bound,audit=prepare_root_bindings(design.rootComponent,plan,supplied,motion_helper=helper)
        write('motion_contract.json',contract);write('motion_plan.json',prepared);write('occurrence_binding_audit.json',audit)
        report.update(status='bindings_ready',motion_helper_sha256=helper_sha,part_count=len(bound),
                      rigid_groups=len(prepared['groups']),main_revolutes=len(prepared['joints']))
        write('concealed_motion_integration.json',report)
        native=helper.apply_motion_plan(design,prepared,bound,output/'native_motion_report.json',namespace=namespace)
        report.update(status='native_joint_creation_completed',native_motion_created=native['native_joint_creation_complete'],
                      full_robot_motion_verified=False,native_report='native_motion_report.json')
        write('concealed_motion_integration.json',report)
        return report
    except Exception:
        report['status']='concealed_motion_integration_failed';report['errors'].append(traceback.format_exc())
        write('concealed_motion_integration.json',report)
        raise
