"""Bounded proximal-femur knee-drive candidate, separate from the checked leg.

The new knee motor, reduction and adjustable bearing cartridge move with the
femur. The 25:50 metal gears are manufacturing candidates, not rated purchases.
Geometry and interfaces remain subject to the emitted collision/fit report.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

CAD=Path(__file__).resolve().parents[1]
if str(CAD) not in sys.path: sys.path.insert(0,str(CAD))
import leg_native as legacy
from leg_gears import involute_spur_points
from retention_recipe import build_retention_recipe

COLORS=legacy.COLORS

def _mirror_ops(ops):
    for op in ops:
        if op['kind']=='box':
            x,y,z=op['center'];op['center']=(x,-y,z)
        elif op['kind'] in ('cylinder','annulus'):
            for key in ('start','end'):
                x,y,z=op[key];op[key]=(x,-y,z)
        elif op['kind']=='polygon':
            for key in ('origin','normal','x_axis'):
                x,y,z=op[key];op[key]=(x,-y,z)
            op['points']=[(x,-y) for x,y in op['points']]
    return ops

def leg_spec(params,leg_name='FL',yaw_deg=None,hip_deg=None,knee_deg=None,carriage_u_mm=0.):
    """Return an explicit mechanical candidate with the relative-knee contract."""
    if abs(carriage_u_mm)>1e-9:
        raise ValueError('First solid build is nominal carriage u=0; installation travel remains a separate check')
    old=legacy.leg_spec(params,leg_name,yaw_deg,hip_deg,knee_deg)
    index=params['geometry']['leg_names'].index(leg_name)
    hand=[1,-1,-1,1][index]
    h,k,heading=[old['pose_deg'][x] for x in ('hip','knee','heading')]
    centers=old['joint_centers_world_mm']; L=params['geometry']['femur_m']*1000
    fm=legacy._mat(heading,h,centers['hip'])
    tm=legacy._mat(heading,h+k,centers['knee'])
    rotor=legacy._mat(heading,h+k,centers['hip'])
    frames=dict(body=legacy._mat(),yaw=legacy._mat(heading,at=centers['yaw']),
                femur=fm,tibia=tm,wheel=legacy._mat(heading,h+k,centers['wheel']))
    parts=[]
    for source in old['parts']:
        n=source['name']
        if n.startswith('K') or n=='S02_C018_K_CASE' or n=='P01_rotating_coxa_bridge': continue
        if n.startswith(('F04_matched_metal_pulley','T06_knee_inner_race_spacer')): continue
        if n.startswith(('F02_femur_cross_spacer','F03_femur_tie')) and n.endswith('_-48'):continue
        p=copy.deepcopy(source)
        if n=='Y06_yaw_output_40T':p['link']='yaw';p['rigid_group']='yaw'
        if n=='H06_output_40T':p['link']='femur';p['rigid_group']='femur'
        if n.startswith('W') and n not in ('W02_6mm_wheel_axle','W03_wheel_hub','W04_tire_ENVELOPE','W06_FIT0493_4mmD_SHAFT','W09_6to4mm_coupling_ENVELOPE'):
            p['link']='tibia';p['rigid_group']='tibia'
        if n in ('W06_FIT0493_4mmD_SHAFT','W09_6to4mm_coupling_ENVELOPE'):
            p['link']='wheel';p['rigid_group']='wheel'
        if n.startswith(('F02_femur_cross_spacer','F03_femur_tie')) or n in ('F01_femur_cheek_belt','F06_knee_608_1','F07_knee_bearing_keeper_1') or n.startswith('F08_knee_keeper_M3_1'):
            if hand<0:_mirror_ops(p['ops'])
            for op in p['ops']:
                if op['kind'] in ('cylinder','annulus'):
                    for key in ('start','end'):
                        x,y,z=op[key]
                        if y>=37:op[key]=(x,y+3.125,z)
                elif op['kind']=='polygon':
                    x,y,z=op['origin'];op['origin']=(x,y+3.125,z)
                elif op['kind']=='box':
                    x,y,z=op['center'];op['center']=(x,y+3.125,z)
            if hand<0:_mirror_ops(p['ops'])
        parts.append(p)
    by={p['name']:p for p in parts}
    def part(name,ops,link='femur',category='print',color='structure',note='',rigid_group=None,material=None,density=None):
        p=dict(name=name,ops=ops,link=link,category=category,color=color,note=note,
               transform=frames.get(link,fm),rigid_group=rigid_group or link)
        if material:p.update(material=material,density_g_cm3=density)
        elif category=='print':p.update(material='PETG',density_g_cm3=1.27)
        if hand<0:_mirror_ops(p['ops'])
        parts.append(p);by[name]=p;return p
    def box(c,s,mode='add'):return dict(kind='box',center=c,size=s,mode=mode)
    def yr(x,z,a,b,r,inner=0,mode='add'):
        return dict(kind='annulus' if inner else 'cylinder',start=(x,a,z),end=(x,b,z),radius=r,inner=inner,mode=mode)
    def profile(points,y,t,mode='add'):
        return dict(kind='polygon',points=points,origin=(0,y,0),normal=(0,-1,0),x_axis=(1,0,0),thickness=t,mode=mode)
    def add_ops(p,ops):
        p['ops'].extend(_mirror_ops(copy.deepcopy(ops)) if hand<0 else copy.deepcopy(ops))

    # Retain the hip-side yaw carriage, deleting the remote-drive side flange.
    dx=params['geometry']['hip_radial_offset_m']*1000
    dy=params['geometry']['hip_transverse_offset_m']*1000*hand
    length=math.hypot(dx,dy);nx,ny=-dy/length*7,dx/length*7
    co=[dict(kind='annulus',start=(0,0,22),end=(0,0,28),radius=10,inner=4.2,mode='add'),
        dict(kind='polygon',points=[(nx,ny),(dx+nx,dy+ny),(dx-nx,dy-ny),(-nx,-ny)],origin=(0,0,22),normal=(0,0,1),x_axis=(1,0,0),thickness=6,mode='add'),
        box((dx,dy-hand*24,25),(22,72,6)),box((dx+6.75,dy-hand*60,25),(13.5,8,6)),
        box((dx+6.75,dy-hand*61.75,-6),(13.5,6.5,56)),
        dict(kind='cylinder',start=(0,0,21),end=(0,0,29),radius=4.2,mode='cut'),
        dict(kind='cylinder',start=(dx,dy-hand*66,0),end=(dx,dy-hand*57.5,0),radius=3.7,mode='cut')]
    for zz in (-31,-24):co.append(dict(kind='cylinder',start=(dx-1,dy-hand*62,zz),end=(dx+15,dy-hand*62,zz),radius=1.7,mode='cut'))
    for y in (-43.5,-25.5):co.append(dict(kind='cylinder',start=(dx,dy+hand*y,21),end=(dx,dy+hand*y,29),radius=1.7,mode='cut'))
    p=dict(name='PF01_hip_only_coxa',ops=co,link='yaw',rigid_group='yaw',category='print',color='structure',material='PETG',density_g_cm3=1.27,transform=frames['yaw'],note='Remote knee support flange removed; hip-side connection retained')
    parts.append(p);by[p['name']]=p

    retention=build_retention_recipe(mount_y_mm=-7,input_right_bearing_start_y_mm=42.325,knee_right_bearing_start_y_mm=42.325)
    # Fixed rails become part of the existing negative femur cheek.
    rail_ops=[]
    for x in (-18,18):rail_ops.append(box((x,-10,-56),(8,6,80)))
    for z in (-22,-56):rail_ops.append(box((0,-10,z),(44,6,8)))
    add_ops(by['F01_femur_cheek_drive'],rail_ops)
    # Nominal sliding plate. Circular proximal outline prevents upstream corner interference.
    plate=[yr(0,0,-7,-3,17),box((0,-5,-43),(50,4,54)),
           yr(0,0,-8,-2,3.8,mode='cut')]
    cp=part('PF02_sliding_carriage',plate,note='4mm nominal plate on fixed femur rails; tension setting and locked slip strength unmeasured')
    # Independent pair of supported input bearings, both carried by this moving plate.
    for i,y0 in enumerate((5.,52.325)):
        floor=y0-1.2; end=y0+7.2
        ops=[yr(0,0,floor,end,17,10),yr(0,0,y0,end+.1,11.2,mode='cut')]
        for x in (-14,14):ops.append(yr(x,0,floor-.1,end+.1,1.7,mode='cut'))
        if i==0:
            # Reverse the left cup so the contract keeper is clear of the pulley.
            ops=[yr(0,0,4.8,13.2,17,10),yr(0,0,4.7,12,11.2,mode='cut')]
            for x in (-14,14):ops.append(yr(x,0,4.7,13.3,1.7,mode='cut'))
            ops.insert(0,box((0,.9,-22),(20,7.8,8)))
            ops.insert(0,box((0,9,-18),(20,8.4,8)))
        else:
            for x in (-30,30):ops.insert(0,box((x,(floor-3)/2,-29),(6,floor+3,58)))
            ops.insert(0,box((0,(floor-3)/2,-60),(66,floor+3,6)))
            ops.insert(0,box((0,floor+2,-14),(60,6,6)))
        hp=part(f'PF03_input_bearing_carrier_{i}',ops,note='Shared fit contract OD34,seat22.4x7.2,floor1.2,through20,no lead-in; support bridges remain candidate')
        part(f'PF04_627_{i}',[yr(0,0,y0,y0+7,11,3.5)],category='hardware_reference',color='metal',material='bearing_steel_envelope_upper_bound',density=7.85,note='627 nominal7x22x7; mass is solid-steel annulus upper bound')
        ka,kb=(2.4,4.8) if i==0 else (end,end+2.4)
        keeper=[yr(0,0,ka,kb,17,10)]
        for x in (-14,14):keeper.append(yr(x,0,ka-.1,kb+.1,1.7,mode='cut'))
        part(f'PF05_input_keeper_{i}',keeper,note='Shared OD34/ID20/t2.4,M3holesatx+/-14; axial clash checked explicitly')
    shaft=part('PF06_input_shaft',[yr(0,0,3,61.325,3.5)],category='hardware_reference',color='metal',material='steel_candidate',density=7.85,note='7mm radial-load shaft; M3 major-bore envelope,2.5mm tap-drill operation; torque bypasses shaft')
    # A-shape matched GT pulley envelope and face-bolted metal output gear.
    for label,link,z,bore in (('input','femur',0,7),('knee','tibia',0,8)):
        ops=[yr(0,z,14.125,28.125,12.5,bore/2+.1),
             yr(0,z,15.975,26.275,14.9,bore/2+.1),
             yr(0,z,14.975,15.975,17,bore/2+.1),yr(0,z,26.275,27.275,17,bore/2+.1)]
        for a in range(4):
            angle=a*math.pi/2;ops.append(yr(8*math.cos(angle),8*math.sin(angle),20.025,28.225,2,mode='cut'))
        p=part('PF07_'+label+'_A_pulley',ops,link=link,category='hardware_reference',color='gear',material='aluminium_candidate',density=2.7,note='Conditional MISUMI A32GT3090 QFC16-M4 factory machining; exact teeth omitted',rigid_group='knee_input_rotor' if label=='input' else 'tibia')
        if label=='input':p['transform']=rotor
    gear_ops=[profile(involute_spur_points(50,samples=3),46.125,8),yr(0,0,38,46.3,3.65,mode='cut')]
    for a in range(4):
        angle=a*math.pi/2;gear_ops.append(yr(8*math.cos(angle),8*math.sin(angle),38,46.3,2.25,mode='cut'))
    gp=part('PF08_metal_50T_output',gear_ops,category='hardware_reference',color='gear',material='aluminium_candidate',density=2.7,rigid_group='knee_input_rotor',note='Custom7mm bore metal50T gear; material/heat treatment/rating and factory acceptance pending')
    gp['transform']=rotor
    phase=3.6-2*k
    pin=[profile([(x,z-37.5) for x,z in involute_spur_points(25,phase_deg=phase,samples=3)],46.125,8),yr(0,-37.5,38,46.3,4,mode='cut')]
    for a in range(4):
        angle=math.radians(phase)+a*math.pi/2;pin.append(yr(7*math.cos(angle),-37.5+7*math.sin(angle),38,46.3,1.7,mode='cut'))
    part('PF09_metal_25T_pinion',pin,category='hardware_reference',color='gear',material='steel_candidate',density=7.85,rigid_group='knee_motor_rotor',note='25T improves horn-hole web; machined metal and M3 factory thread engagement require verification')
    case=part('PF10_C018_knee_CASE',[box((0,69.125,-47.615),(24.73,35,45.23))],category='hardware_reference',color='servo',note='Housing physically fixed to femur cartridge; COM47.615mm down femur')
    case.update(mass_g=55,mass_provenance='C018 manufacturer nominal complete actuator mass')
    horn=[yr(0,-37.5,46.125,48.625,9.975,1.6),yr(0,-37.5,48.625,50.625,4.5,2.95)]
    for a in range(4):
        angle=math.radians(phase)+a*math.pi/2;horn.append(yr(7*math.cos(angle),-37.5+7*math.sin(angle),46,48.7,1.5,mode='cut'))
    hp=part('PF11_factory_horn',horn,category='hardware_reference',color='metal',note='2.5mm flange plus2mm raised spline boss toward case; gear contacts flat face',rigid_group='knee_motor_rotor')
    hp.update(mass_g=0,mass_provenance='Assumed included in55g servo; weigh supplied horn separately')
    # Open longitudinal clamp rails and two hard-stop crossbars carry case reactions.
    mount=[]
    for x in (-15.365,15.365):mount.append(box((x,69.125,-47.615),(6,41,51.23)))
    mount.append(box((0,89.625,-47.615),(36.73,6,51.23)))
    mount.append(box((0,69.125,-74.23),(36.73,41,3)))
    part('PF12_motor_cradle',mount,note='Open front for horn access; cradle-to-right carrier fastening is a first-build interface')
    # Attach new purchased hardware/retention recipes and apply their explicit cuts.
    targets={'carriage_plate':cp,'fixed_rails':by['F01_femur_cheek_drive'],
             'input_shaft':shaft,'knee_shaft':by['T01_knee_metal_shaft'],
             'tibia_main_cheek':by['T02_tibia_main_cheek']}
    for r in retention['parts']:
        if r['name'].startswith('RT_input_face_sleeve'):continue
        p=copy.deepcopy(r);p['transform']=rotor if p.get('rigid_group')=='knee_input_rotor' else frames[p['link']]
        if hand<0:_mirror_ops(p['ops'])
        parts.append(p);by[p['name']]=p
    # Move the metal input gear10mm outboard on four steel standoffs. The belt
    # remains at its original datum. This corrects measured yaw-case collisions.
    for p in parts:
        n=p['name']
        if not n.startswith('RT_input_'):continue
        ops=p['ops']
        if hand<0:_mirror_ops(ops)
        if 'M4x14_face' in n:
            # M4x25: eight gear + ten spacer + seven thread engagement.
            for op in ops:
                if op['kind'] in ('cylinder','annulus'):
                    x,a,z=op['start'];_,b,_=op['end']
                    if op['radius']==2:op['start']=(x,21.125,z);op['end']=(x,46.125,z)
                    else:op['start']=(x,a+10,z);op['end']=(x,b+10,z)
            p['note']='M4x25 through8mm metal gear and10mm steel standoff;7mm nominal engagement in8mm factorytap'
        elif n.endswith('inner_spacer_2') or n.endswith('inner_spacer_3') or n.endswith('washer_high') or n.endswith('end_high'):
            for op in ops:
                if op['kind'] in ('cylinder','annulus'):
                    for key in ('start','end'):
                        x,y,z=op[key];op[key]=(x,y+10,z)
        if hand<0:_mirror_ops(ops)
    for i in range(4):
        a=i*math.pi/2
        pp=part(f'PF13_input_face_standoff_{i}',[yr(8*math.cos(a),8*math.sin(a),28.125,38.125,3.25,2.15)],category='hardware_reference',color='metal',material='steel_candidate',density=7.85,rigid_group='knee_input_rotor',note='10mm steel compression standoff; register and reversed-load stiffness require measurement')
        pp['transform']=rotor
    pp=part('PF14_input_central_spacer',[yr(0,0,28.125,38.125,4.5,3.6)],category='hardware_reference',color='metal',material='steel_candidate',density=7.85,rigid_group='knee_input_rotor');pp['transform']=rotor
    targets['tibia_hub']=by['RT_knee_face_bolted_adapter']
    for cut in retention['cuts']:
        if cut['target']=='input_gear':continue
        if cut['target'] in targets:add_ops(targets[cut['target']],cut['ops'])
    # Full major-thread voids are used for coarse assembly contact; drilling
    # remains2.5mm for M3. This avoids counting unmodeled thread engagement as
    # solid interference.
    for target in (shaft,by['T01_knee_metal_shaft']):
        for op in target['ops']:
            if op.get('mode')=='cut' and op.get('radius')==1.25:
                op['radius']=1.5
                if target is shaft:
                    for key in ('start','end'):
                        x,y,z=op[key]
                        if abs(y)>30:op[key]=(x,y+hand*10,z)
    # Merge intended one-piece printed load paths; no unrelated hardware is fused.
    def merge_into(target_name,source_names):
        target=by[target_name]
        for name in source_names:
            target['ops'].extend(by[name]['ops']);parts.remove(by[name])
    merge_into('PF02_sliding_carriage',['PF03_input_bearing_carrier_0','PF03_input_bearing_carrier_1','PF12_motor_cradle'])
    for xx in (-18,18):
        add_ops(cp,[box((xx,0,-56),(12.4,6,14.4),'cut')])
    for xx in (-15.279,15.279):add_ops(cp,[box((xx,21.125,-60),(5,12,8),'cut')])
    merge_into('T03_tibia_outer_cheek',['RT_knee_face_bolted_adapter'])
    for n in ('T05_tibia_tie_-9_-48','T05_tibia_tie_9_-48'):
        for op in by[n]['ops']:
            for key in ('start','end'):
                x,y,z=op[key]
                if abs(y)>=32:op[key]=(x,y+hand*4.125,z)
    # Clear the long motor/cradle from the former positive cheek. A retained
    # distal cheek and existing u85 cross ties remain; proximal positive support
    # is through the new cartridge, explicitly cantilevered from the fixed rail.
    add_ops(by['F01_femur_cheek_belt'],[box((0,44.125,-47.5),(50,12,65),'cut')])
    merge_into('F01_femur_cheek_drive',['RT_fixed_jack_bridge'])
    jackcuts=[box((0,-5,-84),(5.8,24,16),'cut'),
              box((0,-15.5,-91),(18.2,4,2.1),'cut'),
              dict(kind='cylinder',start=(0,-5,-69),end=(0,-5,-106),radius=2.2,mode='cut'),
              box((0,-5,-70.75),(12,12,1.5),'cut')]
    add_ops(by['F01_femur_cheek_drive'],jackcuts)
    # The original bridge recipe already cut its hex and load-plate pockets;
    # the relief above clears only material introduced by the merged rail.
    add_ops(by['F01_femur_cheek_drive'],[box((0,-5,-98),(9,9,4),'cut')])
    add_ops(by['F01_femur_cheek_drive'],[dict(kind='cylinder',start=(0,-5,-100),end=(0,-5,-110),radius=3.8,mode='cut')])
    for x in (-9,9):
        n=f'F02_femur_cross_spacer_{x}_-85'
        for op in by[n]['ops']:
            a,b=op['start'],op['end'];op['start']=(a[0],hand*6,a[2])
        add_ops(by['F01_femur_cheek_drive'],[yr(x,-85,-17,7,1.7,mode='cut')])
    for p in parts:
        p.setdefault('rigid_group','yaw' if p['link']=='pod' else p['link'])
        if p['name'] in ('Y07_yaw_input_20T','Y08_factory_horn'):p['rigid_group']='yaw_motor_rotor'
        if p['name'] in ('H07_input_20T','H09_factory_horn'):p['rigid_group']='hip_motor_rotor'
        if p['name']=='PF06_input_shaft':p['rigid_group']='knee_input_rotor'
    contract_path=CAD.parents[0]/'coupons'/'bed1_proximal_20260907'/'interface_contract.json'
    contract_raw=contract_path.read_bytes()
    retention['metadata'].update(input_bearing_centres_y_mm=[8.5,55.825],
        input_gear_y_mm=[38.125,46.125],knee_adapter_y_mm=[28.125,36.125],
        input_steel_bridge_length_mm=10,input_face_bolt_length_mm=25,input_face_bolt_engagement_mm=7,
        input_shaft=dict(diameter_mm=7,y_mm=[3,61.325],end_tap='M3',pilot_mm=2.5,rendered_major_bore_mm=3),
        current_scope='Nominal locked position only; geometric travel and load rating not validated')
    return dict(schema_version=1,status='first_proximal_solid_candidate_unvalidated_interfaces',leg_name=leg_name,
                parts=parts,pose_deg=old['pose_deg'],joint_centers_world_mm=centers,frames_world_mm=frames,
                fit_contract=json.loads(contract_raw),fit_contract_sha256=hashlib.sha256(contract_raw).hexdigest(),
                topology='proximal_femur_relative_knee',motor_coordinate_equation='s=[2*yaw,2*hip,2*knee]',
                knee_servo_com_femur_mm=[0,hand*69.125,-47.615],retention=retention['metadata'],
                removed_legacy_parts=[p['name'] for p in old['parts'] if p['name'] not in by],
                limitations=['Old yaw/hip20T printed pinion root web remains a load-release gate.',
                             'New25:50 metal gears and QFC pulley machining are conditional, not purchased or load-rated here.',
                             'The new cartridge and case mount are heavy, unoptimized printed load paths; no stiffness or print release.',
                             'Keeper screws, slider lower nuts/washers, jack side cover, motor clamp preload and horn mounting screws remain incomplete hardware details.',
                             'Printed knee carrier central-to-sleeve ligament is0.6mm; narrow knee spacer wall is0.2mm. Both require redesign or qualification.',
                             'Nominal cartridge only; installation travel and full moving clearance need separate checks.'])

def build_four_legs(root,params,**pose):
    raise NotImplementedError('Native component replay will use this same recipe after the first offline solid check')
