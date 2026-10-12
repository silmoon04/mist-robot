"""Small native 17-component / 16-joint test. Run only inside Fusion.

Creates a NEW marked test document, never builds into the existing MIST body.
The body document is reactivated in finally. Only the root agent runs this.
"""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import math
import sys
import traceback

HERE=Path(__file__).resolve().parent
CAD=HERE.parent
ROOT=CAD.parent
BODY_DOCUMENT_NAME='MIST concealed wheel drive - native assembly'


def _load(name,path):
    raw=path.read_bytes()
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    exec(compile(raw,str(path),'exec'),module.__dict__)
    module.__fixture_source_sha256__=hashlib.sha256(raw).hexdigest()
    return module


def _write(path,report):
    path.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')


def _frame(heading, pitch=0., origin=(0.,0.,0.)):
    a,b=math.radians(heading),math.radians(-pitch)
    ca,sa,cb,sb=math.cos(a),math.sin(a),math.cos(b),math.sin(b)
    return [[ca*cb,-sa,ca*sb,origin[0]], [sa*cb,ca,sa*sb,origin[1]],
            [-sb,0,cb,origin[2]], [0.,0.,0.,1.]]


def _point(frame,p):
    return [sum(frame[i][j]*p[j] for j in range(3))+frame[i][3] for i in range(3)]


def fixture_specifications(params,coordinates=None):
    g=params['geometry'];length=g['femur_m']*1000;tibia=g['tibia_m']*1000
    reach=g['drive_radial_reach_from_pitch_m']*1000;down=g['hip_to_wheel_axle_height_m']*1000
    knee=-math.acos((reach*reach+down*down-length*length-tibia*tibia)/(2*length*tibia))
    hip=math.atan2(reach,down)-math.atan2(tibia*math.sin(knee),length+tibia*math.cos(knee))
    specs=[]
    for i,leg in enumerate(g['leg_names']):
        az=g['mount_azimuths_deg'][i]
        q=list((coordinates or {}).get(leg,[g['drive_heading_deg'][i]-az,math.degrees(hip),math.degrees(knee)]))
        heading=az+q[0]
        origin=[g['hip_mount_radius_m']*1000*math.cos(math.radians(az)),g['hip_mount_radius_m']*1000*math.sin(math.radians(az)),0.]
        co=[g['hip_radial_offset_m']*1000,g['hip_transverse_offset_m']*1000*[1,-1,-1,1][i],0.]
        yaw=_frame(heading,origin=origin);pitch_point=_point(yaw,co)
        femur=_frame(heading,q[1],pitch_point);knee_point=_point(femur,[0,0,-length])
        tibia_frame=_frame(heading,q[1]+q[2],knee_point);wheel_point=_point(tibia_frame,[0,0,-tibia])
        frames=dict(yaw=yaw,femur=femur,tibia=tibia_frame,wheel=_frame(heading,q[1]+q[2],wheel_point))
        specs.append(dict(leg_name=leg,pose_deg=dict(yaw=q[0],hip=q[1],knee=q[2],heading=heading),
                          joint_centers_world_mm=dict(yaw=origin,hip=pitch_point,knee=knee_point,wheel=wheel_point),
                          frames_world_mm=frames,
                          parts=[dict(name=link,link=link,rigid_group=link,transform=frames[link]) for link in frames]))
    return dict(parts=[dict(name='TEST_chassis',rigid_group='body')]),specs


def _require(value,label):
    if value is False or value is None:raise RuntimeError(label)
    return value


def _fingerprint(design,motion):
    root=design.rootComponent
    return dict(timeline_count=design.timeline.count,occurrence_count=root.allOccurrences.count,
                occurrences={o.fullPathName:motion.as_matrix(o.transform2) for o in root.allOccurrences},
                body_count=sum(o.component.bRepBodies.count for o in root.allOccurrences))


