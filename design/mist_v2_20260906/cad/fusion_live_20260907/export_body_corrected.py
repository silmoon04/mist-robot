import json
from pathlib import Path
import adsk.core
import adsk.fusion

OUTPUT=Path(r'/design/mist_v2_20260906/cad/fusion_live_20260907/native_body')


def run(_context: str):
    app=adsk.core.Application.get()
    d=adsk.fusion.Design.cast(app.activeProduct)
    marker=d.rootComponent.attributes.itemByName('MIST','build_stage')
    if not marker or marker.value!='concealed_wheel_20260907':
        raise RuntimeError('Unexpected design')
    if d.computeAll() is False:
        raise RuntimeError('Compute All failed')
    if abs(d.rootComponent.occurrences.item(0).transform2.translation.z+3.5)>1e-9:
        raise RuntimeError('Assembly offset did not survive recompute')
    manager=d.exportManager
    for options in (manager.createFusionArchiveExportOptions(str(OUTPUT/'MIST_body_native.f3d')),
                    manager.createSTEPExportOptions(str(OUTPUT/'MIST_body_native.step'))):
        if not manager.execute(options):
            raise RuntimeError('Native body export failed')
    app.activeViewport.fit()
    if not app.activeViewport.saveAsImageFile(str(OUTPUT/'MIST_body_native.png'),1400,1100):
        raise RuntimeError('Native preview export failed')
    report=json.loads((OUTPUT/'verification.json').read_text())
    report.update(placement_corrected=True,assembly_offset_mm=[0,0,-35],
                  placement_evidence='placement_fix_verified.json',geometry_evidence='precise_comparison.json')
    (OUTPUT/'verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'native_body_exported':True,'offset_mm':-35,'physical_fit_validated':False}))
