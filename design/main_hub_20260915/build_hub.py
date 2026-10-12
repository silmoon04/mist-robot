"""Printable four-leg deck matched to the centred DFM leg interfaces."""
from pathlib import Path
import sys,json,math,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output';R7=ROOT.parent/'single_leg_r7_wide_joints_20260914'
sys.path.insert(0,str(R7/'cad'))
import geom as g,build as lb,leg
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
ANGLES={'FL':45,'FR':-45,'RL':135,'RR':-135}
THICKNESS=6.;YAW_RADIUS=75.;YAW_HEIGHT=38.

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hole(x,y,r=1.7):return g.cylinder(r,30,(x,y,-2))
def point(x,y,deg):
    a=math.radians(deg);return (x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a))

def make_hub():
    poly=[(103*math.cos(math.radians(a)),103*math.sin(math.radians(a))) for a in range(30,390,60)]
    hub=g.prism_xy(poly,0,THICKNESS);holes=[]
    # Upward ribs lie between the fixed servo case envelopes. Flat underside
    # and open-through holes make the entire body a no-support print.
    hub=g.fuse(hub,g.box(135,8,6,(0,0,9)),g.box(8,146,6,(0,0,9)))
    # Full-width bearing strips carry the outer feet beyond the hex edge.
    for deg in ANGLES.values():
        for side in (-1,1):hub=g.fuse(hub,g.rotate(g.box(51,12,THICKNESS,(YAW_RADIUS-10.5,side*20,THICKNESS/2)),(0,0,1),deg))
    for deg in ANGLES.values():
        # Preserve the R5 mounting radius and all four saddle foot locations.
        plug=g.fuse(g.box(60,29,20,(YAW_RADIUS-15,0,6)),g.cylinder(15,20,(YAW_RADIUS,0,-2)))
        # Front sweep relief outside a 30 mm radius permits the longer coxa.
        front=g.cut(g.box(100,150,22,(YAW_RADIUS+50,0,6)),g.cylinder(30,30,(YAW_RADIUS,0,-5)))
        hub=g.cut(hub,g.rotate(plug,(0,0,1),deg),g.rotate(front,(0,0,1),deg))
        for x,y in leg.CONSTANTS['mount_holes_xy']:
            xy=point(YAW_RADIUS+x,y,deg);holes.append({'kind':'yaw_saddle','angle_deg':deg,'xy_mm':xy});hub=g.cut(hub,hole(*xy))
    for kind,coords in [('cover',[(78,0),(-78,0),(0,90),(0,-90)]),('future_central_mount',[(x,y) for x in (-14,14) for y in (-8,8)])]:
        for xy in coords:hub=g.cut(hub,hole(*xy));holes.append({'kind':kind,'xy_mm':xy})
    # Retain the established strap interfaces, avoiding the structural ribs.
    for x in (-30,0,30):
        for y in (-16,16):hub=g.cut(hub,g.box(12,3.6,20,(x,y,6)))
    for x in (-65,65):
        for y in (-15,15):hub=g.cut(hub,g.box(3.6,10,20,(x,y,6)))
    for x in (-14,14):hub=g.cut(hub,g.box(3.6,16,20,(x,67,6)))
    assert g.valid(hub)
    count=0;e=TopExp_Explorer(hub,TopAbs_SOLID)
    while e.More():count+=1;e.Next()
    assert count==1,count
    # Confirm real remaining bearing area around each mounting bore.
    seats=[]
    for row in holes:
        x,y=row['xy_mm'];r=2.85 if row['kind']=='yaw_saddle' else 3.5
        ring=g.cut(g.cylinder(r,THICKNESS,(x,y,0)),g.cylinder(1.7,THICKNESS,(x,y,0)))
        fraction=g.common_volume(ring,hub)/g.volume(ring)
        assert fraction>.999,(row,fraction)
        seats.append(dict(row,annular_material_fraction=fraction,outer_radius_mm=r))
    return hub,seats

