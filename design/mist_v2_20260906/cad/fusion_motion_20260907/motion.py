"""Native Fusion motion rig for explicit MIST part/link assignments.

Imports Autodesk only when apply_motion_plan runs inside Fusion. Offline plan
checks do not claim native execution, solver success or transmission mates.
"""
from __future__ import annotations
import datetime
import hashlib
import json
import math
from pathlib import Path
import traceback

SCHEMA = 1
LINKS = ('body', 'yaw', 'femur', 'tibia', 'wheel')


def _finite(values, label):
    if not all(math.isfinite(float(v)) for v in values):
        raise ValueError(label + ' contains a non-finite value')


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def norm(a):
    return math.sqrt(dot(a, a))


def unit(a):
    _finite(a, 'axis')
    length = norm(a)
    if length < 1e-12:
        raise ValueError('A joint axis cannot be zero')
    return [v/length for v in a]


def mmul(a, b):
    return [[sum(a[i][k]*b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]


def point(matrix, value):
    return [dot(matrix[i][:3], value)+matrix[i][3] for i in range(3)]


def direction(matrix, value):
    return [dot(matrix[i][:3], value) for i in range(3)]


def inverse_rigid(matrix):
    r = [row[:3] for row in matrix[:3]]
    rt = [list(row) for row in zip(*r)]
    return [rt[i]+[-dot(rt[i], [matrix[k][3] for k in range(3)])] for i in range(3)]+[[0., 0., 0., 1.]]


def as_matrix(matrix):
    return [[float(matrix.getCell(i, j)) for j in range(4)] for i in range(4)]


def matrix_error(a, b):
    return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))


def rotation_about(axis, angle):
    x, y, z = unit(axis)
    c, t, s = math.cos(angle), 1-math.cos(angle), math.sin(angle)
    return [[t*x*x+c, t*x*y-s*z, t*x*z+s*y],
            [t*x*y+s*z, t*y*y+c, t*y*z-s*x],
            [t*x*z-s*y, t*y*z+s*x, t*z*z+c]]


def map_limits(initial_fusion_rad, built_physical_deg, physical_limits_deg, sign):
    """Account for both the as-built angular offset and the measured API sign."""
    if sign not in (-1, 1):
        raise ValueError('Rotation sign must be measured as -1 or +1')
    values = [initial_fusion_rad + sign*math.radians(q-built_physical_deg) for q in physical_limits_deg]
    return sorted(values)


def verify_probe(before_parent, before_child, after_parent, after_child, centre_cm, axis, delta_rad):
    """Measure actual child-relative-parent rotation, axis and centre of a probe."""
    before_relative = mmul(inverse_rigid(before_parent), before_child)
    after_relative = mmul(inverse_rigid(after_parent), after_child)
    delta = mmul(after_relative, inverse_rigid(before_relative))
    inv_parent = inverse_rigid(before_parent)
    local_axis = unit(direction(inv_parent, axis))
    local_centre = point(inv_parent, centre_cm)
    skew = [(delta[2][1]-delta[1][2])/2, (delta[0][2]-delta[2][0])/2, (delta[1][0]-delta[0][1])/2]
    angle = math.atan2(dot(local_axis, skew), (sum(delta[i][i] for i in range(3))-1)/2)
    if abs(abs(angle)-abs(delta_rad)) > max(1e-7, abs(delta_rad)*.01):
        raise RuntimeError('Native probe did not produce the requested relative rotation')
    expected_r = rotation_about(local_axis, angle)
    rotation_error = max(abs(delta[i][j]-expected_r[i][j]) for i in range(3) for j in range(3))
    expected_t = [local_centre[i]-dot(expected_r[i], local_centre) for i in range(3)]
    translation_error = max(abs(delta[i][3]-expected_t[i]) for i in range(3))
    if rotation_error > 1e-7 or translation_error > 1e-6:
        raise RuntimeError('Native probe rotated around a different axis or joint centre')
    return dict(sign=1 if angle*delta_rad > 0 else -1, measured_relative_angle_rad=angle,
                commanded_delta_rad=delta_rad, rotation_matrix_error=rotation_error,
                centre_error_cm=translation_error)


