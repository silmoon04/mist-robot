"""Replay the two current fixture demonstrations without recreating geometry."""
from pathlib import Path
import importlib.util,json,math
import adsk.core,adsk.fusion
HERE=Path(__file__).resolve().parent

def run(context):
    source=HERE/'show_fusion.py';spec=importlib.util.spec_from_file_location('fixture_playback',source)
    demo=importlib.util.module_from_spec(spec);spec.loader.exec_module(demo)
    app=adsk.core.Application.get();h=demo.helper();docs={}
    for d in app.documents:
        a=d.attributes.itemByName(demo.GROUP,'kind')
        if a:docs[a.value]=d
    if 'motion' not in docs or 'exploded' not in docs:raise RuntimeError('Open both fixture documents before replay')
    manifest=json.loads((HERE/'fixture_manifest.json').read_text())
    docs['exploded'].activate();design=adsk.fusion.Design.cast(app.activeProduct)
    occ={o.component.name:o for o in design.rootComponent.occurrences}
    demo.paint(app,design,h,occ)
    app.activeViewport.visualStyle=adsk.core.VisualStyles.ShadedVisualStyle
    clamp=occ['TEST ONLY - existing clamp'];gauge=occ['TEST ONLY - remove gauge before motion']
    for p in manifest['parts']:occ[p['name']].isLightBulbOn=False
    clamp.isLightBulbOn=True;gauge.isLightBulbOn=True;gauge.transform2=demo.translate((0,0,38));demo.camera(app)
    index=0
    for start,end in [(38,0),(0,55)]:
        for i in range(18):
            t=i/17;t=t*t*(3-2*t);gauge.transform2=demo.translate((0,0,start+(end-start)*t))
            demo.frame(app,HERE/'fusion/assembly_frames',index);index+=1
    clamp.isLightBulbOn=False;gauge.isLightBulbOn=False
    for p in manifest['parts']:occ[p['name']].isLightBulbOn=True;occ[p['name']].transform2=demo.translate(p['explode_mm'])
    demo.camera(app)
    for i in range(26):
        t=i/25;t=t*t*(3-2*t)
        for p in manifest['parts']:occ[p['name']].transform2=demo.translate([v*(1-t) for v in p['explode_mm']])
        demo.frame(app,HERE/'fusion/assembly_frames',index);index+=1
    design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(HERE/'fusion/fixture_exploded_assembly.f3d')))
    docs['motion'].activate();design=adsk.fusion.Design.cast(app.activeProduct)
    occ={o.component.name:o for o in design.rootComponent.occurrences};demo.paint(app,design,h,occ)
    for component in [design.rootComponent]+[o.component for o in design.rootComponent.allOccurrences]:
        component.isConstructionFolderLightBulbOn=False;component.isSketchFolderLightBulbOn=False
        component.isOriginFolderLightBulbOn=False;component.isJointsFolderLightBulbOn=False
    app.activeViewport.visualStyle=adsk.core.VisualStyles.ShadedVisualStyle
    joint=design.rootComponent.asBuiltJoints.item(0);joint.isLightBulbOn=False;demo.camera(app)
    base_before=h._matrix_mm(occ['base'].transform2)
    for i in range(61):
        joint.jointMotion.rotationValue=math.radians(10)*math.sin(i/60*4*math.pi)
        adsk.doEvents();demo.frame(app,HERE/'fusion/motion_frames',i)
        assert h._matrix_mm(occ['base'].transform2)==base_before
    joint.jointMotion.rotationValue=0;adsk.doEvents()
    design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(HERE/'fusion/fixture_working_revolute_joint.f3d')))
    app.activeViewport.saveAsImageFile(str(HERE/'fusion/fixture_assembled.png'),1500,1100)
    return {'status':'completed','native_revolute_count':1}
