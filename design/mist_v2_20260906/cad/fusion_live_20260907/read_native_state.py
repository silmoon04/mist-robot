"""Read only: identify task-owned native stages without triggering recompute."""
import json
from pathlib import Path
import adsk.core
import adsk.fusion


def run(_context: str):
    app=adsk.core.Application.get()
    documents=[]
    for document in app.documents:
        design=adsk.fusion.Design.cast(document.products.itemByProductType('DesignProductType'))
        if design:
            root=design.rootComponent
            marker=root.attributes.itemByName('MIST','build_stage')
            if marker and marker.value=='concealed_wheel_20260907':
                documents.append({'name':document.name,'solids':sum(occ.component.bRepBodies.count for occ in root.allOccurrences),
                    'legs':[{'name':occ.component.name,'stage':occ.component.attributes.itemByName('MIST','build_status').value}
                            for occ in root.occurrences if occ.component.attributes.itemByName('MIST','concealed_leg')]})
    result={'status':'completed','documents':documents,'active_document':app.activeDocument.name}
    Path(__file__).with_name('live_state.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    return result
