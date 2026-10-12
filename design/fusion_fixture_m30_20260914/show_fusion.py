"""Show actual fixture assembly and a verified native revolute joint in Fusion."""
from pathlib import Path
import importlib.util,json,math,sys,time
import adsk.core,adsk.fusion
HERE=Path(__file__).resolve().parent
OUT=HERE/'fusion'
GROUP='fixture_teaching_m30_20260914'

def helper():
    path=HERE.parent/'hexapod_phone_quad_r5_20260912/cad/fusion_import.py'
    spec=importlib.util.spec_from_file_location('fixture_native_helpers',path)
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    m.DESTINATION=OUT;m.GROUP=GROUP;m.EXPECTED_LINKS=2;m.EXPECTED_JOINTS=1
    return m

def translate(xyz):
    m=adsk.core.Matrix3D.create();m.translation=adsk.core.Vector3D.create(*(v/10 for v in xyz));return m

def import_part(app,root,name,path):
    occ=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());occ.component.name=name
    opt=app.importManager.createSTEPImportOptions(str(path));opt.isViewFit=False
    app.importManager.importToTarget2(opt,occ.component)
    return occ

def camera(app):
    view=app.activeViewport;c=view.camera;c.cameraType=adsk.core.CameraTypes.OrthographicCameraType
    c.eye=adsk.core.Point3D.create(11,-16,12);c.target=adsk.core.Point3D.create(0,0,0)
    c.upVector=adsk.core.Vector3D.create(0,0,1);c.isFitView=True;view.camera=c;view.fit();view.refresh();adsk.doEvents()

def paint(app,design,h,occurrences):
    source=h._appearance_source(app)
    if source is None:return
    colors={'fixed':(65,73,80),'moving':(45,157,163),'bridge':(217,155,55),'gauge':(220,106,62)}
    apps={}
    for name,rgb in colors.items():
        a=design.appearances.addByCopy(source,'Fixture_'+name)
        for prop in a.appearanceProperties:
            p=adsk.core.ColorProperty.cast(prop)
            if p:p.value=adsk.core.Color.create(*rgb,255);break
        apps[name]=a
    for name,occ in occurrences.items():
        key='fixed' if 'FIXED' in name or name=='base' or 'clamp' in name else 'gauge' if 'gauge' in name else 'bridge' if 'bridge' in name or 'spacer' in name else 'moving'
        occ.appearance=apps[key]
        for body in h._bodies(occ):
            native=body.nativeObject or body
            native.appearance=apps[key]

def frame(app,folder,index):
    app.activeViewport.refresh();adsk.doEvents()
    app.activeViewport.saveAsImageFile(str(folder/f'{index:04d}.png'),960,720)

def run(context):
    OUT.mkdir(parents=True,exist_ok=True);h=helper();app=adsk.core.Application.get()
    manifest=json.loads((HERE/'fixture_manifest.json').read_text())
    doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    doc.name='ASSEMBLY DEMO - gauge removed before movement - M3x30'
    doc.attributes.add(GROUP,'kind','exploded')
    design=adsk.fusion.Design.cast(app.activeProduct);design.designType=adsk.fusion.DesignTypes.DirectDesignType
    root=design.rootComponent
    parts={p['name']:import_part(app,root,p['name'],p['step']) for p in manifest['parts']}
    clamp=import_part(app,root,'TEST ONLY - existing clamp',HERE/'assets/alignment_clamp.step')
    gauge=import_part(app,root,'TEST ONLY - remove gauge before motion',HERE/'assets/alignment_gauge.step')
    paint(app,design,h,{**parts,'clamp':clamp,'gauge':gauge})
    for occ in parts.values():occ.isLightBulbOn=False
    gauge.transform2=translate((0,0,38));camera(app)
    seq=OUT/'assembly_frames';seq.mkdir(exist_ok=True);index=0;stages=[]
    for name,start,end,n in [('Gauge seats for alignment only',38,0,18),('Remove gauge before motion',0,55,18)]:
        for i in range(n):
            t=i/(n-1);t=t*t*(3-2*t);gauge.transform2=translate((0,0,start+(end-start)*t))
            frame(app,seq,index);index+=1
        stages.append({'stage':name,'last_frame':index-1})
    gauge.isLightBulbOn=False;clamp.isLightBulbOn=False
    for p in manifest['parts']:
        occ=parts[p['name']];occ.isLightBulbOn=True;occ.transform2=translate(p['explode_mm'])
    camera(app)
    for i in range(26):
        t=i/25;t=t*t*(3-2*t)
        for p in manifest['parts']:parts[p['name']].transform2=translate([v*(1-t) for v in p['explode_mm']])
        frame(app,seq,index);index+=1
    stages.append({'stage':'Horn fixture assembles around fixed servo case','last_frame':index-1})
    export=design.exportManager
    export.execute(export.createFusionArchiveExportOptions(str(OUT/'fixture_exploded_assembly.f3d')))
    # A separate native design keeps the true revolute joint independent of
    # the temporary exploded offsets used above.
    identity=[[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.]]
    links={'base':{'_step_path':str(HERE/'assets/base.step'),'assembly_transform':identity},
           'output':{'_step_path':str(HERE/'assets/output.step'),'assembly_transform':identity,
              'joint':{'parent':'base','origin_mm':[0,0,0],'axis':[0,1,0],
                       'type':'revolute','neutral_angle_rad':0,'limits_rad':[math.radians(-10),math.radians(10)]}}}
    state={'warnings':[]}
    native_doc,native=h._import(app,links,['base','output'],'fixture_m30_native_v1',state)
    native_doc.name='MOVE THIS - case fixed, cheeks and bridge rotate - M3x30'
    native_doc.attributes.add(GROUP,'kind','motion')
    h._joints(native,links,['base','output'],state)
    occs=h._occurrences(native,links);paint(app,native,h,occs)
    native.rootComponent.isJointsFolderLightBulbOn=False
    for occ in occs.values():occ.component.isConstructionFolderLightBulbOn=False;occ.component.isSketchFolderLightBulbOn=False
    joint=native.rootComponent.asBuiltJoints.item(0);joint.name='Drive this joint - output only - +/-10deg'
    camera(app)
    seq2=OUT/'motion_frames';seq2.mkdir(exist_ok=True)
    before=h._matrix_mm(occs['base'].transform2)
    for i in range(61):
        angle=math.radians(10)*math.sin(i/60*4*math.pi)
        joint.jointMotion.rotationValue=angle;adsk.doEvents();frame(app,seq2,i)
        assert h._matrix_mm(occs['base'].transform2)==before
    joint.jointMotion.rotationValue=0;adsk.doEvents()
    native.exportManager.execute(native.exportManager.createFusionArchiveExportOptions(str(OUT/'fixture_working_revolute_joint.f3d')))
    app.activeViewport.saveAsImageFile(str(OUT/'fixture_assembled.png'),1500,1100)
    state.update(status='completed',assembly_document=doc.name,motion_document=native_doc.name,
        assembly_frames=index,motion_frames=61,assembly_stages=stages,
        scope='Actual native Fusion joint motion; not physical servo actuation or force dynamics.',
        gauge_removed_before_motion=True,case_stationary_in_all_motion_frames=True)
    (OUT/'demo_report.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    return state
