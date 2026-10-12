"""Native body stage, kept as the base for the concealed wheel-drive assembly."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import adsk.core
import adsk.fusion

CAD=Path(r'/design/mist_v2_20260906/cad')
OUTPUT=CAD/'fusion_live_20260907/native_body'


def load(name,path):
    source=path.read_bytes()
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    exec(compile(source,str(path),'exec'),module.__dict__)
    return module,hashlib.sha256(source).hexdigest()


def run(_context: str):
    OUTPUT.mkdir(exist_ok=True)
    app=adsk.core.Application.get()
    document=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.name='MIST concealed wheel drive - native assembly'
    design=adsk.fusion.Design.cast(app.activeProduct)
    design.designType=adsk.fusion.DesignTypes.ParametricDesignType
    design.rootComponent.attributes.add('MIST','build_stage','concealed_wheel_20260907')
    params=json.loads((CAD.parent/'simulation/design_parameters_20260907.json').read_text())
    native,native_hash=load('native_parts',CAD/'native_parts.py')
    body_module,body_hash=load('mist_live_body',CAD/'body_native.py')
    progress={'status':'building','document':document.name,'features':0,'started_unix':time.time()}
    (OUTPUT/'progress.json').write_text(json.dumps(progress))
    original=native._feature_body
    def record_feature(feature,name):
        body=original(feature,name)
        progress.update(features=progress['features']+1,last_feature=name)
        if progress['features']%10==0:
            (OUTPUT/'progress.json').write_text(json.dumps(progress))
        return body
    native._feature_body=record_feature
    try:
        result=body_module.build_body(design.rootComponent,params)
    finally:
        native._feature_body=original
    library=app.materialLibraries.itemByName('Fusion Appearance Library')
    base=library.appearances.itemByName('Plastic - Matte (White)')
    appearances={}
    for part in result['spec']['parts']:
        rgba=body_module.COLORS[part['color']]
        key=tuple(rgba[:3])
        if key not in appearances:
            appearance=design.appearances.addByCopy(base,'MIST RGB '+'-'.join(map(str,key)))
            for property_id in ('opaque_albedo','surface_albedo'):
                prop=adsk.core.ColorProperty.cast(appearance.appearanceProperties.itemById(property_id))
                if prop:
                    prop.value=adsk.core.Color.create(*key,255)
            appearances[key]=appearance
        result['bodies'][part['name']].appearance=appearances[key]
    if design.computeAll() is False:
        raise RuntimeError('Native body Compute All failed')
    records=[]
    for name,body in result['bodies'].items():
        if not body.isSolid:
            raise RuntimeError('Non-solid native body component: '+name)
        records.append({'name':name,'volume_mm3':body.volume*1000,'sketches':body.parentComponent.sketches.count})
    exporter=design.exportManager
    for options in (exporter.createFusionArchiveExportOptions(str(OUTPUT/'MIST_body_native.f3d')),
                    exporter.createSTEPExportOptions(str(OUTPUT/'MIST_body_native.step'))):
        if not exporter.execute(options):
            raise RuntimeError('Native body export failed')
    app.activeViewport.fit()
    if not app.activeViewport.saveAsImageFile(str(OUTPUT/'MIST_body_native.png'),1400,1100):
        raise RuntimeError('Native body preview failed')
    progress.update(status='completed',elapsed_s=time.time()-progress['started_unix'],parts=records,
                    source_sha256={'native_parts.py':native_hash,'body_native.py':body_hash},
                    native_execution=True,appearance_assigned=True,physical_materials_assigned=False,
                    physical_fit_validated=False)
    (OUTPUT/'progress.json').write_text(json.dumps(progress,indent=2))
    (OUTPUT/'verification.json').write_text(json.dumps(progress,indent=2))
    (OUTPUT/'body_spec.json').write_text(json.dumps(result['spec'],indent=2))
    print(json.dumps({'status':progress['status'],'document':document.name,'parts':len(records),
                      'elapsed_s':progress['elapsed_s'],'features':progress['features']}))