def build_motion_plan(parameters, body_spec, leg_specs, *, group_overrides=None):
    """Build a serializable plan. Every leg part needs an explicit rigid group.

    A group can be supplied by part.rigid_group or group_overrides['FL/name'].
    Body, yaw, pod, femur, tibia and wheel are structural groups. A name ending
    in '_rotor' is separate. Its motion_housing_link, mass_group or link specifies
    the housing frame, in that order.
    Internal rotors get an explicit fixed-phase preview attachment, not a mate.
    """
    overrides = group_overrides or {}
    geometry = parameters['geometry']
    groups, parts, freezes, joints = {}, {}, {}, []
    def add(key, group, role, item):
        if key in parts:
            raise ValueError('Duplicate part key: '+key)
        parts[key] = dict(group=group, role=role, part_name=item['name'])
        groups.setdefault(group, []).append(key)
    for p in body_spec['parts']:
        add('body/'+p['name'], 'body', 'body', p)
    for spec in leg_specs:
        leg = spec['leg_name']
        if leg not in geometry['leg_names']:
            raise ValueError('Unknown leg '+leg)
        for p in spec['parts']:
            key = leg+'/'+p['name']
            raw = overrides.get(key, p.get('rigid_group'))
            if raw is None:
                raise ValueError(key+': explicit rigid_group required; recipe link alone can misclassify rotating gears or motor cases')
            raw = 'yaw' if raw == 'pod' else raw
            raw = 'body' if raw in ('base', 'base_link') else raw
            if raw in LINKS:
                group = 'body' if raw == 'body' else leg+'/'+raw
                add(key, group, raw, p)
            elif raw.endswith('_rotor'):
                housing = p.get('motion_housing_link', p.get('mass_group', p.get('link')))
                if isinstance(housing, str):
                    housing = housing.removeprefix(leg+'/').removeprefix(leg+'_')
                housing = 'yaw' if housing == 'pod' else housing
                housing = 'body' if housing in ('base','base_link') else housing
                if housing not in LINKS:
                    raise ValueError(key+': rotor needs a valid link for its housing frame')
                group = leg+'/'+raw
                parent = 'body' if housing == 'body' else leg+'/'+housing
                if group in freezes and freezes[group] != parent:
                    raise ValueError(group+': rotor parts disagree about housing frame')
                freezes[group] = parent
                add(key, group, 'internal_rotor', p)
            else:
                raise ValueError(key+': unsupported rigid group '+str(raw))
        heading = math.radians(spec['pose_deg']['heading'])
        axes = {'yaw':[0, 0, 1], 'hip':[math.sin(heading), -math.cos(heading), 0],
                'knee':[math.sin(heading), -math.cos(heading), 0],
                'wheel':[math.sin(heading), -math.cos(heading), 0]}
        edges = [('yaw','body',leg+'/yaw'), ('hip',leg+'/yaw',leg+'/femur'),
                 ('knee',leg+'/femur',leg+'/tibia'), ('wheel',leg+'/tibia',leg+'/wheel')]
        for index, (name, parent, child) in enumerate(edges):
            q = 0.0 if name == 'wheel' else float(spec['pose_deg'][name])
            limits = None if name == 'wheel' else list(geometry['joint_limits_deg'][index])
            centre = list(spec['joint_centers_world_mm'][name])
            _finite([q, *centre, *axes[name]], leg+'/'+name)
            if limits is not None and not limits[0] <= q <= limits[1]:
                raise ValueError(leg+'/'+name+': built angle is outside physical limits')
            joints.append(dict(name=leg+'_'+name, parent_group=parent, child_group=child,
                               centre_world_mm=centre, axis_world=unit(axes[name]),
                               built_physical_deg=q, physical_limits_deg=limits,
                               continuous=name == 'wheel'))
    for j in joints:
        for group in (j['parent_group'], j['child_group']):
            if not groups.get(group):
                raise ValueError(j['name']+': missing rigid group '+group)
    for group, parent in freezes.items():
        if not groups.get(parent):
            raise ValueError(group+': missing rotor housing group '+parent)
    unknown = set(overrides)-set(parts)
    if unknown:
        raise ValueError('Unused group overrides: '+str(sorted(unknown)))
    plan = dict(schema_version=SCHEMA, units=dict(position='mm', physical_angle='deg', native_length='cm', native_angle='rad'),
                groups=groups, parts=parts, joints=joints, fixed_phase_rotor_attachments=freezes,
                transmission_metadata=parameters.get('transmission', {}), native_execution=False,
                transmission_mates_created=False, full_motion_verified=False,
                limitations=['Bearing races stay with their declared envelope group.',
                             'Internal rotors keep their assembled phase relative to their housing; no gear or belt mates.',
                             'Rigid groups do not model print compliance, backlash, cable flex or structural strength.'])
    raw = json.dumps(plan, sort_keys=True, allow_nan=False).encode()
    plan['plan_sha256'] = hashlib.sha256(raw).hexdigest()
    return plan