def _world_check(root,occurrences,expected,motion,namespace):
    checks=[]
    for spec in expected:
        leg=spec['leg_name']
        for link,frame_mm in spec['frames_world_mm'].items():
            target=[[v/10 if j==3 and i<3 else v for j,v in enumerate(row)] for i,row in enumerate(frame_mm)]
            actual=motion.as_matrix(occurrences[leg+'/'+link].transform2)
            error=motion.matrix_error(target,actual)
            checks.append(dict(kind='occurrence_transform',part=leg+'/'+link,max_matrix_error_cm=error,passed=error<1e-5))
        for name,centre in spec['joint_centers_world_mm'].items():
            joint=_require(root.asBuiltJoints.itemByName(namespace+'_'+leg+'_'+name),'Missing native joint '+leg+'_'+name)
            origin=joint.geometry.origin
            error=math.sqrt(sum((value*10-centre[i])**2 for i,value in enumerate([origin.x,origin.y,origin.z])))
            checks.append(dict(kind='joint_world_origin',joint=leg+'_'+name,error_mm=error,passed=error<.01,
                               expected_mm=centre,actual_mm=[origin.x*10,origin.y*10,origin.z*10]))
    return checks


def run(context=None):
    import adsk.core as core
    import adsk.fusion as fusion
    app=core.Application.get()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=HERE/'joint_fixture_runs'/stamp
    output.mkdir(parents=True)
    report=dict(status='started',test_only=True,production_geometry=False,native_execution=True,
                intended_components=17,intended_main_joints=16,full_ROM_verified=False,
                full_robot_motion_verified=False,errors=[],reactivated_body=False)
    _write(output/'fixture_report.json',report)
    body_document=None;body_design=None;fixture_document=None
    try:
        matches=[app.documents.item(i) for i in range(app.documents.count) if app.documents.item(i).name==BODY_DOCUMENT_NAME]
        if len(matches)!=1:raise RuntimeError('Expected exactly one existing body document named '+BODY_DOCUMENT_NAME)
        body_document=matches[0]
        _require(body_document.activate(),'Could not activate preserved body document')
        body_design=_require(fusion.Design.cast(app.activeProduct),'Body document has no design')
        native=_load('mist_fixture_native_parts',CAD/'native_parts.py')
        motion=_load('mist_fixture_motion',CAD/'fusion_motion_20260907/motion.py')
        report['source_sha256']={'native_parts.py':native.__fixture_source_sha256__,'motion.py':motion.__fixture_source_sha256__,
                                 'joint_fixture.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        report['preserved_body_before']=_fingerprint(body_design,motion)
        params=json.loads((ROOT/'simulation/design_parameters_20260907.json').read_text())
        body_spec,specs=fixture_specifications(params)
        plan=motion.build_motion_plan(params,body_spec,specs)
        _write(output/'parameters.json',params);_write(output/'motion_plan.json',plan);_write(output/'fixture_specs.json',specs)
        fixture_document=app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
        fixture_document.name='MIST JOINT FIXTURE TEST ONLY '+stamp
        design=_require(fusion.Design.cast(app.activeProduct),'Fixture document has no design')
        design.designType=fusion.DesignTypes.ParametricDesignType
        root=design.rootComponent;root.attributes.add('MIST','build_role','TEST_ONLY_17_COMPONENTS_16_JOINTS')
        occurrences={}
        body=root.occurrences.addNewComponent(core.Matrix3D.create())
        body.component.name='TEST_chassis'
        native.box(body.component,'TEST_chassis_box',[0,0,50],[160,160,40])
        native.place_occurrence(body,core.Matrix3D.create())
        occurrences['body/TEST_chassis']=body
        for spec in specs:
            leg=spec['leg_name']
            for part in spec['parts']:
                link=part['name'];occ=root.occurrences.addNewComponent(core.Matrix3D.create())
                occ.component.name='TEST_'+leg+'_'+link
                if link=='yaw':native.box(occ.component,'TEST_yaw_block',[17.5,0,0],[35,12,12])
                elif link=='femur':native.box(occ.component,'TEST_femur_bar',[0,0,-params['geometry']['femur_m']*500],[10,10,params['geometry']['femur_m']*1000])
                elif link=='tibia':native.box(occ.component,'TEST_tibia_bar',[0,0,-params['geometry']['tibia_m']*500],[8,8,params['geometry']['tibia_m']*1000])
                else:native.box(occ.component,'TEST_wheel_marker',[0,0,0],[30,8,30])
                matrix=core.Matrix3D.create()
                for i in range(4):
                    for j in range(4):matrix.setCell(i,j,part['transform'][i][j]/10 if j==3 and i<3 else part['transform'][i][j])
                native.place_occurrence(occ,matrix)
                occurrences[leg+'/'+link]=occ
        _require(design.computeAll(),'Fixture Compute All failed after placement')
        report.update(status='fixture_components_created',fixture_document=fixture_document.name,
                      actual_components=len(occurrences),actual_solids=sum(o.component.bRepBodies.count for o in occurrences.values()))
        for spec in specs:
            for link,frame in spec['frames_world_mm'].items():
                wanted=[[v/10 if j==3 and i<3 else v for j,v in enumerate(row)] for i,row in enumerate(frame)]
                if motion.matrix_error(motion.as_matrix(occurrences[spec['leg_name']+'/'+link].transform2),wanted)>1e-6:
                    raise RuntimeError('Placement changed on Compute All: '+spec['leg_name']+'/'+link)
        _write(output/'fixture_report.json',report)
        namespace='MIST_fixture_motion'
        native_report=motion.apply_motion_plan(design,plan,occurrences,output/'native_motion_report.json',namespace=namespace)
        report['native_motion_report']=native_report
        report['baseline_world_checks']=_world_check(root,occurrences,specs,motion,namespace)
        if not all(c['passed'] for c in report['baseline_world_checks']):raise RuntimeError('Baseline joint world datum or component transform check failed')
        _write(output/'fixture_report.json',report)
        # Drive one complete chain after all16 joints exist. This checks that
        # downstream datums follow yaw and hip rather than remaining in world.
        values={spec['leg_name']:[spec['pose_deg'][key] for key in ['yaw','hip','knee']] for spec in specs}
        values['FL']=[values['FL'][0]+5,values['FL'][1]+4,values['FL'][2]-3]
        driven=[]
        try:
            for name,target in zip(['FL_yaw','FL_hip','FL_knee'],values['FL']):
                row=next(r for r in native_report['joint_records'] if r['name']==name)
                joint=root.asBuiltJoints.itemByName(row['native_name'])
                jm=fusion.RevoluteJointMotion.cast(joint.jointMotion)
                driven.append((jm,float(jm.rotationValue)))
                jm.rotationValue=row['probe']['initial_fusion_value_rad']+row['probe']['sign']*math.radians(target-row['built_physical_deg'])
                _require(design.computeAll(),'Upstream drive Compute All failed')
            _,expected=fixture_specifications(params,values)
            report['upstream_drive_world_checks']=_world_check(root,occurrences,expected,motion,namespace)
            if not all(c['passed'] for c in report['upstream_drive_world_checks']):raise RuntimeError('Downstream datums or links failed after upstream motion')
        finally:
            for jm,value in reversed(driven):jm.rotationValue=value
            _require(design.computeAll(),'Fixture restoration Compute All failed')
        report['restoration_world_checks']=_world_check(root,occurrences,specs,motion,namespace)
        if not all(c['passed'] for c in report['restoration_world_checks']):raise RuntimeError('Full fixture baseline was not restored')
        report['native_revolute_count']=len(native_report['joint_records'])
        report['created_rigid_groups']=design.rootComponent.rigidGroups.count
        report['rigid_group_scope']='One component per structural link; multi-part rigid grouping is not exercised by this small fixture.'
        target=output/'MIST_JOINT_FIXTURE_TEST_ONLY.f3d'
        exporter=design.exportManager
        _require(exporter.execute(exporter.createFusionArchiveExportOptions(str(target))),'Fixture F3D export failed')
        report.update(status='native_fixture_passed',archive=str(target),fixture_joint_checks_verified=True)
    except Exception:
        report['status']='native_fixture_failed';report['errors'].append(traceback.format_exc())
    finally:
        if body_document:
            try:
                report['reactivated_body']=bool(body_document.activate())
                if not report['reactivated_body']:raise RuntimeError('Could not reactivate preserved body document')
                if body_design and 'motion' in locals():
                    report['preserved_body_after']=_fingerprint(body_design,motion)
                    report['preserved_body_unchanged']=report.get('preserved_body_before')==report['preserved_body_after']
                    if not report['preserved_body_unchanged']:raise RuntimeError('Preserved body fingerprint changed')
            except Exception:
                report['status']='native_fixture_failed';report['errors'].append(traceback.format_exc())
        _write(output/'fixture_report.json',report)
        _write(HERE/'last_joint_fixture.json',dict(directory=str(output),report='fixture_report.json',status=report['status']))
        app.log('MIST joint fixture: '+report['status']+'; report='+str(output/'fixture_report.json'))
    return report
