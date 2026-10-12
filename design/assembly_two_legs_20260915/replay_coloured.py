"""Quick native Fusion assembly sequence using exact centred DFM solids."""
from pathlib import Path
import json,math,hashlib,importlib.util,sys
import adsk.core,adsk.fusion
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'fusion'

STAGES=[
 ('1. Prepare the yaw servo base', 'Not on overnight plate: saddle and yaw cap. Three M3x30 with nuts and one flat washer each.',
  {'yaw_case_saddle':[0,0,0],'servo_yaw':[0,0,40],'case_cap_yaw':[0,35,0]}),
 ('2. Fit the yaw discs and upper coxa', 'Matching centre retainers first. Main horn: four M3x6, one 0.5 mm washer per screw.',
  {'horn_yaw_main':[0,0,25],'horn_yaw_auxiliary':[0,0,-25],'coxa_upper_and_hip_saddle':[0,0,50]}),
 ('3. Clamp the hip servo', 'Load two post nuts through side slots now. Hip case: three M3x30 with nuts and one washer each.',
  {'servo_hip':[0,0,35],'case_cap_hip':[0,0,-35]}),
 ('4. Fit the yaw spacers and lower arm', 'Four 11.6 mm spacers. Disc: four M3x20 with two washers. Post: two M3x20 with one washer.',
  {**{f'yaw_auxiliary_spacer_{i}':[0,0,-25] for i in range(1,5)},'coxa_lower_auxiliary_arm':[0,0,-45]}),
 ('5. Attach the main femur bracket', 'Fit hip discs and retainers. Main horn: four M3x6 with one washer each. Load the bridge nut.',
  {'horn_hip_main':[0,25,0],'horn_hip_auxiliary':[0,-25,0],'femur_main_and_knee_saddle':[0,45,0]}),
 ('6. Clamp the knee servo', 'Case points back toward hip. Three M3x30 with nuts and one flat washer per screw.',
  {'servo_knee':[0,0,35],'case_cap_knee':[0,0,-35]}),
 ('7. Close the femur fork', 'Annular stand-off faces inward. Four M3x12 with TWO washers; one M3x30 into bridge nut.',
  {'femur_auxiliary_cheek':[0,-45,0]}),
 ('8. Attach the straight tibia', 'Fit knee discs and retainers. Main horn: four M3x6 with one washer each. Load both bridge nuts.',
  {'horn_knee_main':[0,25,0],'horn_knee_auxiliary':[0,-25,0],'tibia_curved_main_and_foot':[0,45,0]}),
 ('9. Close the tibia fork', 'Four M3x12 with TWO washers; two M3x30 with one washer each into the two bridge nuts.',
  {'tibia_auxiliary_cheek':[0,-45,0]}),
]

def matrix(values,offset=(0,0,0)):
    m=adsk.core.Matrix3D.create()
    for i in range(4):
        for j in range(4):
            v=values[i][j]
            if i<3 and j==3:v=(v+sum(values[i][k]*offset[k] for k in range(3)))/10
            m.setCell(i,j,v)
    return m

def run(context):
    OUT.mkdir(exist_ok=True);frames=OUT/'frames';frames.mkdir(exist_ok=True)
    data=json.loads((ROOT/'assets/assembly_manifest.json').read_text());by={p['name']:p for p in data['parts']}
    assert set(by)=={n for _,_,group in STAGES for n in group}
    spec=importlib.util.spec_from_file_location('assembly_helper',ROOT.parent/'hexapod_phone_quad_r5_20260912/cad/fusion_import.py');h=importlib.util.module_from_spec(spec);sys.modules[spec.name]=h;spec.loader.exec_module(h)
    app=adsk.core.Application.get();doc=app.activeDocument;assert doc.name=='ASSEMBLE THE PRINTED LEG - centred DFM parts'
    design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent
    occs={o.component.name:o for o in root.occurrences};assert set(occs)==set(by)
    source=design.appearances.item(0);apps={}
    for key,rgb in {'servo':(48,57,64),'metal':(185,193,200),'pla':(45,154,160),'cap':(218,162,71),'extra':(133,119,168)}.items():
        a=design.appearances.addByCopy(source,'assembly_colour_'+key)
        for prop in a.appearanceProperties:
            c=adsk.core.ColorProperty.cast(prop)
            if c:c.value=adsk.core.Color.create(*rgb,255)
        apps[key]=a
    for p in data['parts']:
        occ=occs[p['name']];occ.transform2=matrix(p['transform']);occ.isLightBulbOn=True
        key=p['material']
        if key=='pla':key='extra' if p['name'] in ('yaw_case_saddle','case_cap_yaw') or 'spacer' in p['name'] else 'cap' if p['name'].startswith('case_cap') else 'pla'
        occ.appearance=apps[key];occ.component.opacity=1
        for b in h._bodies(occ):
            native=b.nativeObject or b;native.appearance=apps[key];native.parentComponent.opacity=1
    view=app.activeViewport;view.visualStyle=adsk.core.VisualStyles.ShadedWithVisibleEdgesOnlyVisualStyle;cam=view.camera;cam.cameraType=adsk.core.CameraTypes.OrthographicCameraType
    cam.eye=adsk.core.Point3D.create(39,-52,28);cam.target=adsk.core.Point3D.create(11,0,-5);cam.upVector=adsk.core.Vector3D.create(0,0,1);cam.isFitView=True;view.camera=cam;view.fit()
    cam=view.camera;cam.viewExtents*=1.0;view.camera=cam
    for title,note,group in STAGES:
        for n,offset in group.items():occs[n].transform2=matrix(by[n]['transform'],offset)
    design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(OUT/'Exploded_Printed_Leg.f3d')))
    view.refresh();adsk.doEvents();view.saveAsImageFile(str(OUT/'exploded.png'),1280,960)
    for occ in occs.values():occ.isLightBulbOn=False
    records=[];index=0
    for stage,(title,note,group) in enumerate(STAGES,1):
        first=index
        for name in group:occs[name].isLightBulbOn=True
        for i in range(33):
            t=max(0,min(1,(i-5)/20));ease=.5-.5*math.cos(t*math.pi)
            for name,offset in group.items():occs[name].transform2=matrix(by[name]['transform'],[v*(1-ease) for v in offset])
            adsk.doEvents();view.refresh();view.saveAsImageFile(str(frames/f'{index:04d}.png'),960,720);index+=1
        view.saveAsImageFile(str(OUT/f'step_{stage:02d}.png'),1280,960)
        records.append({'stage':stage,'title':title,'note':note,'first_frame':first,'last_frame':index-1,'parts':list(group)})
    for p in data['parts']:
        actual=occs[p['name']].transform2;expected=matrix(p['transform'])
        assert max(abs(actual.getCell(i,j)-expected.getCell(i,j)) for i in range(4) for j in range(4))<1e-7
    design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(OUT/'Assembled_Printed_Leg.f3d')))
    view.saveAsImageFile(str(OUT/'assembled.png'),1280,960)
    result={'status':'completed','document_name':doc.name,'source_manifest_sha256':data['source_manifest_sha256'],'parts':len(by),'frames':index,'fps':8,'stages':records,
        'scope':'Exact CAD pieces animated in Fusion using explanatory exploded translations. Hardware quantities appear in captions; screws, nuts, washers and cables are not drawn. Exploded paths are illustrative, not a collision-tested installation path. Saved F3D files are the exploded and assembled states, not an Animation-workspace storyboard. No hardware actuation.'}
    (OUT/'animation_report.json').write_text(json.dumps(result,indent=2));return result
