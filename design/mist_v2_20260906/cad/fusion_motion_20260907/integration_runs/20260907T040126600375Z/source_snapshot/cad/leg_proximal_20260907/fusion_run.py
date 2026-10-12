"""Fusion entry point for a new proximal candidate document and native joints."""
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


def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def _write(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')


def run(context):
    import adsk.core
    import adsk.fusion
    app=adsk.core.Application.get()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output=CAD/'native_proximal_runs'/stamp
    output.mkdir(parents=True,exist_ok=False)
    report=dict(status='started',physical_fit_validated=False,production_release=False,
                physical_materials_assigned=False,native_motion_verified=False)
    _write(output/'build_report.json',report)
    for directory in (CAD,HERE):
        if str(directory) not in sys.path:
            sys.path.insert(0,str(directory))
    try:
        # Unique entry-point aliases avoid importing a different project's helper.
        body_module=_load('mist_proximal_body_20260907',CAD/'body_native.py')
        leg_module=_load('proximal_leg',HERE/'proximal_leg.py')
        replay=_load('mist_proximal_native_replay_20260907',HERE/'native_replay.py')
        motion=_load('mist_native_motion_20260907',CAD/'fusion_motion_20260907/motion.py')
        params=json.loads((ROOT/'simulation/design_parameters_20260907.json').read_text())
        params['status']='native_proximal_candidate_unvalidated'
        params['transmission'].update(topology='proximal_femur_relative_knee',knee_motor_mount='femur',
            motor_coordinate_equation='s=[2*yaw,2*hip,2*knee]; normalized actuator directions require commissioning')
        body_spec=body_module.body_spec(params)
        specs=[leg_module.leg_spec(params,name) for name in params['geometry']['leg_names']]
        params['mass']['knee_servo_com_m']=[value/1000 for value in specs[0]['knee_servo_com_femur_mm']]
        plan=motion.build_motion_plan(params,body_spec,specs)
        _write(output/'parameters.json',params)
        _write(output/'motion_plan_before_build.json',plan)
        _write(output/'leg_specifications.json',specs)
        sources=[CAD/'native_parts.py',CAD/'leg_gears.py',CAD/'leg_native.py',CAD/'body_native.py',
                 HERE/'proximal_leg.py',HERE/'retention_recipe.py',HERE/'native_replay.py',HERE/'fusion_run.py',
                 CAD/'fusion_motion_20260907/motion.py']
        report['source_sha256']={str(path.relative_to(CAD)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
        document=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        document.name='MIST proximal candidate '+stamp
        design=adsk.fusion.Design.cast(app.activeProduct)
        if design is None:
            raise RuntimeError('The new document has no Fusion design')
        design.designType=adsk.fusion.DesignTypes.ParametricDesignType
        root=design.rootComponent
        root.name='MIST_PROXIMAL_CANDIDATE_FIT_AND_LOAD_PENDING'
        for name,value in params['geometry'].items():
            if name.endswith('_m') and isinstance(value,(int,float)):
                design.userParameters.add('mist_'+name[:-2],adsk.core.ValueInput.createByReal(value*100),'mm',
                                          'Generation input; rerun the builder after changing the source dimensions')
        body=body_module.build_body(root,params)
        legs=replay.build_four_legs(root,params,specifications=specs)
        if design.computeAll() is False:
            raise RuntimeError('Fusion Compute All failed after native feature replay')
        report['motion']=motion.rig_build_results(design,params,body,legs,output_directory=output/'motion')
        report['native_motion_verified']=True
        if design.computeAll() is False:
            raise RuntimeError('Fusion Compute All failed after joint creation')
        entities=adsk.core.ObjectCollection.create()
        bodies=[]
        for occurrence in root.allOccurrences:
            for native_body in occurrence.component.bRepBodies:
                proxy=native_body.createForAssemblyContext(occurrence)
                if not proxy or not proxy.isSolid or proxy.volume<=0:
                    raise RuntimeError('Invalid native assembly solid: '+native_body.name)
                entities.add(proxy)
                bodies.append(dict(component=occurrence.fullPathName,body=native_body.name,volume_mm3=proxy.volume*1000))
        request=design.createInterferenceInput(entities)
        request.areCoincidentFacesIncluded=False
        intersections=design.analyzeInterference(request)
        if intersections is None:
            raise RuntimeError('Fusion returned no interference result')
        report['interferences']=[]
        for item in intersections:
            volume=item.interferenceBody.volume*1000
            if not math.isfinite(volume):
                raise RuntimeError('A native interference volume is nonfinite')
            report['interferences'].append(dict(a=getattr(item.entityOne,'name','unnamed'),
                                               b=getattr(item.entityTwo,'name','unnamed'),volume_mm3=volume))
        report['bodies']=bodies
        exporter=design.exportManager
        for options in (exporter.createFusionArchiveExportOptions(str(output/'MIST_proximal_candidate.f3d')),
                        exporter.createSTEPExportOptions(str(output/'MIST_proximal_candidate.step'))):
            if not exporter.execute(options):
                raise RuntimeError('Native assembly export failed')
        app.activeViewport.fit()
        app.activeViewport.saveAsImageFile(str(output/'MIST_proximal_native_view.png'),1600,1200)
        report.update(status='native_candidate_built',body_count=len(bodies),
            note='Joint probes and one-pose interference only. Gear/belt mates, full travel, material assignment, structural strength and physical fit remain separate checks.')
        _write(output/'build_report.json',report)
        app.log('MIST proximal candidate saved to '+str(output))
    except Exception:
        report.update(status='native_build_failed',error=traceback.format_exc())
        _write(output/'build_report.json',report)
        app.log(report['error'])
        raise