def resolve_occurrences(root, body_result, leg_results):
    """Resolve builder components uniquely into the root assembly context.

    Works with the existing result['components'] contract. A newer explicit
    result['part_occurrences'] map is also accepted and checked by component.
    Ambiguous reused components fail; no matching by display name is attempted.
    """
    result = {}
    for assembly_key, built in [('body', body_result)]+[(item['spec']['leg_name'], item) for item in leg_results]:
        components = built.get('components', {})
        if not components and 'part_occurrences' in built:
            components = {name: occurrence.component for name, occurrence in built['part_occurrences'].items()}
        if not components:
            raise ValueError(assembly_key+': builder returned no component/occurrence map')
        for name, component in components.items():
            matches = root.allOccurrencesByComponent(component)
            if matches.count != 1:
                raise ValueError(f'{assembly_key}/{name}: expected one root occurrence, found {matches.count}')
            result[assembly_key+'/'+name] = matches.item(0)
    return result


def _require(value, message):
    if value is None or value is False:
        raise RuntimeError(message)
    return value


def _compute(design):
    _require(design.computeAll(), 'Fusion Compute All failed')


def _write(path, report):
    Path(path).write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')


def root_context_grounding_nodes(root, supplied):
    """Canonical root proxies for bindings and their ancestor occurrence paths.

    Native-local subcomponent occurrences cannot be pinned or transformed in
    the tested Fusion build. sourceComponent is assembly-context-sensitive:
    it must be the design root for every pin operation here. Ancestors come
    from root.allOccurrences, never from a possibly native-local context node.
    """
    index={}
    for occurrence in root.allOccurrences:
        path=occurrence.fullPathName
        if path in index:raise ValueError('Duplicate full occurrence path '+path)
        index[path]=occurrence
    canonical={};nodes={}
    for key,occurrence in supplied.items():
        path=occurrence.fullPathName
        if path not in index:raise ValueError(key+': occurrence is not in the root assembly context')
        node=index[path]
        if node.sourceComponent!=root:
            raise ValueError(key+': root occurrence enumeration did not return root source context')
        canonical[key]=node
        for ancestor_path,ancestor in index.items():
            if path==ancestor_path or path.startswith(ancestor_path+'+'):
                if ancestor.sourceComponent!=root:
                    raise ValueError(ancestor_path+': ancestor is not in root source context')
                nodes[ancestor_path]=ancestor
    ordered=[nodes[path] for path in sorted(nodes,key=lambda p:(-len(p),p))]
    return canonical,ordered


