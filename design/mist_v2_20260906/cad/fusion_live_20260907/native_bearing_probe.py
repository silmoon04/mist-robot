"""Build one actual fit carrier in a new native Fusion document."""
import importlib.util
import json
from pathlib import Path
import sys
import adsk.core
import adsk.fusion

CAD=Path(r'/design/mist_v2_20260906/cad')
OUTPUT=CAD/'fusion_live_20260907/bearing_probe'


def run(_context: str):
    OUTPUT.mkdir(exist_ok=True)
    app=adsk.core.Application.get()
    document=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.name='MIST native bearing carrier verification'
    design=adsk.fusion.Design.cast(app.activeProduct)
    design.designType=adsk.fusion.DesignTypes.ParametricDesignType
    spec=importlib.util.spec_from_file_location('mist_native_probe_parts',CAD/'native_parts.py')
    native=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=native
    spec.loader.exec_module(native)
    occurrence=design.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    component=occurrence.component
    component.name='MIST_OD34_bearing_carrier_22p4'
    body=native.annulus(component,'Carrier blank',(0,0,0),(0,0,8.4),17,10)
    bore=native.cylinder(component,'Bearing seat',(0,0,1.2),(0,0,8.5),11.2)
    body=native.subtract(component,body,[bore],'Seat pocket')
    for index,x in enumerate((-14,14)):
        hole=native.cylinder(component,'Keeper clearance '+str(index),(x,0,-.1),(x,0,8.5),1.7)
        body=native.subtract(component,body,[hole],'Keeper hole '+str(index))
    if design.computeAll() is False:
        raise RuntimeError('Native carrier Compute All failed')
    if not body.isSolid or component.bRepBodies.count!=1:
        raise RuntimeError('Native carrier is not one solid')
    archive=design.exportManager.createFusionArchiveExportOptions(str(OUTPUT/'MIST_bearing_carrier_native.f3d'))
    if not design.exportManager.execute(archive):
        raise RuntimeError('Native carrier F3D export failed')
    step=design.exportManager.createSTEPExportOptions(str(OUTPUT/'MIST_bearing_carrier_native.step'))
    if not design.exportManager.execute(step):
        raise RuntimeError('Native carrier STEP export failed')
    app.activeViewport.fit()
    if not app.activeViewport.saveAsImageFile(str(OUTPUT/'MIST_bearing_carrier_native.png'),1200,900):
        raise RuntimeError('Native carrier preview failed')
    report={'native_execution':True,'document':document.name,'solid_count':component.bRepBodies.count,
            'volume_mm3':body.volume*1000,'sketches':component.sketches.count,
            'features':component.features.count,'fusion_version':app.version,'physical_fit_validated':False}
    (OUTPUT/'verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
