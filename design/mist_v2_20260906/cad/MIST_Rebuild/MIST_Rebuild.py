"""Run from Fusion Scripts and Add-Ins; always creates a new design document."""
from pathlib import Path
import datetime
import hashlib
import importlib
import json
import math
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
CAD = ROOT / 'cad'

def _json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')

def _name(entity):
    return getattr(entity, 'fullPathName', getattr(entity, 'name', '<unnamed>'))

def run(context):
    import adsk.core
    import adsk.fusion
    app = adsk.core.Application.get()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = CAD / 'native_runs' / stamp
    out.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'simulation' / 'design_parameters_20260907.json'
    raw = source.read_bytes()
    params = json.loads(raw)
    report = {'status':'started', 'parameters_sha256':hashlib.sha256(raw).hexdigest(),
              'started_utc':stamp, 'physical_fit_validated':False, 'production_release':False}
    _json(out / 'parameters.json', params)
    _json(out / 'build_report.json', report)
    try:
        if str(CAD) not in sys.path:
            sys.path.insert(0, str(CAD))
        import native_parts
        import leg_gears
        import body_native
        import leg_native
        for module in (native_parts, leg_gears, body_native, leg_native):
            importlib.reload(module)
        document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        document.name = 'MIST candidate ' + stamp
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise RuntimeError('New document did not expose a Fusion design')
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        root = design.rootComponent
        root.attributes.add('MIST','build_role','MIST_CANDIDATE_PHYSICAL_FIT_PENDING')
        # These are generation inputs. Builders document which timeline features
        # are editable and which placements require a rerun of this script.
        for name, value in params['geometry'].items():
            if name.endswith('_m') and isinstance(value, (float, int)):
                design.userParameters.add('mist_'+name[:-2], adsk.core.ValueInput.createByReal(value*100), 'mm', 'Shared generation input; rerun builder after changes')
        body = body_native.build_body(root, params)
        legs = leg_native.build_four_legs(root, params)
        compute = design.computeAll()
        if compute is False:
            raise RuntimeError('Fusion Compute All failed')
        report['body_checks'] = body.get('checks', {})
        report['leg_checks'] = [{k:v for k,v in item.items() if k in ('checks','bom','joint_records')} for item in legs] if isinstance(legs, list) else legs.get('checks', {})
        report['body_specification'] = body.get('spec', {})
        report['leg_specifications'] = [item.get('spec', {}) for item in legs] if isinstance(legs, list) else []
        report['native_motion_joints_created'] = all(item.get('checks', {}).get('native_motion_joints_created', False) for item in legs) if isinstance(legs, list) else False
        report['source_sha256'] = {name:hashlib.sha256((CAD/name).read_bytes()).hexdigest() for name in ('native_parts.py','leg_gears.py','body_native.py','leg_native.py')}
        records = []
        inputs = adsk.core.ObjectCollection.create()
        for occurrence in root.allOccurrences:
            for native_body in occurrence.component.bRepBodies:
                proxy = native_body.createForAssemblyContext(occurrence)
                if not proxy:
                    raise RuntimeError('No root assembly context for '+native_body.name)
                bbox = proxy.boundingBox
                records.append({'component':occurrence.fullPathName,'body':native_body.name,
                                'solid':native_body.isSolid,'volume_mm3':native_body.volume*1000,
                                'bbox_mm':[[bbox.minPoint.x*10,bbox.minPoint.y*10,bbox.minPoint.z*10],
                                           [bbox.maxPoint.x*10,bbox.maxPoint.y*10,bbox.maxPoint.z*10]]})
                if not native_body.isSolid or native_body.volume <= 0:
                    raise RuntimeError('Invalid solid: '+native_body.name)
                # Include references: servo/body, shaft/bearing and battery/phone
                # intersections matter for packaging. Report contacts without
                # suppressing errors or declaring the whole assembly printable.
                inputs.add(proxy)
        report['bodies'] = records
        request = design.createInterferenceInput(inputs)
        request.areCoincidentFacesIncluded = False
        interferences = design.analyzeInterference(request)
        if interferences is None:
            raise RuntimeError('Fusion returned no interference-analysis result')
        report['interferences'] = []
        for item in interferences:
            volume = item.interferenceBody.volume * 1000
            if not math.isfinite(volume):
                raise RuntimeError('Nonfinite interference volume')
            report['interferences'].append({'a':_name(item.entityOne),'b':_name(item.entityTwo),'volume_mm3':volume})
        exporter = design.exportManager
        for options in (exporter.createFusionArchiveExportOptions(str(out/'MIST_candidate.f3d')),
                        exporter.createSTEPExportOptions(str(out/'MIST_candidate.step'))):
            if not exporter.execute(options):
                raise RuntimeError('Native assembly export failed')
        app.activeViewport.fit()
        app.activeViewport.saveAsImageFile(str(out/'MIST_native_view.png'),1600,1200)
        report.update(status='native_build_completed_candidate_only',body_count=len(records),
                      interference_count=len(report['interferences']),
                      note='One assembled pose only. Interferences require review. Full ROM, transmission teeth, thermal duty and physical fit remain separate checks.')
        _json(out/'build_report.json',report)
        app.log('MIST candidate saved to '+str(out))
    except Exception:
        report.update(status='native_build_failed',error=traceback.format_exc())
        _json(out/'build_report.json',report)
        app.log(report['error'])
        raise