def local_frames(yaw,hip,knee):
    f={'base_mount':np.eye(4),'coxa':lb.pose(rpy=(0,0,yaw))};f['femur']=f['coxa']@lb.pose((82,0,0),(0,hip,0));f['tibia']=f['femur']@lb.pose((90,0,0),(0,knee,0));return f

def main():
    OUT.mkdir(exist_ok=True);hub,seats=make_hub();g.export_step(hub,OUT/'Main_Hub_4Leg.step');g.export_stl(hub,OUT/'Main_Hub_4Leg.stl',.04)
    previous=ROOT.parent/'print_dfm_20260914/output';m=json.loads((previous/'manifest.json').read_text())
    records=[]
    hardware={p['name']:p['shape'] for p in leg.build_leg() if not p['printable']}
    for p in m['parts']:
        if p['name']=='bench_mounting_plate':continue
        if p['printable']:shape=g.import_step(previous/'parts_step'/(p['name']+'.step'))
        else:shape=hardware[p['name']]
        lo,hi=g.bounds(shape);corners=np.array([[x,y,z,1] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])]);records.append((p,shape,corners))
    hits=[];checks=0;rows=[];hb=g.bounds(hub);min_gap=1e9
    # Includes operating edges and five-degree guards. Hip/knee extremes
    # cover under-body sweeps; samples do not establish all inter-leg motion.
    samples=[(yaw,hip,knee) for yaw in (-60,-55,-30,0,30,55,60) for hip,knee in [(-35,0),(-30,5),(30,81),(65,115),(70,120)]]
    full=[]
    for label,deg in ANGLES.items():
        x,y=point(YAW_RADIUS,0,deg);mount=lb.pose((x,y,YAW_HEIGHT),(0,0,deg));neutral=local_frames(0,30,81)
        for p,s,corners in records:full.append(lb.shape_at(s,mount@neutral[p['link']]))
        for yaw,hip,knee in samples:
            frames=local_frames(yaw,hip,knee)
            for p,s,corners in records:
                t=mount@frames[p['link']];xyz=(corners@t.T)[:,:3];lo,hi=xyz.min(axis=0),xyz.max(axis=0)
                if any(hi[i]<=hb[0][i]+1e-6 or hb[1][i]<=lo[i]+1e-6 for i in range(3)):continue
                checks+=1;world=lb.shape_at(s,t);v=g.common_volume(hub,world)
                if v>.01:hits.append({'leg':label,'angles':[yaw,hip,knee],'part':p['name'],'mm3':v})
            rows.append({'leg':label,'angles':[yaw,hip,knee]})
        print(label,'checks',checks,'hits',len(hits),flush=True)
    report={'status':'pass' if not hits else 'fail','hub_stl_sha256':sha(OUT/'Main_Hub_4Leg.stl'),'source_leg_manifest_sha256':sha(previous/'manifest.json'),
        'dimensions_mm':[hb[1][i]-hb[0][i] for i in range(3)],'deck_thickness_mm':THICKNESS,'rib_top_z_mm':12,'yaw_radius_mm':75,'yaw_origin_z_mm':YAW_HEIGHT,
        'mounting_seats':seats,'leg_mount_angles_deg':ANGLES,'valid_single_solid':True,'hub_leg_boolean_checks':checks,'sampled_leg_poses':rows,'intersections':hits,
        'solid_volume_mm3':g.volume(hub),'scope':'Exact hub versus fixed and moving leg solids at sampled individual poses. No full-robot walking, inter-leg collision, motor torque or material failure validation. Retains cover bolt pattern; legacy battery tray is not compatible with the revised openings. New central mounting holes are reserved for a future tray. Cover and electronics interfaces require rechecking for the thicker ribbed deck.'}
    (OUT/'Hub_Check.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:report[k] for k in ['status','dimensions_mm','hub_leg_boolean_checks','intersections']}),flush=True)
    assert not hits,hits
    g.export_step([hub,*full],OUT/'Hub_With_Four_Legs.step')

if __name__=='__main__':main()

