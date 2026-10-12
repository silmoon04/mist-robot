"""Interim concealed wheel-drive revision, isolated from the 657-part candidate.

The FIT0493 housing is physically moved into the upper tibia. A supported
longitudinal shaft and a 1:1 right-angle gearset replace the foot motor. Bought
bevel geometry is initially an explicit envelope pending the supplier drawing.
"""
from __future__ import annotations
import copy,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
CAD=HERE.parent
sys.path.insert(0,str(CAD/'leg_proximal_20260907'))
import proximal_leg as prior
from thermal_shell import build_shell_recipe,thermal_assumptions
COLORS=dict(prior.COLORS)
COLORS.update(white=(235,234,225,255),dark=(35,40,44,255))

def leg_spec(params,leg_name='FL',yaw_deg=None,hip_deg=None,knee_deg=None):
    p=copy.deepcopy(params)
    p['geometry']['tibia_m']=.140
    spec=prior.leg_spec(p,leg_name,yaw_deg,hip_deg,knee_deg)
    index=p['geometry']['leg_names'].index(leg_name)
    hand=[1,-1,-1,1][index]
    frames=spec['frames_world_mm'];T=140.
    parts=[]
    for source in spec['parts']:
        name=source['name']
        if name in ('W05_FIT0493_motor_CASE','W06_FIT0493_4mmD_SHAFT','W07_motor_mount_cradle','W09_6to4mm_coupling_ENVELOPE') or name.startswith('W08_motor_brace'):continue
        if name.startswith(('T04_tibia_cross_spacer','T05_tibia_tie')):continue
        if name=='T03_tibia_outer_cheek':continue
        part=copy.deepcopy(source)
        if name=='W01_wheel_626_1':
            for op in part['ops']:
                for key in ('start','end'):
                    x,y,z=op[key];op[key]=(x,y+hand*16,z)
        if name=='W02_6mm_wheel_axle':
            for op in part['ops']:
                x,y,z=op['end'];op['end']=(x,hand*54,z)
            part['note']='Extended6mm wheelshaft for internal miter output; positive torque/axial retention pending gear drawing'
        parts.append(part)
    by={p['name']:p for p in parts}
    def box(c,s,mode='add'):return dict(kind='box',center=c,size=s,mode=mode)
    def cyl(a,b,r,inner=0,mode='add'):
        return dict(kind='annulus' if inner else 'cylinder',start=a,end=b,radius=r,inner=inner,mode=mode)
    def part(name,ops,link='tibia',category='print',color='structure',material=None,density=None,note='',rigid_group=None):
        q=dict(name=name,ops=ops,link=link,category=category,color=color,transform=frames[link],
               rigid_group=rigid_group or link,note=note)
        if category=='print':q.update(material=material or 'PETG',density_g_cm3=density or 1.27)
        elif material:q.update(material=material,density_g_cm3=density)
        if hand<0:prior._mirror_ops(q['ops'])
        parts.append(q);by[name]=q;return q
    def yr(x,u,a,b,r,inner=0,mode='add'):
        return cyl((x,a,-u),(x,b,-u),r,inner,mode)
    def poly(points,y,t,mode='add'):
        return dict(kind='polygon',points=points,origin=(0,y,0),normal=(0,-1,0),x_axis=(1,0,0),thickness=t,mode=mode)
    def add_ops(target,ops):
        target['ops'].extend(prior._mirror_ops(copy.deepcopy(ops)) if hand<0 else copy.deepcopy(ops))
    positive=[yr(0,0,28.125,36.125,22,4.1)]
    for i in range(4):
        a=i*math.pi/2
        positive.append(yr(8*math.cos(a),-8*math.sin(a),28,36.3,3.3,mode='cut'))
    for s in (-1,1):
        points=[(s*x,-u) for x,u in ((15,14),(21,14),(21,90),(14.4,110),(14.4,T),(8.4,T),(8.4,110),(15,90))]
        positive.append(poly(points,43,6))
        positive.append(box((s*18,35.5625,-14),(6,14.875,8)))
    positive.extend([yr(0,T,40.8,48.2,16.5,8),yr(0,T,42,48.3,9.7,mode='cut')])
    for x in (-14,14):positive.append(yr(x,T,40.7,48.3,1.7,mode='cut'))
    frame=part('CW09_positive_tibia_frame',positive,note='Integral knee face adapter,taperedrails andpositivewheelbearingboss; oldmotor-crossingcheekremoved')
    for u in (50.,90.):
        for s in (-1,1):
            x=s*17.1
            add_ops(by['T02_tibia_main_cheek'],[box((x,-19,-u),(7.2,6,8)),yr(x,u,-23,-15,1.7,mode='cut')])
            add_ops(frame,[yr(x,u,36,44,1.7,mode='cut')])
            part(f'CW10_steel_frame_spacer_{s}_{u}',[yr(x,u,-16,37,2.5,1.6)],category='hardware_reference',color='metal',material='steel_candidate',density=7.85,note='Steelcompressiontube outsideØ25motor; M3nutdetailpendingstock')
            part(f'CW11_frame_M3_{s}_{u}',[yr(x,u,-22,43,1.5),yr(x,u,43,45.5,2.75)],category='hardware_reference',color='metal',material='steel_candidate',density=7.85)
    keeper=[yr(0,0,48.2,50.6,16.5,8),yr(0,0,48,48.2,9.5,8)]
    for x in (-14,14):keeper.append(yr(x,0,48.1,50.7,1.7,mode='cut'))
    part('CW12_wheel_bearing_keeper',keeper,link='wheel',note='Stationaryouter-racecap; occurrenceusesaxleframe',rigid_group='tibia')['link']='tibia'
    for x in (-14,14):
        q=part(f'CW13_wheel_keeper_M3_{x}',[yr(x,0,40.8,50.6,1.5),yr(x,0,50.6,53.1,2.75)],link='wheel',category='hardware_reference',color='metal',material='steel_candidate',density=7.85,rigid_group='tibia');q['link']='tibia'
    drive_y=20.
    motor=part('CW01_FIT0493_upper_tibia_CASE',[
        cyl((0,drive_y,-60),(0,drive_y,-81),12.5),
        cyl((0,drive_y,-20),(0,drive_y,-60),12.2)],category='hardware_reference',color='servo',
        note='Actual61mm gearbox-face to encoder-rear envelope; housingu20..81,insideupper tibia,not foot')
    motor.update(mass_g=98,mass_provenance='DFRobot FIT0493 nominal complete98g,including outputshaft')
    dshaft=part('CW02_motor_4mm_D_output',[
        cyl((0,drive_y,-81),(0,drive_y,-93),2),
        box((0,drive_y+2.25,-89),(6,1.5,8),'cut')],category='hardware_reference',color='metal',
        note='4mmD shaft12mm long,3.5mm acrossflat over8mm; rotation axis longitudinal',rigid_group='wheel_drive_rotor')
    dshaft.update(mass_g=0,mass_provenance='Included in complete98g motor')
    part('CW03_4D_to_6mm_coupling_ENVELOPE',[
        cyl((0,drive_y,-85),(0,drive_y,-105),6,2),
        cyl((0,drive_y,-95),(0,drive_y,-106),3.1,mode='cut')],category='hardware_reference',color='metal',
        material='aluminium_candidate',density=2.7,rigid_group='wheel_drive_rotor',
        note='Ø12x20 coupling envelope; stock clamp selection and D interface pending,not a friction-only claim')
    part('CW04_supported_6mm_longitudinal_shaft',[
        cyl((0,drive_y,-95),(0,drive_y,-135),3)],category='hardware_reference',color='metal',
        material='steel_candidate',density=7.85,rigid_group='wheel_drive_rotor',
        note='Separate steel shaft; motor4mm output is not the wheel-load bearing')
    carriers=[]
    for i,(u0,u1) in enumerate(INPUT_626_FACES_U_MM):
        part(f'CW05_shaft_626_bearing_{i}',[
            cyl((0,drive_y,-u0),(0,drive_y,-u1),9.5,3)],category='hardware_reference',color='metal',
            material='bearing_steel_envelope_upper_bound',density=7.85,
            note='6266x19x6 envelope,independent drive-shaft support; axial retention still to integrate')
        if i==0:
            # Upper cup opens toward the knee. Its outer race can be inserted
            # without passing through the lower cup's smaller shoulder hole.
            a,b=u0-.2,u1+1.2
            cut_a,cut_b=u0-.3,u1
        else:
            a,b=u0-1.2,u1+.2
            cut_a,cut_b=u0,u1+.3
        q=part(f'CW06_shaft_bearing_carrier_{i}',[
            cyl((0,drive_y,-a),(0,drive_y,-b),13.5,8),
            box((0,33,-(a+b)/2),(20,11,b-a)),
            cyl((0,drive_y,-cut_a),(0,drive_y,-cut_b),9.7,mode='cut')],
            note=('OD27/seat19.4x6.2, opposed insertion directions. Central shoulders overlap only inside the same printed frame; effective central web is2mm. Axial retention still incomplete.'))
        carriers.append(q)
    reference=dict(kind='step_reference',mode='add',path=str(OEM_MITER_STEP_PATH.resolve()),sha256=OEM_MITER_STEP_SHA256)
    def gear_world_transform(rotation):
        base=frames['tibia']
        origin=prior.legacy._point(base,(0,hand*drive_y,-T))
        return [[sum(base[i][k]*rotation[k][j] for k in range(3)) for j in range(3)]+[origin[i]] for i in range(3)]+[[0,0,0,1]]
    driver=part('CW07_miter_driver_OEM',[copy.deepcopy(reference)],category='hardware_reference',color='gear',
        rigid_group='wheel_drive_rotor',note='Actual KHK SM1-20 teeth CAD; selected SM1-20H has same nominal geometry. Native validated phase input0/output9. Torque and axial locks remain incomplete.')
    driver['transform']=gear_world_transform([[hand,0,0],[0,0,hand],[0,-1,0]])
    output=part('CW08_miter_output_OEM',[copy.deepcopy(reference)],link='wheel',category='hardware_reference',color='gear',
        note='Actual KHK geometry. Output back faceY40 requires outer626Y42..48. H-grade material/rating is distinct from this plain-SM source model.')
    t=math.radians(OEM_MITER_OUTPUT_PHASE_DEG);c,s=math.cos(t),math.sin(t)
    output['transform']=gear_world_transform([[c,0,s],[0,-hand,0],[hand*s,0,-hand*c]])
    for gear in (driver,output):
        gear.update(mass_g=19,mass_provenance='KHK nominal19g for SM1-20 geometry; actual H-grade purchase unweighed',
                    reference_shape=dict(source_variant='SM1-20',selected_material_variant='SM1-20H',native_axis='-Y',native_apex_mm=[0,0,0],source_sha256=OEM_MITER_STEP_SHA256))
    # One printed positive frame carries both shaft bearing bosses. These
    # intended load-path intersections belong within the same manufactured part.
    for q in carriers:
        frame['ops'].extend(q['ops']);parts.remove(q)
    for q in build_shell_recipe():
        q=copy.deepcopy(q);q['transform']=frames['tibia']
        if q['name']=='TH03_white_faceted_cover_rear':
            for op in q['ops']:
                if op.get('kind')=='cylinder' and op.get('mode')=='cut' and op.get('radius')==17.1:
                    x,y,z=op['end'];op['end']=(x,53.4,z)
        if hand<0:prior._mirror_ops(q['ops'])
        parts.append(q);by[q['name']]=q
    spec.update(parts=parts,status='concealed_wheel_interim_geometry_not_print_release',
        wheel_drive=dict(topology='longitudinal_upper_tibia_shaft_miter_1to1',tibia_mm=T,
                         motor_case_u_mm=[20,81],motor_com_tibia_mm=[0,hand*20,-50.5],
                         motor_output_u_mm=[81,93],coupling_u_mm=[85,105],shaft_u_mm=[95,135],
                         drive_axis_tibia=[0,0,-1],drive_axis_y_mm=hand*20,wheel_axis='localY',
                         declared_ratio=1,mesh_geometry='OEM_STEP_SM1_20_geometry_for_conditional_SM1_20H',
                         input_phase_deg=0,output_phase_deg=9,phase_relation='output_phase=9-input_phase',
                         outer_wheel_bearing_y_mm=[hand*42,hand*48],input_bearing_u_mm=INPUT_626_FACES_U_MM,
                         geometry_validation='Native Fusion phased pair cleared7coupledposes; OpenCascade warning-bearing zero results are not clearance proof'),
        removed_foot_drive_parts=['W05','W06','W07','W08','W09'],
        thermal_design=thermal_assumptions(),
        limitations=spec['limitations']+['Final shaft torque/axial retention remains incomplete; OEM teeth are now real STEP references.',
                                       'Tibia grows130to140mm to fitcoupling plus independentbearings; oldsnapshots unchanged.',
                                       'Oldmotor-crossingcross-tiesremoved; replacementframe requiresstrength/creepvalidation.',
                                       'Ventedandconductivelyclampedbaydoesnotestablishcontinuous1Arating.'])
    return spec

# Persistent checkpoint: OEM STEP verified as one solid, native axis -Y,
# apex at origin. Native Fusion validates output phase9-input phase; zero-volume
# OpenCascade results accompanied by warnings are not clearance evidence.
OEM_MITER_STEP_PATH = CAD.parents[0] / 'references' / 'KHK_SM1_20' / 'SM1-20_On.stp'
OEM_MITER_STEP_SHA256 = 'c4aebaa418f6955130f9bf4f4a798dc478b181fea47327865db2d7aedb386a98'
OEM_MITER_OUTPUT_PHASE_DEG = 9.0
OUTER_WHEEL_626_FACES_Y_MM = (42.0, 48.0)
INPUT_626_FACES_U_MM = ((105.5, 111.5), (113.5, 119.5))
INPUT_CUP_ASSEMBLY = 'upper cup opens toward knee; lower cup opens toward foot'
CHECKPOINT_STATUS = 'OEM integration and cup coordinates being applied; mounts, casing and retention incomplete'
