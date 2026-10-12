"""Append a frozen leg recipe to the task-owned native MIST assembly."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback
import adsk.core
import adsk.fusion

HERE=Path(__file__).resolve().parent
REQUEST=HERE/'concealed_build_request.json'


def write(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')


def load(name,path,output):
    raw=path.read_bytes()
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    exec(compile(raw,str(path),'exec'),module.__dict__)
    destination=output/'source_snapshot'/path.name
    destination.parent.mkdir(exist_ok=True)
    destination.write_bytes(raw)
    return module,hashlib.sha256(raw).hexdigest()


def run(_context: str):
    request=json.loads(REQUEST.read_text())
    output=Path(request['output'])
    output.mkdir(parents=True,exist_ok=False)
    source=Path(request['recipes'])
    source_bytes=source.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest()!=request['recipes_sha256']:
        raise RuntimeError('Frozen recipes changed before the native build')
    specs=json.loads(source_bytes)
    (output/'recipes_frozen.json').write_bytes(source_bytes)
    write(output/'request.json',request)
    app=adsk.core.Application.get()
    selected=[]
    for document in app.documents:
        design=adsk.fusion.Design.cast(document.products.itemByProductType('DesignProductType'))
        if design:
            marker=design.rootComponent.attributes.itemByName('MIST','build_stage')
            if marker and marker.value=='concealed_wheel_20260907':
                selected.append((document,design))
    if len(selected)!=1:
        raise RuntimeError('Expected exactly one task-owned concealed MIST assembly')
    document,design=selected[0]
    if not document.activate():
        raise RuntimeError('Could not activate the task-owned MIST assembly')
    progress={'status':'building','leg':request['leg'],'started_unix':time.time(),
              'native_execution':True,'physical_fit_validated':False,'production_release':False,
              'physical_materials_assigned':False,'features_created':0,'document':document.name}
    write(output/'progress.json',progress)
    native,native_hash=load('native_parts',HERE.parent/'native_parts.py',output)
    step,step_hash=load('purchased_step',HERE/'purchased_step.py',output)
    replay,replay_hash=load('mist_concealed_native_replay',HERE/'concealed_native_replay.py',output)
    progress['source_sha256']={'native_parts.py':native_hash,'purchased_step.py':step_hash,
                               'concealed_native_replay.py':replay_hash}
    original=native._feature_body
    def record_feature(feature,name):
        body=original(feature,name)
        progress['features_created']+=1
        progress['last_feature']=name
        if progress['features_created']%10==0:
            write(output/'progress.json',progress)
        return body
    def record_part(row):
        progress.update(row)
        write(output/'progress.json',progress)
    native._feature_body=record_feature
    try:
        result=replay.build_leg(design.rootComponent,specs[request['leg']],request['palette'],record_part,
                                extend=request.get('extend',False),max_build_seconds=request.get('max_build_seconds',300))
        write(output/'occurrence_bindings.json',result['records'])
        geometry=[]
        for name,body in result['bodies'].items():
            occurrence=result['part_occurrences'][name]
            proxy=body.createForAssemblyContext(occurrence)
            bb=proxy.preciseBoundingBox
            props=proxy.getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy)
            geometry.append({'name':name,'root_path':occurrence.fullPathName,'solid':proxy.isSolid,
                'volume_mm3':props.volume*1000,'local_features':body.parentComponent.features.count,
                'bounds_world_mm':[[bb.minPoint.x*10,bb.minPoint.y*10,bb.minPoint.z*10],
                                   [bb.maxPoint.x*10,bb.maxPoint.y*10,bb.maxPoint.z*10]]})
        write(output/'geometry.json',geometry)
        all_solids=sum(occ.component.bRepBodies.count for occ in design.rootComponent.allOccurrences)
        exporter=design.exportManager
        name='MIST_concealed_native_after_'+request['leg']
        for options in (exporter.createFusionArchiveExportOptions(str(output/(name+'.f3d'))),
                        exporter.createSTEPExportOptions(str(output/(name+'.step')))):
            if not exporter.execute(options):
                raise RuntimeError('Native assembly export failed')
        if not app.activeViewport.fit():
            raise RuntimeError('Native assembly viewport fit failed')
        if not app.activeViewport.saveAsImageFile(str(output/(name+'.png')),1500,1200):
            raise RuntimeError('Native assembly preview failed')
        progress.update(status='completed' if result['complete'] else 'partial_stage_completed',elapsed_s=time.time()-progress['started_unix'],
            leg_part_count=len(geometry),assembly_solid_count=all_solids,
            requested_recipe_complete=result['complete'],
            reused_parts=sum(row['reused'] for row in result['records']),
            full_motion_verified=False,geometry_correspondence_pending=True)
        print(json.dumps({key:progress[key] for key in ('status','leg','elapsed_s','leg_part_count','assembly_solid_count','features_created','reused_parts')}))
        return progress
    except Exception:
        progress.update(status='failed',error=traceback.format_exc(),elapsed_s=time.time()-progress['started_unix'])
        raise
    finally:
        native._feature_body=original
        write(output/'progress.json',progress)
        write(output/'build_report.json',progress)