def _make_datum(parent_occurrence, joint, core):
    """Create fixed native sketch geometry attached to the parent link.

    The sketch plane normal defines joint Z. The first live fixture showed
    that the prior custom sketch-line input rotated about the sketch normal
    instead of the requested line, so the normal is now the intended axis.
    """
    component = parent_occurrence.component
    inverse = inverse_rigid(as_matrix(parent_occurrence.transform2))
    centre = point(inverse, [v/10 for v in joint['centre_world_mm']])
    axis = unit(direction(inverse, joint['axis_world']))
    planes = [component.xYConstructionPlane, component.xZConstructionPlane, component.yZConstructionPlane]
    candidates = []
    for plane in planes:
        geo = plane.geometry
        normal = unit([geo.normal.x, geo.normal.y, geo.normal.z])
        candidates.append((1-abs(dot(normal, axis)), plane, normal, [geo.origin.x, geo.origin.y, geo.origin.z]))
    deviation, base, normal, origin = min(candidates, key=lambda x:x[0])
    if deviation > 1e-7:
        raise ValueError(joint['name']+': axis is not normal to a supported parent-component principal plane')
    distance = dot(normal, [centre[i]-origin[i] for i in range(3)])
    plane_input = component.constructionPlanes.createInput()
    _require(plane_input.setByOffset(base, core.ValueInput.createByReal(distance)), 'Datum plane input failed')
    plane = _require(component.constructionPlanes.add(plane_input), 'Datum plane creation failed')
    plane.name = 'MIST_'+joint['name']+'_datum_plane'
    sketch = _require(component.sketches.add(plane), 'Datum sketch creation failed')
    sketch.name = 'MIST_'+joint['name']+'_axis_sketch'
    sketch_point = sketch.modelToSketchSpace(core.Point3D.create(*centre))
    if abs(sketch_point.z) > 1e-7:
        raise RuntimeError('Joint datum did not lie on its parametric sketch plane')
    native_point = _require(sketch.sketchPoints.add(sketch_point), 'Datum sketch point creation failed')
    native_point.isFixed = True
    if not native_point.isFixed:
        raise RuntimeError('Datum point did not become fixed')
    plane.isLightBulbOn = False
    sketch.isLightBulbOn = False
    point_proxy = _require(native_point.createForAssemblyContext(parent_occurrence), 'Point assembly proxy failed')
    return point_proxy, dict(definition='parent_sketch_normal_standard_joint_Z',
                             requested_axis_local=axis,sketch_normal_local=normal,
                             normal_dot_requested_axis=dot(normal,axis))


def refresh_joint_drive():
    """Update a temporary Drive Joints pose without recomputing its as-built zero.

    Live Fusion evidence showed Compute All resets rotationValue to the saved
    as-built value. Event/viewport refresh preserves the driven pose.
    """
    import adsk
    import adsk.core
    adsk.doEvents()
    result=adsk.core.Application.get().activeViewport.refresh()
    if result is False:
        raise RuntimeError('Joint drive viewport refresh failed')


def _probe(design, motion, parent, child, joint):
    value = float(motion.rotationValue)
    before_parent, before_child = as_matrix(parent.transform2), as_matrix(child.transform2)
    # The live setter rounded 0.001 rad to exactly 0.1 degree. Probe at that
    # explicitly representable increment; retain the original strict checks.
    delta = math.radians(.1)
    try:
        motion.rotationValue = value+delta
        refresh_joint_drive()
        result = verify_probe(before_parent, before_child, as_matrix(parent.transform2), as_matrix(child.transform2),
                              [v/10 for v in joint['centre_world_mm']], joint['axis_world'], delta)
    finally:
        motion.rotationValue = value
        refresh_joint_drive()
        _compute(design)
    restored_parent, restored_child = as_matrix(parent.transform2), as_matrix(child.transform2)
    if matrix_error(before_parent, restored_parent) > 1e-6 or matrix_error(before_child, restored_child) > 1e-6:
        raise RuntimeError(joint['name']+': native direction probe did not restore the assembled pose')
    result['initial_fusion_value_rad'] = value
    result['assembled_pose_restored'] = True
    result['drive_pose_is_transient'] = True
    result['compute_all_after_restoration_only'] = True
    return result


