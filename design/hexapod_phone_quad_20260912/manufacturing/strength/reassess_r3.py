"""R3 mesh-derived section comparison. No material failure simulation is claimed."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import numpy as np
import trimesh
from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
MESH=ROOT/'cad/output/parts_mesh'
CACHE={}


def section(name, axis, position, region=None):
    if name not in CACHE:
        CACHE[name]=trimesh.load_mesh(MESH/(name+'.stl'))
    normal=np.eye(3)[axis]
    sec=CACHE[name].section(plane_normal=normal,plane_origin=normal*position)
    axes=[i for i in range(3) if i != axis]
    polygons=[Polygon(p[:,axes]) for p in sec.discrete]
    shape=polygons[0]
    for poly in polygons[1:]:
        shape=shape.symmetric_difference(poly)
    if region is not None:
        shape=shape.intersection(box(*region))
    components=[shape] if shape.geom_type=='Polygon' else list(shape.geoms)
    A=Qx=Qy=Ixx=Iyy=Ixy=0.
    vertices=[]
    for poly in components:
        poly=orient(poly,sign=1.)
        for ring in [poly.exterior,*poly.interiors]:
            xy=np.asarray(ring.coords)
            vertices.extend(xy.tolist())
            x,y=xy[:-1].T
            u,v=xy[1:].T
            c=x*v-u*y
            A+=c.sum()/2
            Qx+=((x+u)*c).sum()/6
            Qy+=((y+v)*c).sum()/6
            Ixx+=((y*y+y*v+v*v)*c).sum()/12
            Iyy+=((x*x+x*u+u*u)*c).sum()/12
            Ixy+=((2*x*y+x*v+u*y+2*u*v)*c).sum()/24
    cx,cy=Qx/A,Qy/A
    Ixx-=A*cy*cy
    Iyy-=A*cx*cx
    Ixy-=A*cx*cy
    vertices=np.asarray(vertices)
    centered=vertices-[cx,cy]
    inertia=np.array([[Iyy,Ixy],[Ixy,Ixx]])
    Z=[1/np.max(np.abs(centered@np.linalg.solve(inertia,vec))) for vec in ([0.,1.],[1.,0.])]
    return dict(part=name,cut_axis='xyz'[axis],cut_mm=float(position),region=region,
                transverse_axes=['xyz'[i] for i in axes],area_mm2=A,
                centroid_transverse_mm=[cx,cy],I_transverse_mm4=[Ixx,Iyy,Ixy],
                section_modulus_transverse_mm3=Z,
                transverse_bounds_mm=[vertices.min(axis=0).tolist(),vertices.max(axis=0).tolist()])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sliced-total-mass-kg',type=float)
    parser.add_argument('--slice-mass-source',type=Path)
    parser.add_argument('--as-printed-manifest',type=Path)
    parser.add_argument('--walking-trajectory',type=Path)
    args=parser.parse_args()
    manifest=ROOT/'cad/output/assembly_manifest.json'
    m=json.loads(manifest.read_text())
    baseline=json.loads((OUT/'baseline_r2/strength_results.json').read_text())
    mass=m['total_mass_kg']
    sliced_evidence=None
    if args.slice_mass_source:
        sliced=json.loads(args.slice_mass_source.read_text())
        assert sliced['status']=='pass'
        assert sliced['source_manifest_hash']==hashlib.sha256(manifest.read_bytes()).hexdigest()
        expected={p['sku'] for p in m['print_parts']}
        assert {p['sku'] for p in sliced['parts']}==expected
        deposited=sliced['quantity_weighted_totals']['model_mass_g']/1000
        calculated=mass-m['printable_mass_solid_kg']+deposited
        if args.sliced_total_mass_kg is not None:
            assert abs(args.sliced_total_mass_kg-calculated)<1e-6
        args.sliced_total_mass_kg=calculated
        sliced_evidence=dict(production_sku_count=len(sliced['parts']),
                             production_piece_count=sliced['quantity_weighted_totals']['piece_count'],
                             deposited_model_mass_kg=deposited,
                             retained_nonprinted_mass_kg=mass-m['printable_mass_solid_kg'],
                             support_mass_excluded_kg=sliced['quantity_weighted_totals']['support_mass_g']/1000,
                             calculation='Manifest total minus manifest printable solid mass plus deposited model mass. Support and adhesion are excluded.')
    if args.as_printed_manifest:
        printed=json.loads(args.as_printed_manifest.read_text())
        assert printed['mass_model']['source_solid_manifest_sha256']==hashlib.sha256(manifest.read_bytes()).hexdigest()
        assert args.slice_mass_source is not None
        assert printed['mass_model']['source_production_properties_sha256']==hashlib.sha256(args.slice_mass_source.read_bytes()).hexdigest()
        assert abs(printed['total_mass_kg']-args.sliced_total_mass_kg)<1e-6
        args.sliced_total_mass_kg=printed['total_mass_kg']
    rows=[]
    sections={}
    for label,name,axis,pos,region in [
        ('femur','FL_femur_main_and_knee_saddle',0,40,None),
        ('tibia','FL_tibia_curved_main_and_foot',0,30,None),
        ('foot','FL_tibia_curved_main_and_foot',0,80,None),
        ('yaw_lower','FL_coxa_lower_auxiliary_arm',0,20,None),
        ('femur_bridge','FL_femur_main_and_knee_saddle',1,0,[62.99,-23.01,77.01,-8.99]),
        ('tibia_bridge','FL_tibia_curved_main_and_foot',1,8,[43.99,12.99,60.01,26.01]),
        ('phone_spine_centre','phone_cradle_rear_frame',2,53.25,[-20,74.25,20,82.25]),
        ('phone_top_bridge','phone_cradle_top_cap',1,0,None),
        ('phone_lower_clip_bolt','phone_cradle_lower_clip_right',1,78.25,None),
        ('femur_cheek_bolt','FL_femur_main_and_knee_saddle',0,70,[19,-23,23,-9]),
    ]:
        sections[label]=section(name,axis,pos,region)
    def add(label,demand,allowable,case,detail):
        rows.append(dict(check=label,demand_MPa=demand,allowable_MPa=allowable,
                         conditional_margin=allowable/demand,case=case,detail=detail))
    def stress(label,nominal,allowable,case,detail):
        add(label,nominal*4,allowable,case,detail)
    for label in ('femur','tibia'):
        zy,zz=sections[label]['section_modulus_transverse_mm3']
        stress(label+' sagittal',529.1991449773549/zy,12,'R2 sampled torque',
               'Global sampled peak applied to main cheek; no side load.')
        stress(label+' combined',588/zy+500/zz,12,'frozen moments',
               'Entire 588 Nmm sagittal and 500 Nmm lateral moment assigned to one cheek; auxiliary stiffness not credited.')
        sections[label]['conditional_side_force_at_100mm_N']=max(0,(12/4-588/zy)*zz/100)
    cheek_scans={}
    worst_cheeks={}
    for label,name,end in [('femur','FL_femur_main_and_knee_saddle',62),
                           ('tibia','FL_tibia_curved_main_and_foot',44)]:
        scan=[]
        for x in np.arange(11.,end,.5):
            s=section(name,0,float(x),[14.99,-100,23.01,100])
            zy,zz=s['section_modulus_transverse_mm3']
            s['screening_demand_MPa']=4*(588/zy+500/zz)
            s['conditional_side_moment_Nmm']=max(0,(3-588/zy)*zz)
            scan.append(s)
        cheek_scans[label]=scan
        worst_cheeks[label]=max(scan,key=lambda s:s['screening_demand_MPa'])
        add(label+' longitudinal main-cheek scan',worst_cheeks[label]['screening_demand_MPa'],12,
            'frozen constant moment upper bound',
            'Full root moments at every cut outside metal horn radius. Conservative screening envelope, not a reconstructed section load diagram; rib terminations are included.')
    # Scan every window and shoulder at 0.25 mm intervals. Holes are included.
    post_scan=[]
    for z in np.arange(-43.75,-24.99,.25):
        s=section('FL_coxa_upper_and_hip_saddle',2,float(z))
        post_scan.append(s)
    phone_scan=[]
    for z in np.arange(42.3,64.21,.1):
        s=section('phone_cradle_rear_frame',2,float(z),[-20,74.25,20,82.25])
        demand=4*2.5*(97-z)/s['section_modulus_transverse_mm3'][1]
        s['screening_demand_MPa']=demand
        phone_scan.append(s)
    worst_phone=max(phone_scan,key=lambda x:x['screening_demand_MPa'])
    add('Phone USB spine scan',worst_phone['screening_demand_MPa'],12,'5 N phone push',
        'Full horizontal push shared equally between two columns at z97. Scan through opening includes rounded transitions; notches remain assumed.')
    ztop=sections['phone_top_bridge']['section_modulus_transverse_mm3']
    stress('Phone rear top bridge horizontal',5*148.5/4/ztop[1],12,'5 N phone push',
           'Simply supported span148.5mm, centre push along X; bridge longitudinal direction Y is in the print plane.')
    stress('Phone rear top bridge vertical',5*148.5/4/ztop[0],12,'5 N alternate direction',
           'Separate vertical midpoint force, not simultaneously added to horizontal push.')
    zclip=sections['phone_lower_clip_bolt']['section_modulus_transverse_mm3'][1]
    stress('Phone short corner clip',2.5*8.5/zclip,12,'5 N pane push via lower clips',
           'Two clips share pane load,2.5N each at8.5mm from bolt; actual net section through clearance hole. No force applied to absent front bar.')
    envelopes=[('frozen R2 2g',baseline['loads']['two_leg_2g_N_per_leg']),('R3 solid mass 2g',mass*9.81)]
    if args.sliced_total_mass_kg is not None:
        envelopes.append(('R3 sliced mass 2g',args.sliced_total_mass_kg*9.81))
    worst_posts={}
    for case,F in envelopes:
        stress('Yaw lower arm',F*32/sections['yaw_lower']['section_modulus_transverse_mm3'][0],12,case,
               'Entire leg vertical envelope assigned to lower arm; upper/lower force sharing remains unknown.')
        for key in ('femur_bridge','tibia_bridge'):
            s=sections[key]
            # Beam runs along Y. Vertical loading bends about X.
            stress(key,F*38/4/s['section_modulus_transverse_mm3'][0],4,case,
                   '38mm clear span simply supported under central vertical force. Actual chamfers and longitudinal bolt holes included in section. Layer-normal tension.')
        scored=[(4*(F*18/s['section_modulus_transverse_mm3'][1]+250/s['section_modulus_transverse_mm3'][0]),s) for s in post_scan]
        demand,worst=max(scored,key=lambda pair:pair[0])
        worst_posts[case]=worst
        add('Coxa post scanned',demand,12,case,
            'Vertical load18mm eccentric, side force5N with50mm lever; scan all staggered windows and shoulder.')
        stress('Curved foot',F*25/sections['foot']['section_modulus_transverse_mm3'][0]+125/sections['foot']['section_modulus_transverse_mm3'][1],12,case,
               'Perpendicular envelope load over25mm plus5N lateral over25mm.')
        bolt=588/(4*7)+F/4
        stress('Horn group bearing',bolt/(3.4*4),8,case,'Four M3 bolts on14mm PCD; unchanged4mm cheek thickness at horn.')
        stress('External washer face punching shear',bolt/(math.pi*5.7*4),3,case,
               'Full4mm cheek face replaces0.8mm nut-pocket face; conservative5.7mm effective perimeter. Washer geometry and preload require coupon verification.')
        stress('Yaw lower horn counterbore face shear',bolt/(math.pi*6.2*6.5),3,case,
               '9mm plate with2.5mm counterbore retains6.5mm below head-bearing plane. Hole splitting and metal engagement remain separate checks.')
    walking=None
    if args.walking_trajectory:
        simulation_report_path=args.walking_trajectory.parent/'simulation_report.json'
        simulation_report=json.loads(simulation_report_path.read_text())
        assert args.as_printed_manifest is not None
        assert simulation_report['inputs']['manifest_sha256']==hashlib.sha256(args.as_printed_manifest.read_bytes()).hexdigest()
        assert simulation_report['inputs']['unchanged_during_run']
        assert abs(simulation_report['mass_kg']-args.sliced_total_mass_kg)<1e-9
        traj=json.loads(args.walking_trajectory.read_text())
        walking={}
        for label,joint in [('femur','hip'),('tibia','knee')]:
            scored=[]
            for frame in traj['frames']:
                for leg,force in frame['foot_normal_n'].items():
                    torque=abs(frame['joint_torque_nm'][joint+'_'+leg])
                    for s in cheek_scans[label]:
                        demand=4*(1000*torque/s['section_modulus_transverse_mm3'][0]+abs(force)/s['area_mm2'])
                        scored.append((demand,frame['time_s'],leg,s['cut_mm'],torque,force))
            demand,time,leg,x,torque,force=max(scored)
            walking[label]=dict(demand_MPa=demand,conditional_margin=12/demand,time_s=time,
                                leg=leg,cut_x_mm=x,joint_torque_Nm=torque,foot_normal_N=force)
            add(label+' ordinary-walk sagittal envelope',demand,12,'sampled R3 walking',
                'Per-frame same-leg measured joint torque applied unattenuated to all scanned main-cheek sections, plus full foot normal treated as axial demand. No lateral bending, torsion, contact preload or perfect auxiliary sharing is inferred.')
    inputs=[manifest,ROOT/'cad/leg.py',ROOT/'cad/phone.py',ROOT/'cad/body.py']
    inputs.extend(MESH/(name+'.stl') for name in CACHE)
    if args.slice_mass_source:
        inputs.append(args.slice_mass_source.resolve())
    if args.as_printed_manifest:
        inputs.append(args.as_printed_manifest.resolve())
    if args.walking_trajectory:
        inputs.append(args.walking_trajectory.resolve())
        inputs.append(simulation_report_path.resolve())
    report=dict(status='conditional_analytical_screen_no_printed_strength_pass',
                baseline_reference='baseline_r2/strength_results.json',
                solid_total_mass_kg=mass,sliced_total_mass_kg=args.sliced_total_mass_kg,
                sliced_mass_evidence=sliced_evidence,
                sampled_walking_screen=walking,
                frozen_loads=baseline['loads'],notch_factor=2,effective_section_ratio=.5,
                assumptions='Room temperature short duration.12MPa XY tension,4MPa Z tension,3MPa shear,8MPa bearing. No bead or joint damage model.',
                sections=sections,post_scan=post_scan,phone_scan=phone_scan,
                longitudinal_cheek_scans=cheek_scans,worst_cheek_sections=worst_cheeks,
                worst_phone_section=worst_phone,worst_post_sections=worst_posts,
                results=rows,
                source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (OUT/'r3_strength_results.json').write_text(json.dumps(report,indent=2)+'\n')
    for r in rows:
        print(f"{r['case']}: {r['check']}: {r['demand_MPa']:.3f}MPa margin{r['conditional_margin']:.3f}")
    print('Worst phone cut',worst_phone['cut_mm'])
    print('Worst post cuts',{k:v['cut_mm'] for k,v in worst_posts.items()})
    print('Conditional side force',{k:sections[k]['conditional_side_force_at_100mm_N'] for k in ('femur','tibia')})


if __name__=='__main__':
    main()
