"""MIST leg candidate shared by native Fusion and offline OpenCascade.

Dimensions in recipes are mm. Poses and mount datums follow simulation/model.py.
Purchased belt teeth, servo horn interfaces and shaft torque couplings remain
measurement/design gates; reference envelopes are never a print release.
"""
from __future__ import annotations
import math
import hashlib
import json
from pathlib import Path
from leg_gears import involute_spur_points

COLORS = {"white": (235,234,225,255), "structure": (66,77,86,255),
          "metal": (170,182,192,255), "gear": (39,154,164,255),
          "black": (22,29,34,255), "servo": (53,73,93,255),
          "reference": (191,128,71,180)}

def _mat(angle=0, pitch=0, at=(0,0,0)):
    a,b=math.radians(angle),math.radians(-pitch)
    ca,sa,cb,sb=math.cos(a),math.sin(a),math.cos(b),math.sin(b)
    return [[ca*cb,-sa,ca*sb,at[0]],[sa*cb,ca,sa*sb,at[1]],[-sb,0,cb,at[2]],[0,0,0,1]]

def _point(matrix, point):
    return [sum(matrix[i][j]*point[j] for j in range(3))+matrix[i][3] for i in range(3)]

def _capsule_points(length, radius, samples=14):
    # XY outline of a capsule extending down local Y; extrude along leg Y.
    upper=[(radius*math.cos(math.pi*i/samples),radius*math.sin(math.pi*i/samples)) for i in range(samples+1)]
    lower=[(radius*math.cos(math.pi+math.pi*i/samples),-length+radius*math.sin(math.pi+math.pi*i/samples)) for i in range(samples+1)]
    return upper+lower

