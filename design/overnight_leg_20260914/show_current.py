from pathlib import Path
import json,hashlib
import adsk.core,adsk.fusion
ROOT=Path(__file__).resolve().parent

def run(context):
    app=adsk.core.Application.get();wanted='single_leg_r7_wide_joints_20260914'
    digest=hashlib.sha256((ROOT.parent/wanted/'output/manifest.json').read_bytes()).hexdigest()
    for i in range(app.documents.count):
        doc=app.documents.item(i)
        marker=doc.attributes.itemByName(wanted,'input_sha256')
        if marker and marker.value==digest:
            doc.activate();app.activeViewport.fit();app.activeViewport.refresh();adsk.doEvents()
            return {'status':'completed','document':doc.name}
    raise RuntimeError('Current R7 document not found')

