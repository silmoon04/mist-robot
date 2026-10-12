"""Verify the purchased KHK STEP in a separate native Fusion document."""
import hashlib
import json
from pathlib import Path
import adsk.core
import adsk.fusion

ROOT = Path(r'/design/mist_v2_20260906')
OUTPUT = ROOT / 'cad/fusion_live_20260907/vendor_import_probe'
SOURCE = ROOT / 'references/KHK_SM1_20/SM1-20_On.stp'
EXPECTED = 'c4aebaa418f6955130f9bf4f4a798dc478b181fea47327865db2d7aedb386a98'


def run(_context: str):
    OUTPUT.mkdir(exist_ok=True)
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != EXPECTED:
        raise RuntimeError('The supplier STEP does not match its receipt')
    app = adsk.core.Application.get()
    previous = app.activeDocument
    report = {'status': 'started', 'source_sha256': EXPECTED, 'native_execution': True}
    try:
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        doc.name = 'MIST KHK purchased gear import test'
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        root = design.rootComponent
        root.attributes.add('MIST', 'build_role', 'vendor_import_probe_20260907')
        occurrence = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occurrence.component.name = 'KHK_SM1-20_manufacturer_geometry'
        options = app.importManager.createSTEPImportOptions(str(SOURCE))
        imported = app.importManager.importToTarget2(options, occurrence.component)
        if imported is None:
            raise RuntimeError('Fusion STEP import returned no objects')
        report['returned_types'] = [item.objectType for item in imported]
        if design.computeAll() is False:
            raise RuntimeError('Imported STEP recompute failed')
        report['root_bodies'] = root.bRepBodies.count
        report['occurrences'] = []
        for item in root.allOccurrences:
            row = {'path': item.fullPathName, 'bodies': [], 'children': item.component.occurrences.count}
            for body in item.component.bRepBodies:
                proxy = body.createForAssemblyContext(item)
                bb = proxy.preciseBoundingBox
                props = proxy.getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy)
                row['bodies'].append({'name': body.name, 'solid': body.isSolid,
                    'volume_mm3': props.volume * 1000, 'face_count': body.faces.count,
                    'bounds_mm': [[bb.minPoint.x*10, bb.minPoint.y*10, bb.minPoint.z*10],
                                  [bb.maxPoint.x*10, bb.maxPoint.y*10, bb.maxPoint.z*10]]})
            report['occurrences'].append(row)
        solids = [body for row in report['occurrences'] for body in row['bodies']]
        if len(solids) != 1 or not solids[0]['solid']:
            raise RuntimeError('Expected one imported manufacturer solid')
        if abs(solids[0]['volume_mm3'] - 2332.532) > 0.5:
            raise RuntimeError('STEP volume disagrees with independent import')
        if not design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(OUTPUT/'KHK_SM1-20_import.f3d'))):
            raise RuntimeError('Purchased gear test export failed')
        app.activeViewport.fit()
        if not app.activeViewport.saveAsImageFile(str(OUTPUT/'KHK_SM1-20_import.png'),1000,850):
            raise RuntimeError('Purchased gear preview failed')
        report['status'] = 'completed'
        return report
    except Exception as exc:
        report.update(status='failed',error=str(exc))
        raise
    finally:
        if previous:
            report['previous_document_reactivated'] = bool(previous.activate())
        (OUTPUT/'verification.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report))