def leg_spec(params, leg_name="FL", yaw_deg=None, hip_deg=None, knee_deg=None,
             fit_parameters=None, clearance_parameters=None):
    """Return part recipes with rigid world transforms and explicit interface gates."""
    fit_source=Path(__file__).parents[1]/"coupons"/"fit_parameters.json"
    fit_raw=fit_source.read_bytes() if fit_parameters is None else json.dumps(fit_parameters,sort_keys=True).encode()
    fit_snapshot=json.loads(fit_raw)
    fits=fit_snapshot["interfaces"]
    clearances=dict(m3_clearance_diameter_mm=3.4,m4_clearance_diameter_mm=4.4,
                    shaft7_clearance_diameter_mm=7.3,shaft4_clearance_diameter_mm=4.3,
                    coupon_section_transfer_validated=False)
    clearances.update(clearance_parameters or {})
    seat=lambda od: fits["bearing_OD"+str(od)]["seat_diameter_mm"]/2
    g=params["geometry"]; names=g["leg_names"]; index=names.index(leg_name)
    belt_selection=dict(pitch_mm=3,pulley_teeth=32,width_mm=9,pitch_length_mm=375,
                        pulley_outer_diameter_mm=29.8,flange_diameter_mm=33.6,total_pulley_length_mm=20.6,
                        pulley_hub_diameter_mm=21.6,flange_thickness_mm=1.0,face_width_mm=10.25,
                        profile="GatesPowerGripGT3_3M_manufacturer_matched_metal_pulley")
    belt_selection.update(params["transmission"].get("remote_belt",{}))
    az=g["mount_azimuths_deg"][index]
    heading=g["drive_heading_deg"][index] if yaw_deg is None else az+float(yaw_deg)
    yaw=heading-az
    L=g["femur_m"]*1000; T=g["tibia_m"]*1000
    expected_center=(belt_selection["pitch_length_mm"]-belt_selection["pitch_mm"]*belt_selection["pulley_teeth"])/2
    if abs(L-expected_center)>0.01:
        raise ValueError(f"Selected375mm32Tx3mmbelt requires femur{expected_center}mm; update shared geometry before export")
    reach=g["drive_radial_reach_from_pitch_m"]*1000
    down=g["hip_to_wheel_axle_height_m"]*1000
    k=-math.acos(max(-1,min(1,(reach*reach+down*down-L*L-T*T)/(2*L*T))))
    h=math.atan2(reach,down)-math.atan2(T*math.sin(k),L+T*math.cos(k))
    h=math.degrees(h) if hip_deg is None else float(hip_deg)
    k=math.degrees(k) if knee_deg is None else float(knee_deg)
    ratios=params["transmission"]["ratios"]
    if any(abs(float(r)-2)>1e-9 for r in ratios):
        raise ValueError("This gear layout implements 20:40 teeth only; changed ratios require repackaging")
    mount=(g["hip_mount_radius_m"]*1000*math.cos(math.radians(az)),g["hip_mount_radius_m"]*1000*math.sin(math.radians(az)),0)
    hand=[1,-1,-1,1][index]
    transverse=g["hip_transverse_offset_m"]*1000*hand
    coxa=(g["hip_radial_offset_m"]*1000,transverse,0)
    base=_mat(az,at=mount); yawframe=_mat(heading,at=mount)
    yaw_motor_frame=_mat(az+hand*45,at=mount)
    pitchpoint=_point(yawframe,coxa)
    pod=_mat(heading,at=pitchpoint); femur=_mat(heading,h,pitchpoint)
    kneepoint=_point(femur,(0,0,-L)); tibia=_mat(heading,h+k,kneepoint)
    wheelpoint=_point(tibia,(0,0,-T)); wheel=_mat(heading,h+k,wheelpoint)
    frames={"body":base,"yaw":yawframe,"pod":pod,"femur":femur,"tibia":tibia,"wheel":wheel}
    parts=[]; bearings={}
    def part(name, link="pod", category="print", color="structure", note=""):
        p=dict(name=name,link=link,category=category,color=color,note=note,ops=[],transform=frames[link])
        parts.append(p); return p["ops"]
    def box(o,c,s,mode="add"): o.append(dict(kind="box",center=c,size=s,mode=mode))
    def cyl(o,a,b,r,inner=0,mode="add"):
        o.append(dict(kind="annulus" if inner else "cylinder",start=a,end=b,radius=r,inner=inner,mode=mode))
    def poly(o,points,y,thickness,mode="add"):
        o.append(dict(kind="polygon",points=points,origin=(0,y,0),normal=(0,-1,0),x_axis=(1,0,0),thickness=thickness,mode=mode))
    def yring(o,x,z,y0,y1,r,inner=0,mode="add"): cyl(o,(x,y0,z),(x,y1,z),r,inner,mode)
    def rotate_ops_z(ops,degrees):
        c,s=math.cos(math.radians(degrees)),math.sin(math.radians(degrees))
        def rotate(v): return (c*v[0]-s*v[1],s*v[0]+c*v[1],v[2])
        for op in ops:
            if op["kind"]=="box":
                cx,cy,cz=op["center"]; sx,sy,sz=op["size"]
                points=[rotate((cx+a*sx/2,cy+b*sy/2,0))[:2] for a,b in ((-1,-1),(1,-1),(1,1),(-1,1))]
                mode=op["mode"]
                op.clear(); op.update(kind="polygon",points=points,origin=(0,0,cz-sz/2),normal=(0,0,1),x_axis=(1,0,0),thickness=sz,mode=mode)
            elif op["kind"] in ("cylinder","annulus"):
                op["start"]=rotate(op["start"]); op["end"]=rotate(op["end"])
            elif op["kind"]=="polygon":
                for key in ("origin","normal","x_axis"): op[key]=rotate(op[key])
        return ops
    def motor_part(name,category="print",color="structure",note=""):
        ops=part(name,"body",category,color,note)
        parts[-1]["transform"]=yaw_motor_frame
        return ops
    def bolt(name,link,x,z,y0,y1,r=1.5,head_at_start=False):
        o=part(name,link,"hardware_reference","metal","Smooth shank envelope; length, threads and nut procurement remain pending")
        yring(o,x,z,y0,y1,r)
        yring(o,x,z,y0-2,y0,2.8) if head_at_start else yring(o,x,z,y1,y1+2,2.8)
    def bearing(name,link,x,z,y0,code,od,id,width):
        bearings[code]=bearings.get(code,0)+1
        o=part(name,link,"hardware_reference","metal",f"{code} nominal {id}x{od}x{width}mm; races/rolling elements simplified")
        yring(o,x,z,y0,y0+width,od/2,id/2)
    def gear(name,link,x,z,y0,bore,teeth,phase=0):
        o=part(name,link,"print","gear","Module1,20deg involute,8mm face; shaft/horn torque-lock interface unfinished")
        points=[(px+x,pz+z) for px,pz in involute_spur_points(teeth,phase_deg=phase,samples=3)]
        poly(o,points,y0+8,8); yring(o,x,z,y0-1,y0+9,bore/2+0.1,mode="cut")
        if teeth==20:
            for i in range(4):
                a=math.radians(phase)+i*math.pi/2
                yring(o,x+7*math.cos(a),z+7*math.sin(a),y0-1,y0+9,1.8,mode="cut")
    # Fixed yaw bearing bracket is separate from the rotating carriage.
    o=part("Y01_fixed_mount_bridge","body",note="FourM4holes:radial78/98,tangent+/-22mm;52mmbridge mates expanded bodytabs")
    box(o,(-12.5,0,-27.5),(43,52,5))
    cradle=[]
    yaw_fasteners=[(13.6,-25.5),(13.6,25.5),(64.73,-12),(64.73,12)]
    box(cradle,(40.115,0,-30),(53.23,32.73,3))
    for xx in (15.5,64.73): box(cradle,(xx,0,-10.5),(4,32.73,36))
    for sign in (-1,1):
        box(cradle,(13.6,sign*25.5,-12),(5.6,11,39))
        box(cradle,(13.6,sign*17,-12),(5.6,8,39))
    box(cradle,(11.25,0,-27.5),(12.5,32.73,5))
    for xx,yy in yaw_fasteners: cyl(cradle,(xx,yy,-32),(xx,yy,9),1.7,mode="cut")
    o.extend(rotate_ops_z(cradle,45))
    cyl(o,(0,0,-25),(0,0,12),17.1,mode="cut")
    pocket=[]
    box(pocket,(40.115,0,-11),(45.63,25.23,35),"cut")
    o.extend(rotate_ops_z(pocket,45))
    # Relieve the existing body tab below its top plane, while keeping the outer cradle floor.
    box(o,(-8.5,0,-32.5),(47,52,5),"cut")
    # Clearance for the existing body-core post, mirrored with the leg hardware.
    cyl(o,(108/math.sqrt(2)-103,12/math.sqrt(2),-31),
          (108/math.sqrt(2)-103,12/math.sqrt(2),-24),5.3,mode="cut")
    for x in (-25,-5):
        for y in (-22,22): cyl(o,(x,y,-31),(x,y,-24),2.2,mode="cut")
    cyl(o,(-5,22,-25),(-5,22,-19.5),4.7,mode="cut")
    cyl(o,(0,0,-31),(0,0,-24),4.3,mode="cut")
    for x in (-25,-5):
        for y in (-22,22):
            b=part(f"Y12_deck_M4_{x}_{y}","body","hardware_reference","metal","M4sockethead7mmODx4mm,washer9mmOD;3mmAllen approach before carriageinstallation")
            cyl(b,(x,y,-38.2),(x,y,-24),2)
            cyl(b,(x,y,-24),(x,y,-20),3.5)
            w=part(f"Y13_deck_washer_{x}_{y}","body","hardware_reference","metal","9mmODx1mm M4washer envelope")
            cyl(w,(x,y,-25),(x,y,-24),4.5,2.1)
            nut=part(f"Y14_deck_M4_nut_{x}_{y}","body","hardware_reference","metal","M4nut7mmAFx3.2mm under deck; underside toolaccess required")
            points=[(x+7/math.sqrt(3)*math.cos(i*math.pi/3),y+7/math.sqrt(3)*math.sin(i*math.pi/3)) for i in range(6)]
            nut.append(dict(kind="polygon",points=points,origin=(0,0,-38.2),normal=(0,0,1),x_axis=(1,0,0),thickness=3.2,mode="add"))
            cyl(nut,(x,y,-39),(x,y,-34),2,mode="cut")
    for z0,z1,label in ((-25,-13,"lower"),(0,11,"upper")):
        o=part("Y02_608_housing_"+label,"body",note="Bearing seat22.30mm provisional; printed shoulder and bolted retainer")
        cyl(o,(0,0,z0),(0,0,z1),16,4.3)
        seat0=-22 if label=="lower" else 2
        cyl(o,(0,0,seat0),(0,0,seat0+7.1),seat(22),mode="cut")
        for x in (-11,11):
            for y in (-8,8): cyl(o,(x,y,z0-1),(x,y,z1+1),1.7,mode="cut")
        o=part("Y03_608_"+label,"body","hardware_reference","metal","608 bearing nominal8x22x7mm")
        cyl(o,(0,0,seat0),(0,0,seat0+7),11,4); bearings["608"]=bearings.get("608",0)+1
    for x in (-11,11):
        for y in (-8,8):
            o=part(f"Y04_fixed_standoff_{x}_{y}","body")
            cyl(o,(x,y,-13),(x,y,0),3.2,1.7)
    o=part("Y05_metal_yaw_shaft","yaw","hardware_reference","metal","8mm metalshaft; axial retention and torque-lock geometry pending")
    cyl(o,(0,0,-26),(0,0,28),4)
    o=part("Y06_yaw_output_40T","body",color="gear",note="Yaw gear phase follows yaw; provisional8.2mm bore lacks torque key")
    o.append(dict(kind="polygon",points=involute_spur_points(40,phase_deg=hand*yaw,samples=3),origin=(0,0,12),normal=(0,0,1),x_axis=(1,0,0),thickness=8,mode="add"))
    cyl(o,(0,0,11),(0,0,21),4.1,mode="cut")
    o=motor_part("Y07_yaw_input_20T",color="gear",note="Maker horn pattern; motor station45deg aroundyawaxis")
    o.append(dict(kind="polygon",points=involute_spur_points(20,phase_deg=9-2*hand*yaw,samples=3),origin=(30,0,12),normal=(0,0,1),x_axis=(1,0,0),thickness=8,mode="add"))
    cyl(o,(30,0,11),(30,0,21),2.75,mode="cut")
    for i in range(4):
        a=math.radians(9-2*hand*yaw)+i*math.pi/2
        cyl(o,(30+7*math.cos(a),7*math.sin(a),11),(30+7*math.cos(a),7*math.sin(a),21),1.8,mode="cut")
    o=motor_part("S01_C018_yaw_CASE","hardware_reference","servo","Maker45.23x24.73x35mmcase; axis12.5mmfrom short end; projections/cable need physical check")
    box(o,(40.115,0,-11),(45.23,24.73,35))
    o=motor_part("Y08_factory_horn","hardware_reference","metal","Maker19.95OD,14BCD,4.5mmthick;M3threads simplified3mmbores")
    cyl(o,(30,0,7.5),(30,0,12),9.975,2.75)
    for i in range(4):
        a=math.radians(9-2*hand*yaw)+i*math.pi/2
        cyl(o,(30+7*math.cos(a),7*math.sin(a),7),(30+7*math.cos(a),7*math.sin(a),13),1.5,mode="cut")
    o=motor_part("Y09_servo_clamp_cap",note="Rigid bolt-land stops; clearance window leaves factoryhorn accessible")
    box(o,(40.115,0,9.5),(53.23,32.73,4))
    for sign in (-1,1):
        box(o,(13.6,sign*25.5,9.5),(5.6,11,4))
        box(o,(13.6,sign*17,9.5),(5.6,8,4))
    box(o,(53,0,7.35),(16,22,0.3))
    box(o,(53,0,7.3),(14,20,0.4),"cut")
    cyl(o,(30,0,7),(30,0,12),11,mode="cut")
    cyl(o,(0,0,7),(0,0,12),16.3,mode="cut")
    for xx,yy in yaw_fasteners: cyl(o,(xx,yy,7),(xx,yy,13),1.7,mode="cut")
    o=motor_part("Y10_captured_TPU_pad","print","black","TPU95A candidate,1.2mmfree/1.0mmassembled; preload remains unmeasured")
    box(o,(53,0,7),(14,20,1))
    parts[-1].update(material="TPU95A_candidate",density_g_cm3=1.2,free_thickness_mm=1.2,assembled_thickness_mm=1.0,
                     free_shape_ops=[dict(kind="box",mode="add",center=(0,0,.6),size=(14,20,1.2))])
    for xx,yy in yaw_fasteners:
        b=motor_part(f"Y11_cap_M3_{xx}_{yy}","hardware_reference","metal","M3fastener envelope;clamp screws assemble from above")
        cyl(b,(xx,yy,-30 if xx==13.6 else -31.5),(xx,yy,11.5),1.5)
        cyl(b,(xx,yy,11.5),(xx,yy,14),2.8)
    # A removable dogleg bridge rotates around the yaw shaft above the gear.
    o=part("P01_rotating_coxa_bridge","yaw",note="35mm radial and mirrored30mm transverse datum; lower strut clearance is pose-dependent")
    coxa_ops=o
    cyl(o,(0,0,22),(0,0,28),10,4.2)
    dx,dy=coxa[0],coxa[1]; length=math.hypot(dx,dy)
    nx,ny=-dy/length*7,dx/length*7
    o.append(dict(kind="polygon",points=[(nx,ny),(dx+nx,dy+ny),(dx-nx,dy-ny),(-nx,-ny)],origin=(0,0,22),normal=(0,0,1),x_axis=(1,0,0),thickness=6,mode="add"))
    cyl(o,(0,0,21),(0,0,29),4.2,mode="cut")
    box(o,(dx,dy,25),(22,116,6))
    # Two side flanges meet the actual saddle ears. M3 bolts run along local X.
    for prefix,yc,ylo,yhi in (("H",-62,-65,-58.5),("K",62.5,59,66)):
        if prefix=="H": box(o,(dx+6.75,dy-hand*60,25),(13.5,8,6))
        else: box(o,(dx+6.75,dy+hand*62,25),(13.5,10,6))
        box(o,(dx+6.75,dy+hand*(ylo+yhi)/2,-6),(13.5,yhi-ylo,56))
        cyl(o,(dx,dy+hand*(ylo-1),0),(dx,dy+hand*(yhi+1),0),3.7,mode="cut")
        for zz in (-31,-24): cyl(o,(dx-1,dy+hand*yc,zz),(dx+15,dy+hand*yc,zz),1.7,mode="cut")
    cyl(o,(dx+15.5,dy+hand*67,16.7),(dx+15.5,dy+hand*67,24),3.1,mode="cut")
    # Independently supported opposing 7mm trunnions stop 10mm apart.
    for prefix,centers,od,code in (("H",(-42.5,-24.5),14,"687"),("K",(8.5,41.5),22,"627")):
        width=5 if code=="687" else 7
        for j,y in enumerate(centers):
            y0=y-width/2
            bearing(f"{prefix}01_{code}_{j}","pod",0,0,y0,code,od,7,width)
            o=part(f"{prefix}02_bearing_tower_{j}",note=f"Coupon-linked{seat(od)*2:.2f}mmseat;2mm shoulder differs from1.2mmcoupon, so transfer unvalidated")
            yring(o,0,0,y0-2,y0+width,od/2+4,3.7)
            box(o,(0,y0+(width-2)/2,12),(od+8,width+2,20))
            yring(o,0,0,y0-0.1,y0+width+1,seat(od),mode="cut")
            yring(o,0,0,y0-3,y0+width+1,3.7,mode="cut")
            for x in (-od/2-2.1,od/2+2.1): yring(o,x,0,y0-3,y0+width+1,1.7,mode="cut")
            tower_y=y0+(width-2)/2
            cyl(o,(0,tower_y,14),(0,tower_y,29),1.7,mode="cut")
            box(o,(0,tower_y,15.2),(5.8,width+4,2.6),"cut")
            cyl(coxa_ops,(dx,dy+hand*tower_y,21),(dx,dy+hand*tower_y,29),1.7,mode="cut")
            b=part(f"{prefix}14_tower_to_coxa_M3_{j}","pod","hardware_reference","metal","M3 bolt clamps tower roof to co xa bridge throughcapturednut")
            cyl(b,(0,tower_y,14.1),(0,tower_y,28),1.5)
            cyl(b,(0,tower_y,28),(0,tower_y,30.5),2.8)
            b=part(f"{prefix}15_tower_M3_nut_{j}","pod","hardware_reference","metal","M3nut5.5mmAFx2.4mm; accessible cross-slot in bearing tower")
            points=[(5.5/math.sqrt(3)*math.cos(math.pi/6+i*math.pi/3),tower_y+5.5/math.sqrt(3)*math.sin(math.pi/6+i*math.pi/3)) for i in range(6)]
            b.append(dict(kind="polygon",points=points,origin=(0,0,14.1),normal=(0,0,1),x_axis=(1,0,0),thickness=2.4,mode="add"))
            cyl(b,(0,tower_y,14),(0,tower_y,17),1.5,mode="cut")
            o=part(f"{prefix}03_bearing_keeper_{j}",note="TwoM3 throughbolts; keeper bore clears rotating inner race")
            yring(o,0,0,y0+width+0.2,y0+width+2.2,od/2+4,od/2-1)
            for x in (-od/2-2.1,od/2+2.1):
                yring(o,x,0,y0+width,y0+width+3,1.7,mode="cut")
                bolt(f"{prefix}04_keeper_bolt_{j}_{x}","pod",x,0,y0-2,y0+width+2.2,head_at_start=not(prefix=="K" and j==1))
    o=part("H05_hip_metal_trunnion","femur","hardware_reference","metal","7mm smooth shaft -47..-5mm; gear/femur clamps and axial lock unfinished")
    yring(o,0,0,-60,-5,3.5)
    o=part("K05_remote_metal_trunnion","pod","hardware_reference","metal","7mm shaft+5..55mm; pulley bracketed by627pair;10mm gap from hip shaft")
    yring(o,0,0,5,65,3.5)
    for prefix,y0,phase,casey in (("H",-58,h,-81),("K",50,h+k,81)):
        gear(prefix+"06_output_40T","pod",0,0,y0,7,40,phase)
        gear(prefix+"07_input_20T","pod",30,0,y0,5,20,9-2*phase)
        o=part("S02_C018_"+prefix+"_CASE","pod","hardware_reference","servo","Maker45.23x24.73x35mmcase,12.5mmshort-endaxis;no conventional ears")
        box(o,(40.115,casey,0),(45.23,35,24.73))
        horn0=y0-4.5 if prefix=="H" else y0+8
        o=part(prefix+"09_factory_horn","pod","hardware_reference","metal","Maker19.95OD,14BCD,4.5mmthick;M3threads simplified3mmbores")
        yring(o,30,0,horn0,horn0+4.5,9.975,2.75)
        for i in range(4):
            a=math.radians(9-2*phase)+i*math.pi/2
            yring(o,30+7*math.cos(a),7*math.sin(a),horn0-1,horn0+5.5,1.5,mode="cut")
        o=part(prefix+"08_servo_saddle",note="Maker case datum; bolted coxa ears and controlled clamp lands")
        box(o,(40.115,casey,-15.365),(53.23,39,6))
        for x in (15.5,64.73): box(o,(x,casey,-1.5),(4,39,26))
        for x in (15.5,64.73):
            for y in (casey-14,casey+14): cyl(o,(x,y,-19),(x,y,13),1.7,mode="cut")
        ear_y=-62 if prefix=="H" else 62.5
        box(o,(17,ear_y,-23.75),(7,8,22.5))
        for zz in (-31,-24):
            cyl(o,(12,ear_y,zz),(22,ear_y,zz),1.7,mode="cut")
        nearest_y=casey+(14 if prefix=="H" else -14)
        cyl(o,(15.5,nearest_y,-19),(15.5,nearest_y,-12),1.7,mode="cut")
        pocket=fits["servo_body_width"]["pocket_mm"]
        pad_compressed=pocket-24.73
        if not 0.1<=pad_compressed<=1.5: raise ValueError("Servo width fit requires a redesigned clamp pad outside0.1..1.5mm")
        cap_bottom=12.365+pad_compressed
        for x in (15.5,64.73):
            for y in (casey-14,casey+14):
                box(o,(x,y,(11.5+cap_bottom)/2),(4,6,cap_bottom-11.5))
                cyl(o,(x,y,11),(x,y,cap_bottom+1),1.7,mode="cut")
        for zz in (-31,-24):
            b=part(prefix+f"11_saddle_to_coxa_M3_{zz}","pod","hardware_reference","metal","ThroughM3bolt;captured nut/washer detail remains pending")
            cyl(b,(0,ear_y,zz),(20.5,ear_y,zz),1.5)
            cyl(b,(20.5,ear_y,zz),(23.3,ear_y,zz),2.8)
        o=part(prefix+"10_servo_clamp_cap",note="Hard stops set coupon-linked25.23mmpocket; capturedTPUpad supplies preload")
        box(o,(40.115,casey,cap_bottom+2),(53.23,39,4))
        box(o,(40.115,casey,cap_bottom-0.15),(32,22,0.3))
        box(o,(40.115,casey,cap_bottom-0.2),(30,20,0.4),"cut")
        for x in (15.5,64.73):
            for y in (casey-14,casey+14): cyl(o,(x,y,11),(x,y,18),1.7,mode="cut")
        o=part(prefix+"12_captured_TPU_pad","pod","print","black","TPU95A candidate:free thickness0.7mm,assembled0.5mm nominal;preload not measured")
        box(o,(40.115,casey,12.365+pad_compressed/2),(30,20,pad_compressed))
        parts[-1].update(material="TPU95A_candidate",density_g_cm3=1.2,
                         free_thickness_mm=pad_compressed+0.2,assembled_thickness_mm=pad_compressed,
                         free_shape_ops=[dict(kind="box",mode="add",center=(0,0,(pad_compressed+0.2)/2),size=(30,20,pad_compressed+0.2))])
        for x in (15.5,64.73):
            for y in (casey-14,casey+14):
                b=part(prefix+f"13_cap_M3_{x}_{y}","pod","hardware_reference","metal","Smooth fastener envelope,threads/nut detail pending")
                cyl(b,(x,y,-18.365),(x,y,cap_bottom+4),1.5)
                cyl(b,(x,y,cap_bottom+4),(x,y,cap_bottom+6.5),2.8)
    # Femur cheeks place the purchased belt on the positive-Y side.
    for label,y0,first in (("drive",-13,0),("belt",38,-35)):
        o=part("F01_femur_cheek_"+label,"femur",note="6mm PETG cheek with30mmOD608boss;1.2mmfloor/7.2mmseatdepth fromcoupon; lead-in transfer pending")
        poly(o,_capsule_points(L,13),y0+6,6)
        if first: box(o,(0,y0+3,15),(50,10,100),"cut")
        boss0=-15.4 if not first else 38
        boss1=-7 if not first else 46.4
        yring(o,0,-L,boss0,boss1,16,10)
        yring(o,0,-L,boss0+1.2,boss1+0.1,seat(22),mode="cut")
        if first: yring(o,0,-L,boss0-1,boss1+1,10,mode="cut")
        for xx in (-13.5,13.5): yring(o,xx,-L,boss0-1,boss1+1,1.7,mode="cut")
        if not first: yring(o,0,0,y0-1,y0+7,3.65,mode="cut")
        for z in (-48,-85):
            for x in (-9,9): yring(o,x,z,y0-1,y0+7,1.7,mode="cut")
    for z in (-48,-85):
        for x in (-9,9):
            o=part(f"F02_femur_cross_spacer_{x}_{z}","femur")
            yring(o,x,z,-7,38,3.4,1.7)
            bolt(f"F03_femur_tie_{x}_{z}","femur",x,z,-13,44)
    pulley_r=belt_selection["pitch_mm"]*belt_selection["pulley_teeth"]/(2*math.pi)
    for label,z,link,bore in (("input",0,"pod",7),("output",-L,"femur",8)):
        o=part("F04_matched_metal_pulley_ENVELOPE_"+label,link,"hardware_reference","gear","MatchedGT3/GT2 32T3mm9mmbelt metalpulley;6mmsupplierbore reamedto7/8mm; toothgrooves unmodeled")
        yring(o,0,z,16,26.25,belt_selection["pulley_outer_diameter_mm"]/2,bore/2+0.1)
        yring(o,0,z,15,16,belt_selection["flange_diameter_mm"]/2,bore/2+0.1)
        yring(o,0,z,26.25,27.25,belt_selection["flange_diameter_mm"]/2,bore/2+0.1)
        yring(o,0,z,27.25,35.6,belt_selection["pulley_hub_diameter_mm"]/2,bore/2+0.1)
        parts[-1].update(material="aluminium_candidate",density_g_cm3=2.7,mass_provenance="Solidpulleyenvelope estimate; actualgrooves removed in supplied part")
    o=part("F05_purchased_belt_PITCH_RIBBON","femur","hardware_reference","black","375-3M-9 selected reinforcedbelt; ribbon marks pitchpath only,omits teeth; tensioner remains required")
    poly(o,_capsule_points(L,pulley_r+0.3,64),25.625,9)
    poly(o,_capsule_points(L,pulley_r-0.3,64),26.625,11,"cut")
    parts[-1].update(mass_g=10,mass_provenance="Unweighed10g reinforcedbelt estimate,not ribbon volume")
    # Distal knee rotates on a through steel shaft; bearings remain on femur.
    for j,y0 in enumerate((-14.2,39.2)):
        bearing(f"F06_knee_608_{j}","femur",0,-L,y0,"608",22,8,7)
        cap0=y0+7.2
        o=part(f"F07_knee_bearing_keeper_{j}","femur",note="Outer-race-only land; twoM3keepers and20mm central clearance forinner-racespacers")
        yring(o,0,-L,cap0,cap0+2,16,10)
        yring(o,0,-L,cap0-0.2,cap0,11,10)
        for xx in (-13.5,13.5):
            yring(o,xx,-L,cap0-1,cap0+3,1.7,mode="cut")
            bolt(f"F08_knee_keeper_M3_{j}_{xx}","femur",xx,-L,y0-1.2,cap0+2)
    for j,a,b in ((0,-16,-14.2),(1,-7.2,15),(2,35.6,39.2),(3,46.2,48.4)):
        o=part(f"T06_knee_inner_race_spacer_{j}","tibia","hardware_reference","metal","Steel12mmOD/8.2mmID spacer; verify actual608inner-race land before machining")
        yring(o,0,0,a,b,6,4.1)
        parts[-1].update(material="steel_candidate",density_g_cm3=7.85,mass_provenance="Solid metal spacer estimate")
    o=part("T01_knee_metal_shaft","tibia","hardware_reference","metal","8mm smooth steelshaft; external torqueclamps pending; replaces overloaded4mm shaft")
    yring(o,0,0,-24,52,4)
    o=part("T02_tibia_main_cheek","tibia",note="6mmPETG open yoke; wheel626support is separate from motor bearing")
    poly(o,_capsule_points(T,14),-16,6)
    yring(o,0,0,-23,-15,4.2,mode="cut")
    yring(o,0,-T,-23,-15,seat(19),mode="cut")
    for z in (-48,-75):
        for x in (-9,9): yring(o,x,z,-23,-15,1.7,mode="cut")
    o=part("T03_tibia_outer_cheek","tibia")
    poly(o,_capsule_points(T,14),32,6)
    box(o,(0,29,15),(60,10,100),"cut")
    yring(o,0,-T,25,33,seat(19),mode="cut")
    for xx in (-9,9): yring(o,xx,-T+15.5,25,33,1.7,mode="cut")
    for z in (-48,-75):
        for x in (-9,9): yring(o,x,z,25,33,1.7,mode="cut")
    for z in (-48,-75):
        for x in (-9,9):
            o=part(f"T04_tibia_cross_spacer_{x}_{z}","tibia")
            yring(o,x,z,-16,26,3.4,1.7)
            bolt(f"T05_tibia_tie_{x}_{z}","tibia",x,z,-22,32)
    # Wheel torque passes through a coupling to a separate 6mm supported axle.
    wr=g["wheel_diameter_m"]*500; ww=g["wheel_width_m"]*1000
    for j,y0 in enumerate((-22,26)):
        bearing(f"W01_wheel_626_{j}","wheel",0,0,y0,"626",19,6,6)
    o=part("W02_6mm_wheel_axle","wheel","hardware_reference","metal","Two626 supports;6mmwheelshaft to4mmDmotor requires a selected coupling")
    yring(o,0,0,-26,37,3)
    o=part("W03_wheel_hub","wheel","print","white","Bolt-on tirecarrier;6.2mm axle bore torque-lock unfinished")
    yring(o,0,0,-ww/2,ww/2,9,3.1)
    for i in range(6):
        a=2*math.pi*i/6; ca,sa=math.cos(a),math.sin(a)
        points=[(u*ca-v*sa,u*sa+v*ca) for u,v in ((6,-3),(wr-6.2,-3),(wr-6.2,3),(6,3))]
        poly(o,points,2,4)
    yring(o,0,0,-ww/2,ww/2,wr-6,wr-8.4)
    o=part("W04_tire_ENVELOPE","wheel","hardware_reference","black","85x24mm tire candidate; material,tread and measured rolling radius pending")
    yring(o,0,0,-ww/2,ww/2,wr,wr-6)
    o=part("W05_FIT0493_motor_CASE","wheel","hardware_reference","servo","Maker envelope:21mmØ25gearbox,40mmØ24.4motor/encoder;61mmface-to-rear; cable excluded")
    yring(o,0,0,49,70,12.5); yring(o,0,0,70,110,12.2)
    o=part("W06_FIT0493_4mmD_SHAFT","wheel","hardware_reference","metal","4mmDshaft12mmprotrusion;3.5mmacrossflat for8mm")
    yring(o,0,0,37,49,2)
    box(o,(0,41,2.25),(6,8,1.5),"cut")
    o=part("W07_motor_mount_cradle","wheel",note="61mm axial envelope held by open saddle; case clamp and holepattern unfinished")
    box(o,(0,77,-15.5),(33,62,6))
    for x in (-15,15): box(o,(x,77,-2),(3,62,24))
    box(o,(0,44,0),(28,4,31))
    box(o,(0,39,15.5),(28,14,6))
    yring(o,0,0,41,47,6.5,mode="cut")
    for xx in (-9,9): yring(o,xx,15.5,31,47,1.7,mode="cut")
    for xx in (-9,9): bolt(f"W08_motor_brace_M3_{xx}","wheel",xx,15.5,26,46)
    o=part("W09_6to4mm_coupling_ENVELOPE","wheel","hardware_reference","metal","Ø12x12mm stepped6.2/4.2bore coupling envelope; clamp/torque-lock design pending")
    yring(o,0,0,33,45,6,2.1)
    yring(o,0,0,32,37.5,3.1,mode="cut")
    parts[-1].update(material="aluminium_candidate",density_g_cm3=2.7,mass_provenance="Solid coupling envelope estimate")
    for p in parts:
        if p["category"]=="print" and "material" not in p: p.update(material="PETG",density_g_cm3=1.27)
        elif "C018" in p["name"]: p.update(mass_g=55,mass_provenance="C018maker55g nominal; includes complete actuator")
        elif p["name"]=="W05_FIT0493_motor_CASE": p.update(mass_g=98,mass_provenance="FIT0493maker98g nominal; includes shaft")
        elif p["name"]=="W06_FIT0493_4mmD_SHAFT": p.update(mass_g=0,mass_provenance="Included in complete98gFIT0493")
        elif p["name"]=="W04_tire_ENVELOPE": p.update(material="TPU_candidate",density_g_cm3=1.2,mass_provenance="AssumedTPUdensity; unselected tire")
        elif "shaft" in p["name"].lower() or "axle" in p["name"].lower() or "trunnion" in p["name"].lower() or "bolt" in p["name"].lower() or "M3" in p["name"] or "M4" in p["name"] or "washer" in p["name"] or "tie_" in p["name"]:
            p.update(material="steel_candidate",density_g_cm3=7.85,mass_provenance="Solidsteelgeometry estimate")
        elif any(code in p["name"] for code in ("608","687","627","624","626")) and p["category"]=="hardware_reference":
            p.update(material="bearing_steel_envelope_upper_bound",density_g_cm3=7.85,mass_provenance="Solidsteelannulus upperbound; actualrollingelementmass unmeasured")
        elif "factory_horn" in p["name"]:
            p.update(mass_g=0,mass_provenance="Assumedincluded in55gservo; separatehornmustbeweighed")
        for op in p["ops"]:
            if op.get("mode")=="cut" and op.get("kind")=="cylinder":
                if op["radius"]==1.7: op["radius"]=clearances["m3_clearance_diameter_mm"]/2
                elif op["radius"]==2.2: op["radius"]=clearances["m4_clearance_diameter_mm"]/2
                elif op["radius"]==3.65: op["radius"]=clearances["shaft7_clearance_diameter_mm"]/2
                elif op["radius"]==2.15: op["radius"]=clearances["shaft4_clearance_diameter_mm"]/2
        if hand<0 and p["link"]!="yaw":
            # Encode handedness in geometry; occurrence transforms remain proper rotations.
            for op in p["ops"]:
                if op["kind"]=="box": op["center"]=(op["center"][0],-op["center"][1],op["center"][2])
                elif op["kind"] in ("cylinder","annulus"):
                    for key in ("start","end"): op[key]=(op[key][0],-op[key][1],op[key][2])
                elif op["kind"]=="polygon":
                    for key in ("origin","normal","x_axis"): op[key]=(op[key][0],-op[key][1],op[key][2])
                    op["points"]=[(x,-y) for x,y in op["points"]]
    return dict(schema_version=1,units="mm",leg_name=leg_name,parts=parts,
        fit_parameters_snapshot=fit_snapshot,fit_parameters_sha256=hashlib.sha256(fit_raw).hexdigest(),
        fit_parameters_source=str(fit_source),clearance_parameters=clearances,
        coupon_transfer=dict(validated=False,
          differences=["Tower2mmshoulders vs coupon1.2mm; no matching0.6mmlead-in yet.",
                       "Distal cheek seats are throughbores, not full couponboss sections.",
                       "Seatdiameters/servopocket propagate; loadedgeometry/printorientation still differ."]),
        pose_deg=dict(yaw=yaw,hip=h,knee=k,heading=heading),
        joint_centers_world_mm=dict(yaw=mount,hip=pitchpoint,knee=kneepoint,wheel=wheelpoint),
        remote_belt_selection=belt_selection,
        bom=dict(C018=3,FIT0493=1,bearings=bearings,shafts_mm=dict(yaw=8,hip=7,remote=7,knee=8,wheel=6)),
        status="engineering_candidate_incomplete_interfaces_not_print_release",
        checks=dict(shafts_independent=True,hip_trunnion_gap_mm=10,belt_ratio=1,
          proximal_gears_teeth=[20,40],native_Fusion_executed=False,
          motion_clearance_checked=False,shaft_torque_couplings_complete=False,
          servo_horn_drawing_applied=True,servo_horn_physical_fit_checked=False,belt_profile_selected=False,
          native_motion_joints_created=False),
        joint_records=[dict(name="yaw",axis="+Z",coordinate_deg=yaw),dict(name="hip",axis="local-Y",coordinate_deg=h),dict(name="knee",axis="local-Y",coordinate_deg=k)],
        limitations=["Pose only. Full yaw region conflicts between neighboring servo cases.",
          "350deg singleturn commissioning span is a software assumption. C018 multi-loop mode needs turn-count recovery/homing.",
          "Gears have involute flanks but omit root fillets; printedgear fatigue/wear untested.",
          "Belts/pulley teeth, tensioner, shaft torque locks, servo horns, case clamps and wheelcoupling unfinished.",
          "Tower/femur interfaces and retainers require interference and assembly-order review."])

