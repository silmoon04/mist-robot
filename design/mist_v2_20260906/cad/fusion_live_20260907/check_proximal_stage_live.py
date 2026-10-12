"""Verify the completed first native stage persisted after the HTTP timeout."""
import json
from pathlib import Path
import adsk.core
import adsk.fusion

OUTPUT=Path(__file__).resolve().parent/'concealed_stages/FL_proximal_native_04'


def run(_context: str):
    app=adsk.core.Application.get()
    design=adsk.fusion.Design.cast(app.activeProduct)
    root=design.rootComponent if design else None
    marker=root.attributes.itemByName('MIST','build_stage') if root else None
    if not marker or marker.value!='concealed_wheel_20260907':
        raise RuntimeError('The task-owned native MIST assembly is not active')
    objects=adsk.core.ObjectCollection.create()
    rows=[]
    for occurrence in root.allOccurrences:
        for body in occurrence.component.bRepBodies:
            proxy=body.createForAssemblyContext(occurrence)
            if not proxy.isSolid:
                raise RuntimeError('A completed native stage contains a non-solid')
            objects.add(proxy)
            rows.append({'path':occurrence.fullPathName,'body':body.name})
    if len(rows)!=150:
        raise RuntimeError('Expected the33body and117proximal solids after the timed-out request')
    request=design.createInterferenceInput(objects)
    request.areCoincidentFacesIncluded=False
    result=design.analyzeInterference(request)
    if result is None:
        raise RuntimeError('Native stage interference calculation failed')
    overlaps=[{'a':getattr(item.entityOne,'name','unknown'),'b':getattr(item.entityTwo,'name','unknown'),
               'volume_mm3':item.interferenceBody.volume*1000} for item in result]
    camera=app.activeViewport.camera
    camera.cameraType=adsk.core.CameraTypes.OrthographicCameraType
    camera.viewOrientation=adsk.core.ViewOrientations.IsoTopRightViewOrientation
    camera.isSmoothTransition=False
    app.activeViewport.camera=camera
    if not app.activeViewport.fit():
        raise RuntimeError('Could not fit the completed native stage')
    if not app.activeViewport.saveAsImageFile(str(OUTPUT/'MIST_proximal_stage_isometric.png'),1500,1200):
        raise RuntimeError('Native stage isometric export failed')
    grid=[{'id':definition.id,'name':definition.name,'control_type':definition.controlDefinition.objectType}
          for definition in app.userInterface.commandDefinitions if 'grid' in definition.name.lower()]
    report={'status':'completed','native_execution':True,'persisted_after_HTTP_timeout':True,
            'solid_count':len(rows),'interferences':overlaps,'grid_commands':grid,
            'full_leg_complete':False,'full_motion_verified':False}
    (OUTPUT/'live_native_verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
    return report
