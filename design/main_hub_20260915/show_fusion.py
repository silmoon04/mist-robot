"""Show the new printable hub in a separate bright Fusion design."""
from pathlib import Path
import json,math
import adsk.core,adsk.fusion
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'

def run(context):
    app=adsk.core.Application.get();doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);doc.name='PRINT TONIGHT - four-leg main hub and eight spacers'
    design=adsk.fusion.Design.cast(app.activeProduct);design.designType=adsk.fusion.DesignTypes.DirectDesignType;root=design.rootComponent
    source=app.materialLibraries.itemByName('Fusion Appearance Library').appearances.itemByName('Plastic - Matte (White)')
    colors={}
    for name,rgb in [('hub',(125,205,231)),('spacer',(247,192,118))]:
        a=design.appearances.addByCopy(source,'MainHub_'+name)
        for prop in a.appearanceProperties:
            c=adsk.core.ColorProperty.cast(prop)
            if c:c.value=adsk.core.Color.create(*rgb,255)
        colors[name]=a
    def imp(name,path,xyz,color):
        t=adsk.core.Matrix3D.create();t.translation=adsk.core.Vector3D.create(*(v/10 for v in xyz));occ=root.occurrences.addNewComponent(t);occ.component.name=name
        options=app.importManager.createSTEPImportOptions(str(path));options.isViewFit=False;assert app.importManager.importToTarget2(options,occ.component)
        def paint(o):
            o.appearance=colors[color]
            for b in o.component.bRepBodies:b.appearance=colors[color]
            for child in o.childOccurrences:paint(child)
        paint(occ);return occ
    imp('Main hub - six millimetre deck with upper ribs',OUT/'Main_Hub_4Leg.step',(0,0,0),'hub')
    for x in (-101,101):
        for y in (-40.5,-13.5,13.5,40.5):imp('Spacer 8H x13OD - M3',OUT/'Spacer_8H_13OD_M3.step',(x,y,0),'spacer')
    view=app.activeViewport;view.visualStyle=adsk.core.VisualStyles.ShadedWithVisibleEdgesOnlyVisualStyle;cam=view.camera
    cam.cameraType=adsk.core.CameraTypes.OrthographicCameraType;cam.eye=adsk.core.Point3D.create(27,-35,40);cam.target=adsk.core.Point3D.create(0,0,0);cam.upVector=adsk.core.Vector3D.create(0,0,1);cam.isFitView=True;view.camera=cam;view.fit();view.refresh();adsk.doEvents()
    design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(OUT/'Main_Hub_And_Spacers.f3d')))
    view.saveAsImageFile(str(OUT/'Fusion_Hub.png'),1400,1000)
    return {'status':'completed','document_name':doc.name,'component_count':root.occurrences.count}
