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
    raw=path.read_bytes()
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    # Compile the captured bytes to avoid a stale module or same-second pyc
    # cache surviving a second run inside Fusion's persistent Python process.
    exec(compile(raw,str(path),'exec'),module.__dict__)
    module.__mist_source_bytes__=raw
    module.__mist_source_sha256__=hashlib.sha256(raw).hexdigest()
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
        # Reload dependencies in order; ordinary imports in the entry modules
        # then resolve to these exact local source versions.
        dependencies=[_load('native_parts',CAD/'native_parts.py'),
                      _load('leg_gears',CAD/'leg_gears.py'),
                      _load('leg_native',CAD/'leg_native.py'),
                      _load('retention_recipe',HERE/'retention_recipe.py')]
        body_module=_load('mist_proximal_body_20260907',CAD/'body_native.py')
        leg_module=_load('proximal_leg',HERE/'proximal_leg.py')
        replay=_load('mist_proximal_native_replay_20260907',HERE/'native_replay.py')
        motion=_load('mist_native_motion_20260907',CAD/'fusion_motion_20260907/motion.py')
        grouping=_load('mist_reviewed_motion_groups_20260907',CAD/'fusion_motion_20260907/reviewed_groups.py')
        params=json.loads((ROOT/'simulation/design_parameters_20260907.json').read_text())
        params['status']='native_proximal_candidate_unvalidated'
        params['transmission'].update(topology='proximal_femur_relative_knee',knee_motor_mount='femur',
            motor_coordinate_equation='s=[2*yaw,2*hip,2*knee]; normalized actuator directions require commissioning')
        body_spec=body_module.body_spec(params)
        specs=[leg_module.leg_spec(params,name) for name in params['geometry']['leg_names']]
        params['mass']['knee_servo_com_m']=[value/1000 for value in specs[0]['knee_servo_com_femur_mm']]
        explicit_groups=grouping.proximal_group_overrides(specs)
        plan=motion.build_motion_plan(params,body_spec,specs,group_overrides=explicit_groups)
        _write(output/'parameters.json',params)
        _write(output/'motion_plan_before_build.json',plan)
        _write(output/'leg_specifications.json',specs)
        _write(output/'motion_group_overrides.json',explicit_groups)
        _write(output/'motion_group_audit.json',grouping.assignment_audit(specs,explicit_groups))
        sources=dependencies+[body_module,leg_module,replay,motion,grouping]
        report['source_sha256']={str(Path(module.__file__).relative_to(CAD)):module.__mist_source_sha256__ for module in sources}
        report['runner_source_sha256_at_start']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        for module in sources:
            saved=output/'source_snapshot'/Path(module.__file__).relative_to(CAD)
            saved.parent.mkdir(parents=True,exist_ok=True)
            saved.write_bytes(module.__mist_source_bytes__)
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
        report['motion']=motion.rig_build_results(design,params,body,legs,output_directory=output/'motion',
                                                  group_overrides=explicit_groups)
        report['native_motion_joints_created']=report['motion']['native_joint_creation_complete']
        report['native_direction_probes_completed']=all(
            row.get('status')=='created_and_direction_checked' for row in report['motion']['joint_records'])
        report['full_motion_verified']=False
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
        if not app.activeViewport.fit():
            raise RuntimeError('Native viewport fit failed')
        if not app.activeViewport.saveAsImageFile(str(output/'MIST_proximal_native_view.png'),1600,1200):
            raise RuntimeError('Native viewport image export failed')
        report.update(status='native_candidate_built',body_count=len(bodies),
            note='Joint probes and one-pose interference only. Gear/belt mates, full travel, material assignment, structural strength and physical fit remain separate checks.')
        _write(output/'build_report.json',report)
        app.log('MIST proximal candidate saved to '+str(output))
    except Exception:
        report.update(status='native_build_failed',error=traceback.format_exc())
        _write(output/'build_report.json',report)
        app.log(report['error'])
        raise
