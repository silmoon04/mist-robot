"""Observe a drive in the failed test fixture without weakening joint checks.

The root agent runs this inside Fusion. It reuses the marked TEST fixture,
restores the original angle, and reactivates the untouched MIST body document.
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


def _load(name,path):
    raw=path.read_bytes()
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module,hashlib.sha256(raw).hexdigest()


def _write(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')


def run(context=None):
    import adsk
    import adsk.core as core
    import adsk.fusion as fusion
    app=core.Application.get()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=HERE/'joint_drive_diagnostics'/stamp;output.mkdir(parents=True)
    report=dict(status='diagnostic_started',test_only=True,stages=[],errors=[],tolerances_unchanged=True)
    motion,motion_sha=_load('mist_joint_drive_diagnostic_motion',CAD/'fusion_motion_20260907/motion.py')
    fixture,fixture_sha=_load('mist_joint_drive_diagnostic_fixture',HERE/'joint_fixture.py')
    report['source_sha256']=dict(motion=motion_sha,fixture=fixture_sha,diagnostic=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    body_document=None;body_design=None;design=None;cached_motion=None;initial=None
    before_parent=None;before_child=None;body_before=None
    _write(output/'diagnostic.json',report)
    try:
        manifest=json.loads((HERE/'last_joint_fixture.json').read_text())
        failed=json.loads((Path(manifest['directory'])/'fixture_report.json').read_text())
        target_name=failed['fixture_document']
        if not target_name.startswith('MIST JOINT FIXTURE TEST ONLY '):raise RuntimeError('Refusing to drive a non-test document')
        report['fixture_document']=target_name;report['failed_fixture_run']=manifest['directory']
        docs=[app.documents.item(i) for i in range(app.documents.count)]
        body_matches=[doc for doc in docs if doc.name==fixture.BODY_DOCUMENT_NAME]
        target_matches=[doc for doc in docs if doc.name==target_name]
        if len(body_matches)!=1 or len(target_matches)!=1:raise RuntimeError('Expected one body and one failed fixture document')
        body_document=body_matches[0]
        fixture._require(body_document.activate(),'Could not activate body for initial fingerprint')
        body_design=fusion.Design.cast(app.activeProduct)
        body_before=fixture._fingerprint(body_design,motion)
        fixture._require(target_matches[0].activate(),'Could not activate test fixture')
        design=fixture._require(fusion.Design.cast(app.activeProduct),'Fixture has no design')
        root=design.rootComponent
        name='MIST_fixture_motion_FL_yaw'
        joint=fixture._require(root.asBuiltJoints.itemByName(name),'First fixture joint not found')
        parent=joint.occurrenceTwo;child=joint.occurrenceOne
        cached_motion=fusion.RevoluteJointMotion.cast(joint.jointMotion)
        initial=float(cached_motion.rotationValue)
        delta=.001
        plan=json.loads((Path(manifest['directory'])/'motion_plan.json').read_text())
        record=next(row for row in plan['joints'] if row['name']=='FL_yaw')
        centre=[v/10 for v in record['centre_world_mm']];axis=record['axis_world']
        before_parent=motion.as_matrix(parent.transform2);before_child=motion.as_matrix(child.transform2)
        report.update(joint=name,initial_rotation_rad=initial,requested_delta_rad=delta,
                      parent=parent.fullPathName,child=child.fullPathName,
                      body_before=body_before,limits=dict(minimum_enabled=cached_motion.rotationLimits.isMinimumValueEnabled,
                      maximum_enabled=cached_motion.rotationLimits.isMaximumValueEnabled))

        def capture(label,api_result=None):
            fresh=root.asBuiltJoints.itemByName(name)
            fresh_motion=fusion.RevoluteJointMotion.cast(fresh.jointMotion)
            p=motion.as_matrix(fresh.occurrenceTwo.transform2)
            c=motion.as_matrix(fresh.occurrenceOne.transform2)
            relative_before=motion.mmul(motion.inverse_rigid(before_parent),before_child)
            relative_now=motion.mmul(motion.inverse_rigid(p),c)
            change=motion.mmul(relative_now,motion.inverse_rigid(relative_before))
            axis_local=motion.unit(motion.direction(motion.inverse_rigid(before_parent),axis))
            skew=[(change[2][1]-change[1][2])/2,(change[0][2]-change[2][0])/2,(change[1][0]-change[0][1])/2]
            angle=math.atan2(motion.dot(axis_local,skew),(sum(change[i][i] for i in range(3))-1)/2)
            row=dict(stage=label,api_result=api_result,cached_rotation_rad=float(cached_motion.rotationValue),
                     fresh_rotation_rad=float(fresh_motion.rotationValue),observed_relative_rotation_rad=angle,
                     parent_transform=p,child_transform=c,relative_change=change,
                     pending_snapshot=bool(design.snapshots.hasPendingSnapshot),
                     parent_grounded=bool(fresh.occurrenceTwo.isGrounded),child_grounded=bool(fresh.occurrenceOne.isGrounded),
                     parent_ground_to_parent=bool(fresh.occurrenceTwo.isGroundToParent),
                     child_ground_to_parent=bool(fresh.occurrenceOne.isGroundToParent))
            try:
                row['original_probe_check']=dict(passed=True,result=motion.verify_probe(before_parent,before_child,p,c,centre,axis,delta))
            except Exception as error:
                row['original_probe_check']=dict(passed=False,error=str(error))
            report['stages'].append(row);_write(output/'diagnostic.json',report)
            return row

        capture('baseline')
        cached_motion.rotationValue=initial+delta
        capture('immediately_after_set')
        events=adsk.doEvents()
        capture('after_doEvents',events)
        refreshed=app.activeViewport.refresh()
        capture('after_viewport_refresh',refreshed)
        computed=design.computeAll()
        capture('after_ComputeAll',computed)
        adsk.doEvents();app.activeViewport.refresh()
        capture('after_ComputeAll_and_UI_refresh')
        report['status']='joint_drive_diagnostic_complete'
        report['interpretation']='Read the staged raw angle and transform results; this diagnostic does not relax checks or assume a reset.'
    except Exception:
        report['status']='joint_drive_diagnostic_failed';report['errors'].append(traceback.format_exc())
    finally:
        if cached_motion is not None and initial is not None:
            try:
                cached_motion.rotationValue=initial
                adsk.doEvents();app.activeViewport.refresh()
                if design.computeAll() is False:raise RuntimeError('Restore Compute All failed')
                p=motion.as_matrix(parent.transform2);c=motion.as_matrix(child.transform2)
                report['restoration']=dict(rotation_rad=float(cached_motion.rotationValue),
                    parent_error=motion.matrix_error(before_parent,p),child_error=motion.matrix_error(before_child,c))
                if max(report['restoration']['parent_error'],report['restoration']['child_error'])>1e-6:
                    raise RuntimeError('Diagnostic did not restore the original test pose')
            except Exception:
                report['status']='joint_drive_diagnostic_failed';report['errors'].append(traceback.format_exc())
        if body_document:
            try:
                report['body_reactivated']=bool(body_document.activate())
                if not report['body_reactivated']:raise RuntimeError('Body reactivation failed')
                report['body_after']=fixture._fingerprint(body_design,motion)
                report['body_unchanged']=body_before==report['body_after']
                if not report['body_unchanged']:raise RuntimeError('Body fingerprint changed')
            except Exception:
                report['status']='joint_drive_diagnostic_failed';report['errors'].append(traceback.format_exc())
        _write(output/'diagnostic.json',report)
        _write(HERE/'last_joint_drive_diagnostic.json',dict(directory=str(output),status=report['status'],report='diagnostic.json'))
        app.log('MIST joint drive diagnostic: '+report['status']+'; '+str(output/'diagnostic.json'))
    return report