def apply_motion_plan(design, plan, occurrences, report_path, *, namespace='MIST_motion_v1'):
    """Create native rigid groups and as-built joints in a newly built design.

    This intentionally grounds one chassis leaf, clears grounding on the
    supplied moving leaves/containers, and probes/restores 0.1 degree per joint.
    A failed creation writes a partial report and raises. It never authenticates
    Fusion, opens a document, exports a release, or suppresses solver errors.
    """
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = dict(schema_version=SCHEMA, status='preflight', native_execution=False,
                  native_joint_creation_complete=False, transmission_mates_created=False,
                  full_motion_verified=False, full_ROM_checked=False,
                  plan_sha256=plan['plan_sha256'], joint_records=[], rigid_groups=[],
                  fixed_phase_rotor_attachments=[], grounding_changes=[], errors=[],
                  started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    _write(report_path, report)
    try:
        import adsk.core as core
        import adsk.fusion as fusion
        root = design.rootComponent
        payload = {key:value for key,value in plan.items() if key != 'plan_sha256'}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()
        if digest != plan['plan_sha256']:
            raise ValueError('Motion plan changed after its hash was generated')
        if design.designType != fusion.DesignTypes.ParametricDesignType:
            raise ValueError('The helper requires the existing parametric Fusion design')
        if root.attributes.itemByName(namespace, 'status'):
            raise ValueError('This motion namespace has already been used; rebuild in a new document to avoid duplicate constraints')
        expected = set(plan['parts'])
        if expected != set(occurrences):
            raise ValueError('Occurrence map must match the plan exactly; missing='+str(sorted(expected-set(occurrences)))+
                             ', extra='+str(sorted(set(occurrences)-expected)))
        occurrences,grounding_nodes=root_context_grounding_nodes(root,occurrences)
        for key, occurrence in occurrences.items():
            if not occurrence or not occurrence.isValid:
                raise ValueError(key+': invalid occurrence')
            if occurrence.component.occurrences.count:
                raise ValueError(key+': expected a leaf occurrence, not a container')
        paths = [occurrence.fullPathName for occurrence in occurrences.values()]
        if len(paths) != len(set(paths)):
            raise ValueError('One occurrence was assigned to multiple part keys')
        root.attributes.add(namespace, 'status', 'started')
        report['native_execution'] = True
        report['status'] = 'creating_rigid_groups'
        report['grounding_scope']='Bindings and ancestors canonicalized through root.allOccurrences; sourceComponent==root required before pin access.'
        for node in grounding_nodes:
            old = dict(path=node.fullPathName, isGrounded=bool(node.isGrounded), isGroundToParent=bool(node.isGroundToParent))
            node.isGrounded = False
            node.isGroundToParent = False
            if old['isGrounded'] or old['isGroundToParent']:
                report['grounding_changes'].append(old)
        representatives = {}
        for group, keys in plan['groups'].items():
            representatives[group] = occurrences[keys[0]]
            collection = core.ObjectCollection.create()
            for key in keys:
                collection.add(occurrences[key])
            if len(keys) > 1:
                rigid = _require(root.rigidGroups.add(collection, False), 'Rigid group creation failed: '+group)
                rigid.name = namespace+'_'+group.replace('/', '_')
            report['rigid_groups'].append(dict(group=group, part_count=len(keys), include_children=False,
                                                representative=keys[0], native_group_created=len(keys)>1))
        representatives['body'].isGrounded = True
        report['grounded_body_representative'] = representatives['body'].fullPathName
        # Input rotors follow their housing with phase held. This is an explicit
        # animation approximation, not a gear train or belt simulation.
        for rotor, parent_group in plan['fixed_phase_rotor_attachments'].items():
            joint_input = _require(root.asBuiltJoints.createInput(representatives[rotor], representatives[parent_group], None), 'Rotor rigid-joint input failed')
            _require(joint_input.setAsRigidJointMotion(), 'Rotor rigid-joint motion failed')
            rigid = _require(root.asBuiltJoints.add(joint_input), 'Rotor phase attachment failed')
            rigid.name = namespace+'_'+rotor.replace('/', '_')+'_fixed_phase_preview'
            report['fixed_phase_rotor_attachments'].append(dict(group=rotor, housing=parent_group, native_joint=rigid.name))
        _compute(design)
        for joint in plan['joints']:
            record = dict(joint, status='creating')
            report['joint_records'].append(record)
            parent = representatives[joint['parent_group']]
            child = representatives[joint['child_group']]
            point_proxy, datum_definition = _make_datum(parent, joint, core)
            geometry = _require(fusion.JointGeometry.createByPoint(point_proxy), 'Joint geometry creation failed')
            joint_input = _require(root.asBuiltJoints.createInput(child, parent, geometry), 'As-built joint input failed')
            _require(joint_input.setAsRevoluteJointMotion(fusion.JointDirections.ZAxisJointDirection), 'Revolute motion input failed')
            native = _require(root.asBuiltJoints.add(joint_input), 'Native as-built revolute creation failed')
            native.name = namespace+'_'+joint['name']
            motion = _require(fusion.RevoluteJointMotion.cast(native.jointMotion), 'Created joint was not revolute')
            limits = motion.rotationLimits
            limits.isMinimumValueEnabled = False
            limits.isMaximumValueEnabled = False
            limits.isRestValueEnabled = False
            _compute(design)
            probe = _probe(design, motion, parent, child, joint)
            if joint['physical_limits_deg'] is not None:
                mapped = map_limits(probe['initial_fusion_value_rad'], joint['built_physical_deg'], joint['physical_limits_deg'], probe['sign'])
                limits.minimumValue, limits.maximumValue = mapped
                limits.isMinimumValueEnabled = True
                limits.isMaximumValueEnabled = True
            else:
                mapped = None
            _compute(design)
            axis = motion.rotationAxisVector
            record.update(status='created_and_direction_checked', native_name=native.name,
                          datum_definition=datum_definition,
                          probe=probe, native_rotation_limits_rad=mapped,
                          native_axis_vector=[axis.x, axis.y, axis.z] if axis else None,
                          native_axis_vector_context_not_assumed=True,
                          native_is_valid=bool(native.isValid), native_is_suppressed=bool(native.isSuppressed))
            _write(report_path, report)
        report.update(status='native_motion_rig_created', native_joint_creation_complete=True,
                      created_revolute_count=len(report['joint_records']),
                      native_validation_scope='Creation, 0.1 degree transient direction/centre probes and pose restoration only; not full ROM or collision validation.')
        root.attributes.itemByName(namespace, 'status').value = 'completed'
        _write(report_path, report)
        return report
    except Exception:
        report.update(status='native_motion_rig_failed')
        report['errors'].append(traceback.format_exc())
        _write(report_path, report)
        raise


def rig_build_results(design, parameters, body_result, leg_results, output_directory, *, group_overrides=None):
    """Integration call after the existing body and leg native builders return."""
    out = Path(output_directory)
    out.mkdir(parents=True, exist_ok=True)
    plan = build_motion_plan(parameters, body_result['spec'], [r['spec'] for r in leg_results], group_overrides=group_overrides)
    _write(out/'motion_plan.json', plan)
    occurrences = resolve_occurrences(design.rootComponent, body_result, leg_results)
    return apply_motion_plan(design, plan, occurrences, out/'native_motion_report.json')
