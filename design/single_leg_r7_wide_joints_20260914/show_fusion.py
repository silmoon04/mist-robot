"""Open the released single leg with three native revolute joints."""
from pathlib import Path
import importlib.util,sys,json,math
import adsk.core,adsk.fusion
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output';DEST=OUT/'fusion'

def run(context):
    DEST.mkdir(exist_ok=True)
    spec=importlib.util.spec_from_file_location('r7_fusion_helpers',ROOT.parent/'hexapod_phone_quad_r5_20260912/cad/fusion_import.py')
    h=importlib.util.module_from_spec(spec);sys.modules[spec.name]=h;spec.loader.exec_module(h)
    h.DESTINATION=DEST;h.GROUP='single_leg_r7_wide_joints_20260914';h.EXPECTED_LINKS=4;h.EXPECTED_JOINTS=3
    data=json.loads((OUT/'manifest.json').read_text());order=['base','coxa','femur','tibia'];links={}
    for name in order:
        src='base_mount' if name=='base' else name
        links[name]={'_step_path':str(OUT/'links'/(src+'.step')),'assembly_transform':data['frames'][src]}
    for name,parent,origin,axis,neutral,limits in [('coxa','base',[0,0,0],[0,0,1],0,[-55,55]),('femur','coxa',[82,0,0],[0,1,0],30,[-30,65]),('tibia','femur',[90,0,0],[0,1,0],81,[5,115])]:
        links[name]['joint']={'parent':parent,'origin_mm':origin,'axis':axis,'type':'revolute','neutral_angle_rad':math.radians(neutral),'limits_rad':list(map(math.radians,limits))}
    state={'warnings':[]};app=adsk.core.Application.get()
    digest=h.hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest()
    doc,design=h._import(app,links,order,digest,state);doc.name='Single leg R7 - wide yaw hip and knee - M3x30'
    h._joints(design,links,order,state)
    occs=h._occurrences(design,links)
    for occ in occs.values():occ.component.isSketchFolderLightBulbOn=False;occ.component.isConstructionFolderLightBulbOn=False
    design.rootComponent.isJointsFolderLightBulbOn=False
    view=app.activeViewport;cam=view.camera;cam.cameraType=adsk.core.CameraTypes.OrthographicCameraType
    cam.eye=adsk.core.Point3D.create(38,-46,24);cam.target=adsk.core.Point3D.create(3,0,-5);cam.upVector=adsk.core.Vector3D.create(0,0,1);cam.isFitView=True
    view.camera=cam;view.fit();cam=view.camera;cam.viewExtents*=1.8;view.camera=cam;view.refresh();adsk.doEvents()
    joints={j.name:j for j in design.rootComponent.asBuiltJoints}
    seq=DEST/'motion_frames';seq.mkdir(exist_ok=True)
    index=0;stages=[]
    for name,neutral,values in [('coxa',0,[0,-55,55,0]),('femur',30,[30,-30,65,30]),('tibia',81,[81,5,115,81])]:
        first=index
        for start,end in zip(values,values[1:]):
            for i in range(21):
                t=.5-.5*math.cos(math.pi*i/20);angle=start+(end-start)*t
                joints['J_'+name].jointMotion.rotationValue=math.radians(angle-neutral)
                adsk.doEvents();view.refresh();view.saveAsImageFile(str(seq/f'{index:04d}.png'),960,720);index+=1
        stages.append({'joint':name,'first_frame':first,'last_frame':index-1,'positions_deg':values})
    for joint in joints.values():joint.jointMotion.rotationValue=0
    adsk.doEvents();view.refresh();view.saveAsImageFile(str(DEST/'assembled.png'),1500,1100)
    design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(DEST/'Single_Leg_R7.f3d')))
    state.update(status='completed',manifest_sha256=digest,native_revolute_count=len(joints),motion_frames=index,motion_stages=stages,document_name=doc.name,
        scope='Native revolute motion with independent one-degree axis probes. No physical servo actuation or printed-material strength simulation.')
    (DEST/'fusion_report.json').write_text(json.dumps(state,indent=2))
    return state