def build_leg(root, params, leg_name="FL", **pose):
    """Build one native feature component per part; positions require recipe rebuild."""
    import json
    import adsk.core
    import native_parts as n
    spec=leg_spec(params,leg_name,**pose)
    assembly=root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    assembly.component.name="MIST_leg_"+leg_name+"_candidate"
    bodies={}; components={}
    for p in spec["parts"]:
        occurrence=assembly.component.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp=occurrence.component; comp.name=p["name"]; target=None
        for index,op in enumerate(p["ops"]):
            name=p["name"]+"_"+str(index+1); kind=op["kind"]
            if kind=="box": tool=n.box(comp,name,op["center"],op["size"])
            elif kind=="cylinder": tool=n.cylinder(comp,name,op["start"],op["end"],op["radius"])
            elif kind=="annulus": tool=n.annulus(comp,name,op["start"],op["end"],op["radius"],op["inner"])
            elif kind=="polygon": tool=n.polygon(comp,name,op["points"],op["thickness"],op["origin"],op["normal"],op["x_axis"])
            else: raise ValueError(kind)
            if target is None: target=tool
            elif op["mode"]=="cut": target=n.subtract(comp,target,[tool],name+"_cut")
            else: target=n.union(comp,target,[tool],name+"_join")
        target.name=p["name"]
        transform=adsk.core.Matrix3D.create()
        for row in range(4):
            for col in range(4): transform.setCell(row,col,p["transform"][row][col]/10 if col==3 and row<3 else p["transform"][row][col])
        occurrence.transform2=transform
        comp.attributes.add("MIST","category",p["category"])
        comp.attributes.add("MIST","manufacturing_note",p["note"])
        comp.attributes.add("MIST","color_rgba",json.dumps(COLORS[p["color"]]))
        bodies[p["name"]]=target; components[p["name"]]=comp
    native_checks=dict(spec["checks"],native_Fusion_executed=True,native_motion_joints_created=False)
    return dict(occurrence=assembly,components=components,bodies=bodies,spec=spec,
                checks=native_checks,bom=spec["bom"],joint_records=spec["joint_records"])

def build_four_legs(root, params, **pose):
    return [build_leg(root,params,name,**pose) for name in params["geometry"]["leg_names"]]
