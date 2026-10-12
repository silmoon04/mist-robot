import json
from pathlib import Path
import adsk.core
import adsk.fusion

OUTPUT=Path(r'/design/mist_v2_20260906/cad/fusion_live_20260907/native_body')


def run(_context: str):
    app=adsk.core.Application.get()
    design=adsk.fusion.Design.cast(app.activeProduct)
    marker=design.rootComponent.attributes.itemByName('MIST','build_stage') if design else None
    if not marker or marker.value!='concealed_wheel_20260907':
        raise RuntimeError('The MIST native assembly is not active; refusing to inspect a different design')
    rows=[]
    objects=adsk.core.ObjectCollection.create()
    for occurrence in design.rootComponent.allOccurrences:
        for body in occurrence.component.bRepBodies:
            proxy=body.createForAssemblyContext(occurrence)
            bounds=proxy.preciseBoundingBox
            properties=proxy.getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy)
            rows.append({'name':body.name,'volume_mm3':properties.volume*1000,'solid':proxy.isSolid,
                'bounds_world_mm':[[bounds.minPoint.x*10,bounds.minPoint.y*10,bounds.minPoint.z*10],
                                   [bounds.maxPoint.x*10,bounds.maxPoint.y*10,bounds.maxPoint.z*10]]})
            objects.add(proxy)
    request=design.createInterferenceInput(objects)
    request.areCoincidentFacesIncluded=False
    result=design.analyzeInterference(request)
    if result is None:
        raise RuntimeError('No native interference result')
    overlaps=[]
    for item in result:
        overlaps.append({'a':getattr(item.entityOne,'name','unnamed'),'b':getattr(item.entityTwo,'name','unnamed'),
                         'volume_mm3':item.interferenceBody.volume*1000})
    report={'native_execution':True,'calculation_accuracy':'VeryHighCalculationAccuracy','parts':rows,'interferences':overlaps}
    (OUTPUT/'native_geometry_check.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'parts':len(rows),'interferences':len(overlaps),'all_solid':all(x['solid'] for x in rows)}))
