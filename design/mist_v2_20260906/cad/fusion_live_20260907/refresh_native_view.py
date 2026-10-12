"""Set a readable camera and render after Fusion has refreshed the viewport."""
import json
from pathlib import Path
import adsk.core
import adsk.fusion


def run(_context: str):
    app=adsk.core.Application.get()
    design=adsk.fusion.Design.cast(app.activeProduct)
    marker=design.rootComponent.attributes.itemByName('MIST','build_stage') if design else None
    if not marker or marker.value!='concealed_wheel_20260907':
        raise RuntimeError('The task-owned MIST native assembly is not active')
    camera=app.activeViewport.camera
    camera.isSmoothTransition=False
    camera.cameraType=adsk.core.CameraTypes.OrthographicCameraType
    camera.eye=adsk.core.Point3D.create(65,65,48)
    camera.target=adsk.core.Point3D.create(5,5,5)
    camera.upVector=adsk.core.Vector3D.create(0,0,1)
    camera.isFitView=True
    app.activeViewport.camera=camera
    adsk.doEvents()
    app.activeViewport.refresh()
    adsk.doEvents()
    output=Path(__file__).resolve().parent/'concealed_stages/FL_proximal_native_04'
    if not app.activeViewport.saveAsImageFile(str(output/'MIST_proximal_stage_refreshed.png'),1500,1200):
        raise RuntimeError('Native viewport render failed')
    actual=app.activeViewport.camera
    grid=adsk.core.ListControlDefinition.cast(app.userInterface.commandDefinitions.itemById('ViewLayoutGridOnCommand').controlDefinition)
    report={'status':'completed','camera_eye_cm':actual.eye.asArray(),'camera_target_cm':actual.target.asArray(),
            'grid_items':[{'name':item.name,'selected':item.isSelected} for item in grid.listItems]}
    (output/'camera_verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
    return report
