"""Small component-mirror and paired-clone diagnostic; root owns live execution.

Only a new marked test document is modified. Two asymmetric nested parts use
root-context placement overrides. Raw clone behavior is recorded before any
explicit leaf-placement repair, so failed inheritance is never hidden.
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
BODY_DOCUMENT_NAME='MIST concealed wheel drive - native assembly'


def load(name,path):
    raw=path.read_bytes();spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module,hashlib.sha256(raw).hexdigest()


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')


def require(value,message):
    if value is False or value is None:raise RuntimeError(message)
    return value


def determinant(matrix):
    r=matrix
    return r[0][0]*(r[1][1]*r[2][2]-r[1][2]*r[2][1])-r[0][1]*(r[1][0]*r[2][2]-r[1][2]*r[2][0])+r[0][2]*(r[1][0]*r[2][1]-r[1][1]*r[2][0])


def frame(yaw=0,pitch=0,at=(0,0,0)):
    a,b=math.radians(yaw),math.radians(pitch);ca,sa,cb,sb=math.cos(a),math.sin(a),math.cos(b),math.sin(b)
    return [[ca*cb,-sa,ca*sb,at[0]/10],[sa*cb,ca,sa*sb,at[1]/10],[-sb,0,cb,at[2]/10],[0,0,0,1]]


def native_matrix(rows,core):
    m=core.Matrix3D.create()
    for i in range(4):
        for j in range(4):m.setCell(i,j,rows[i][j])
    return m


def attributes(entity):
    return [dict(group=a.groupName,name=a.name,value=a.value) for a in (entity.attributes.item(i) for i in range(entity.attributes.count))]


def bounds(body):
    b=body.boundingBox
    return [[b.minPoint.x*10,b.minPoint.y*10,b.minPoint.z*10],[b.maxPoint.x*10,b.maxPoint.y*10,b.maxPoint.z*10]]


def collect(root,top,motion):
    prefix=top.fullPathName;result=[]
    for occurrence in root.allOccurrences:
        path=occurrence.fullPathName
        if path!=prefix and not path.startswith(prefix+'+'):continue
        if occurrence.component.occurrences.count:continue
        for native_body in occurrence.component.bRepBodies:
            proxy=require(native_body.createForAssemblyContext(occurrence),'Body root proxy failed')
            matrix=motion.as_matrix(occurrence.transform2)
            local_com=native_body.physicalProperties.centerOfMass
            world_com=motion.point(matrix,[local_com.x,local_com.y,local_com.z])
            proxy_com=proxy.physicalProperties.centerOfMass
            result.append(dict(path=path,relative_path=path[len(prefix):].lstrip('+'),
                occurrence_name=occurrence.name,component_name=occurrence.component.name,body_name=native_body.name,
                source_is_root=occurrence.sourceComponent==root,
                transform_cm=matrix,rotation_determinant=determinant(matrix),
                local_bounds_mm=bounds(native_body),world_bounds_mm=bounds(proxy),
                local_com_mm=[local_com.x*10,local_com.y*10,local_com.z*10],
                world_com_mm=[v*10 for v in world_com],
                proxy_physical_com_reported_mm=[proxy_com.x*10,proxy_com.y*10,proxy_com.z*10],
                volume_mm3=proxy.volume*1000,solid=bool(proxy.isSolid),
                occurrence_attributes=attributes(occurrence),component_attributes=attributes(occurrence.component),
                body_attributes=attributes(native_body),component=occurrence.component,occurrence=occurrence))
    return result


def serial(rows):return [{k:v for k,v in r.items() if k not in ('component','occurrence')} for r in rows]


def transformed_bounds(b,kind):
    lo,hi=b
    if kind=='identity':return [list(lo),list(hi)]
    if kind=='mirror_y':return [[lo[0],-hi[1],lo[2]],[hi[0],-lo[1],hi[2]]]
    return [[-hi[0],-hi[1],lo[2]],[-lo[0],-lo[1],hi[2]]]


def compare(source,result,kind):
    # Fixture volumes intentionally differ. This is diagnostic matching only,
    # not a proposed identity scheme for a real leg with identical bearings.
    matches=[];remaining=list(result)
    for original in source:
        candidates=[r for r in remaining if abs(r['volume_mm3']-original['volume_mm3'])<1e-5]
        if len(candidates)!=1:
            matches.append(dict(source=original['path'],passed=False,error='Fixture volume correspondence is not unique'));continue
        found=candidates[0];remaining.remove(found)
        expected=transformed_bounds(original['world_bounds_mm'],kind)
        bbox_error=max(abs(expected[i][j]-found['world_bounds_mm'][i][j]) for i in range(2) for j in range(3))
        c=original['world_com_mm'];expected_com=(list(c) if kind=='identity' else ([c[0],-c[1],c[2]] if kind=='mirror_y' else [-c[0],-c[1],c[2]]))
        com_error=max(abs(expected_com[i]-found['world_com_mm'][i]) for i in range(3))
        matches.append(dict(source=original['path'],result=found['path'],bounds_error_mm=bbox_error,com_error_mm=com_error,
                            shares_component_definition=found['component']==original['component'],
                            proper_rotation=abs(found['rotation_determinant']-1)<1e-6,
                            passed=bbox_error<1e-4 and com_error<1e-4))
    return dict(matches=matches,extra_results=len(remaining),passed=bool(matches) and len(source)==len(result) and all(r['passed'] for r in matches))


def run(context=None):
    import adsk.core as core
    import adsk.fusion as fusion
    app=core.Application.get();stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=HERE/'mirror_fixture_runs'/stamp;output.mkdir(parents=True)
    report=dict(status='started',test_only=True,errors=[],main_document_unchanged=False)
    write(output/'report.json',report)
    body_document=None;body_design=None;body_before=None;distance_parameter=None;original_distance=None
    try:
        fixture,fs=load('mist_mirror_fixture_shared',HERE/'joint_fixture.py')
        motion,ms=load('mist_mirror_fixture_math',CAD/'fusion_motion_20260907/motion.py')
        native,ns=load('mist_mirror_fixture_native',CAD/'native_parts.py')
        report['source_sha256']=dict(fixture=fs,motion=ms,native_parts=ns,mirror_fixture=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        docs=[app.documents.item(i) for i in range(app.documents.count)]
        matches=[d for d in docs if d.name==BODY_DOCUMENT_NAME]
        if len(matches)!=1:raise RuntimeError('Expected exactly one existing MIST body document')
        body_document=matches[0];require(body_document.activate(),'Body activation failed')
        body_design=require(fusion.Design.cast(app.activeProduct),'Body has no design')
        body_before=fixture._fingerprint(body_design,motion)
        doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);doc.name='MIST MIRROR FIXTURE TEST ONLY '+stamp
        design=require(fusion.Design.cast(app.activeProduct),'Test document has no design')
        design.designType=fusion.DesignTypes.ParametricDesignType;root=design.rootComponent
        root.attributes.add('MIST','build_role','MIRROR_AND_CLONE_TEST_ONLY')
        source=root.occurrences.addNewComponent(core.Matrix3D.create());source.component.name='TEST_SOURCE_LEG'
        source.attributes.add('MIST_fixture','leg','FL')
        native.place_occurrence(source,native_matrix(frame(7,at=(13,11,0)),core))
        a=source.component.occurrences.addNewComponent(core.Matrix3D.create());a.component.name='TEST_PART_A'
        b0=native.box(a.component,'A_chiral_block',(2,1,-1),(14,10,8))
        cut=native.box(a.component,'A_corner_notch',(8,5,2),(5,4,4))
        body_a=native.subtract(a.component,b0,[cut],'A_notched_body');body_a.name='TEST_BODY_A'
        a_context=a.createForAssemblyContext(source)
        native.place_occurrence(a_context,native_matrix(frame(17,9,at=(75,70,5)),core))
        sub=source.component.occurrences.addNewComponent(core.Matrix3D.create());sub.component.name='TEST_NESTED_WRAPPER'
        sub_context=sub.createForAssemblyContext(source)
        b=sub.component.occurrences.addNewComponent(core.Matrix3D.create());b.component.name='TEST_PART_B'
        b0=native.box(b.component,'B_chiral_block',(-3,2,1),(10,7,5))
        cut=native.box(b.component,'B_corner_notch',(-7,5,3),(4,3,3))
        body_b=native.subtract(b.component,b0,[cut],'B_notched_body');body_b.name='TEST_BODY_B'
        b_context=b.createForAssemblyContext(sub_context)
        native.place_occurrence(b_context,native_matrix(frame(-13,-11,at=(95,112,-35)),core))
        for label,occurrence,body in [('A',a_context,body_a),('B',b_context,body_b)]:
            for entity in (occurrence,occurrence.component,body):entity.attributes.add('MIST_fixture','part_id',label)
        require(design.computeAll(),'Source Compute All failed')
        source_rows=collect(root,source,motion);report['source']=serial(source_rows)
        report['source_top_transform_cm']=motion.as_matrix(source.transform2)
        write(output/'report.json',report)

        before={o.fullPathName for o in root.occurrences}
        inputs=core.ObjectCollection.create();inputs.add(source)
        mi=require(root.features.mirrorFeatures.createInput(inputs,root.xZConstructionPlane),'Mirror input failed')
        mirrored=require(root.features.mirrorFeatures.add(mi),'Mirror feature failed');mirrored.name='TEST_MIRROR_SOURCE_LEG_XZ'
        require(design.computeAll(),'Mirror Compute All failed')
        new_roots=[o for o in root.occurrences if o.fullPathName not in before]
        mirror_rows=[r for top in new_roots for r in collect(root,top,motion)]
        elements=[]
        pattern_elements=mirrored.patternElements
        if pattern_elements is not None:
            for i in range(pattern_elements.count):
                element=pattern_elements.item(i)
                element_occurrences=element.occurrences
                elements.append(dict(index=i,occurrence_paths=[o.fullPathName for o in element_occurrences] if element_occurrences else []))
        report['mirror']=dict(is_parametric=bool(mirrored.isParametric),health_state=str(mirrored.healthState),
            health_message=mirrored.errorOrWarningMessage,output_roots=[o.fullPathName for o in new_roots],
            pattern_elements_available=pattern_elements is not None,pattern_elements=elements,
            output_mapping_source='root_occurrences_before_after',output_leaves_found=bool(mirror_rows),
            leaves=serial(mirror_rows),comparison=compare(source_rows,mirror_rows,'mirror_y'))
        report['mirror']['proper_leaf_rotations']=bool(mirror_rows) and all(abs(r['rotation_determinant']-1)<1e-6 for r in mirror_rows)
        write(output/'report.json',report)

        rotation=frame(180)
        report['clones']=[]
        for label,original,original_rows in [('source_rotated_180',source,source_rows)]+(
                [('mirror_rotated_180',new_roots[0],mirror_rows)] if len(new_roots)==1 else []):
            stage=dict(name=label)
            try:
                clone=root.occurrences.addExistingComponent(original.component,core.Matrix3D.create())
                clone.attributes.add('MIST_fixture','leg',label)
                native.place_occurrence(clone,native_matrix(motion.mmul(rotation,motion.as_matrix(original.transform2)),core))
                require(design.computeAll(),'Clone Compute All failed')
                raw_rows=collect(root,clone,motion)
                stage.update(root_path=clone.fullPathName,component_name=clone.component.name,
                    shares_component_definition=clone.component==original.component,
                    raw_leaves=serial(raw_rows),raw_comparison=compare(original_rows,raw_rows,'rotate_180'))
                stage['leaf_override_replay_needed']=not stage['raw_comparison']['passed']
                if stage['leaf_override_replay_needed']:
                    for old in original_rows:
                        match=[r for r in raw_rows if r['component']==old['component']]
                        if len(match)!=1:raise RuntimeError('Fixture clone component correspondence is not unique')
                        target=motion.mmul(rotation,old['transform_cm'])
                        if abs(determinant(target)-1)>1e-6:raise RuntimeError('Cannot replay a reflected occurrence transform as a proper placement')
                        native.place_occurrence(match[0]['occurrence'],native_matrix(target,core))
                    require(design.computeAll(),'Clone leaf replay Compute All failed')
                final_rows=collect(root,clone,motion)
                stage.update(final_leaves=serial(final_rows),final_comparison=compare(original_rows,final_rows,'rotate_180'),
                    original_placement_after_clone=compare(original_rows,collect(root,original,motion),'identity'))
            except Exception:stage['error']=traceback.format_exc()
            report['clones'].append(stage);write(output/'report.json',report)

        report['associativity']={}
        try:
            distance_definition=fusion.DistanceExtentDefinition.cast(a.component.features.extrudeFeatures.item(0).extentOne)
            if distance_definition is None:raise RuntimeError('First source extent is not a distance extent')
            distance_parameter=distance_definition.distance;original_distance=float(distance_parameter.value)
            distance_parameter.value=original_distance+.1
            require(design.computeAll(),'Associative source-edit Compute All failed')
            edited_source=collect(root,source,motion)
            edited_mirror=[r for top in new_roots for r in collect(root,top,motion)]
            changed=any(abs(a['volume_mm3']-b['volume_mm3'])>1e-3 for a,b in zip(source_rows,edited_source))
            report['associativity']=dict(source_parameter_delta_mm=1.,source_changed=changed,
                source=serial(edited_source),mirror=serial(edited_mirror),
                mirrored_source_edit_comparison=compare(edited_source,edited_mirror,'mirror_y'))
        except Exception:report['associativity']['error']=traceback.format_exc()
        finally:
            if distance_parameter is not None:
                distance_parameter.value=original_distance;require(design.computeAll(),'Source parameter restoration failed')
        report['restored_source']=serial(collect(root,source,motion))
        archive=output/'MIST_MIRROR_FIXTURE_TEST_ONLY.f3d'
        require(design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive))),'Mirror diagnostic archive export failed')
        report.update(status='native_mirror_diagnostic_completed',archive=str(archive),
            note='Inspect each comparison. A completed diagnostic is not a pass for every mirror/clone behavior. No full-leg mapping is inferred from fixture volumes.')
    except Exception:
        report['status']='native_mirror_diagnostic_failed';report['errors'].append(traceback.format_exc())
    finally:
        if body_document:
            try:
                report['body_reactivated']=bool(body_document.activate())
                if not report['body_reactivated']:raise RuntimeError('Body document reactivation failed')
                report['main_document_unchanged']=body_before==fixture._fingerprint(body_design,motion)
                if not report['main_document_unchanged']:raise RuntimeError('Main body fingerprint changed')
            except Exception:
                report['status']='native_mirror_diagnostic_failed';report['errors'].append(traceback.format_exc())
        write(output/'report.json',report)
        write(HERE/'last_mirror_fixture.json',dict(directory=str(output),status=report['status'],report='report.json'))
        app.log('MIST mirror diagnostic: '+report['status']+'; '+str(output/'report.json'))
    return report
