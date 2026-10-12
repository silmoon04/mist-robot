"""R5 mesh-derived section comparison. No material failure simulation is claimed."""
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
    parser.add_argument('--slice-mass-source',type=Path)
    parser.add_argument('--as-printed-manifest',type=Path)
    parser.add_argument('--walking-trajectory',type=Path)
    args=parser.parse_args()
    manifest_path=ROOT/'cad/output/assembly_manifest.json'
    m=json.loads(manifest_path.read_text())
    assert 'r5' in m['revision'].lower(), 'Wait for completed R5 export.'
    sources=[manifest_path]
    for filename,h in m['source_hashes'].items():
        p=(ROOT/'cad'/filename).resolve()
        if p.exists():
            assert hashlib.sha256(p.read_bytes()).hexdigest()==h,filename
            sources.append(p)
    solid_mass=m['total_mass_kg']
    mass=solid_mass
    mass_kind='solid CAD comparison'
    slice_evidence=None
    if args.slice_mass_source:
        s=json.loads(args.slice_mass_source.read_text())
        assert s['status']=='pass'
        assert s['source_manifest_hash']==hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        assert {p['sku'] for p in s['parts']}=={p['sku'] for p in m['print_parts']}
        model_mass=s['quantity_weighted_totals']['model_mass_g']/1000
        mass=solid_mass-m['printable_mass_solid_kg']+model_mass
        mass_kind='toolpath-estimated assembly'
        slice_evidence=dict(sku_count=len(s['parts']),pieces=s['quantity_weighted_totals']['piece_count'],
                            model_mass_kg=model_mass,support_excluded_g=s['quantity_weighted_totals']['support_mass_g'])
        sources.append(args.slice_mass_source.resolve())
    if args.as_printed_manifest:
        p=json.loads(args.as_printed_manifest.read_text())
        assert args.slice_mass_source is not None
        assert p['mass_model']['source_solid_manifest_sha256']==hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        assert p['mass_model']['source_production_properties_sha256']==hashlib.sha256(args.slice_mass_source.read_bytes()).hexdigest()
        assert abs(p['total_mass_kg']-mass)<1e-6
        mass=p['total_mass_kg']
        sources.append(args.as_printed_manifest.resolve())
    hip_x=m['parameters']['coxa_mm']
    sections={}
    specs=[('femur_bridge','FL_femur_main_and_knee_saddle',1,0,[57.99,13.49,72.01,27.51]),
           ('tibia_bridge','FL_tibia_curved_main_and_foot',1,8,[31.99,-7.01,48.01,7.01]),
           ('yaw_lower','FL_coxa_lower_auxiliary_arm',0,20,None),
           ('tibia_shank_80','FL_tibia_curved_main_and_foot',0,80,None)]
    for label,name,axis,pos,region in specs:
        sections[label]=section(name,axis,pos,region)
    roots={}
    for label,name,end in [('femur','FL_femur_main_and_knee_saddle',58),
                           ('tibia','FL_tibia_curved_main_and_foot',32)]:
        roots[label]=[section(name,0,float(x),[14.99,-100,23.01,100]) for x in np.arange(11.,end,.5)]
    post=[section('FL_coxa_upper_and_hip_saddle',2,float(z)) for z in np.arange(-43.75,-17.99,.25)]
    shank=[section('FL_tibia_curved_main_and_foot',0,float(x)) for x in np.arange(52.,101.,.5)]
    rows=[]
    def add(name,demand,allow,case,detail,evidence=None):
        rows.append(dict(check=name,demand_MPa=demand,allowable_MPa=allow,
                         conditional_margin=allow/demand,case=case,detail=detail,evidence=evidence))
    def post_score(F,s):
        e=hip_x-s['centroid_transverse_mm'][0]
        return 4*abs(F)*(1/s['area_mm2']+abs(e)/s['section_modulus_transverse_mm3'][1])
    for n in (4,3):
        F=mass*9.81/n
        demand,s=max(((post_score(F,s),s) for s in post),key=lambda q:q[0])
        add('Post equal '+str(n)+'-foot vertical support',demand,12,'1g reference',
            'Full per-leg force assigned to post, including axial force and actual hip-to-section-centroid lever. Direct upper-plate sharing is not credited.',s)
    demand,s=max(((4*588/s['section_modulus_transverse_mm3'][1],s) for s in post),key=lambda q:q[0])
    add('Post entire torque-cap allocation',demand,12,'separate allocation bound',
        'All0.588Nm hypothetically in post bending. Parallel upper path makes this allocation unvalidated.',s)
    for label,scan in roots.items():
        values=[(4*(588/s['section_modulus_transverse_mm3'][0]+500/s['section_modulus_transverse_mm3'][1]),s) for s in scan]
        demand,s=max(values,key=lambda q:q[0])
        add(label+' one-cheek disturbance',demand,12,'independent 5N side-force bound',
            'Constant588Nmm sagittal and500Nmm lateral moment on one main cheek; not observed gait loads and not a whole-leg allowable.',s)
    F2g=mass*9.81
    for label in ('femur_bridge','tibia_bridge'):
        demand=4*F2g*38/4/sections[label]['section_modulus_transverse_mm3'][0]
        add(label+' transverse bending',demand,4,'two-leg 2g proof reference',
            'Central vertical force on38mm clear span with auxiliary fastener retained. Layer-normal tension assumption.',sections[label])
    demand,s=max(((post_score(F2g,s),s) for s in post),key=lambda q:q[0])
    add('Post vertical shock reference',demand,12,'two-leg 2g proof reference',
        'Vertical and axial only; no extra lateral force or torque added.',s)
    walking=None
    if args.walking_trajectory:
        sr_path=args.walking_trajectory.parent/'simulation_report.json'
        sr=json.loads(sr_path.read_text())
        assert args.as_printed_manifest is not None
        assert sr['inputs']['manifest_sha256']==hashlib.sha256(args.as_printed_manifest.read_bytes()).hexdigest()
        assert sr['inputs']['unchanged_during_run']
        assert abs(sr['mass_kg']-mass)<1e-8
        frames=json.loads(args.walking_trajectory.read_text())['frames']
        sources += [args.walking_trajectory.resolve(),sr_path.resolve()]
        walking={}
        for label,joint in [('femur','hip'),('tibia','knee')]:
            best=(-1,None)
            for f in frames:
                for leg,F in f['foot_normal_n'].items():
                    T=abs(f['joint_torque_nm'][joint+'_'+leg])
                    for s in roots[label]:
                        demand=4*(1000*T/s['section_modulus_transverse_mm3'][0]+abs(F)/s['area_mm2'])
                        if demand>best[0]:best=(demand,dict(time_s=f['time_s'],leg=leg,force_N=F,torque_Nm=T,section=s))
            add(label+' sampled sagittal root',best[0],12,'sampled R5 walking',
                'Same-frame torque applied unattenuated to scanned root sections plus full foot normal as axial force. No off-axis contact or preload model.',best[1])
            walking[label]=best[1]
        best=(-1,None)
        for f in frames:
            for leg,F in f['foot_normal_n'].items():
                for s in post:
                    demand=post_score(F,s)
                    if demand>best[0]:best=(demand,dict(time_s=f['time_s'],leg=leg,force_N=F,section=s))
        add('Post sampled vertical and axial envelope',best[0],12,'sampled R5 walking',
            'Full sampled foot normal assigned to post at actual hip-to-centroid lever, no added motor torque or lateral force.',best[1])
        walking['post']=best[1]
        # Beyond X51 only the centred shank remains. Resolve normal contact force
        # into the actual tibia frame; tangential contact and bead damage are absent.
        best=(-1,None)
        for f in frames:
            q=f['base_quat_xyzw']
            base=trimesh.transformations.quaternion_matrix([q[3],q[0],q[1],q[2]])[:3,:3]
            for leg,F in f['foot_normal_n'].items():
                yaw=math.radians(m['parameters']['leg_azimuth_deg'][leg])+f['joint_rad']['yaw_'+leg]
                pitch=f['joint_rad']['hip_'+leg]+f['joint_rad']['knee_'+leg]
                rz=np.array([[math.cos(yaw),-math.sin(yaw),0],[math.sin(yaw),math.cos(yaw),0],[0,0,1]])
                ry=np.array([[math.cos(pitch),0,math.sin(pitch)],[0,1,0],[-math.sin(pitch),0,math.cos(pitch)]])
                force=(base@rz@ry).T@np.array([0.,0.,F])
                for s in shank:
                    cy,cz=s['centroid_transverse_mm']
                    arm=np.array([105-s['cut_mm'],-cy,-cz])
                    moment=np.cross(arm,force)
                    zy,zz=s['section_modulus_transverse_mm3']
                    demand=4*(abs(force[0])/s['area_mm2']+abs(moment[1])/zy+abs(moment[2])/zz)
                    if demand>best[0]:best=(demand,dict(time_s=f['time_s'],leg=leg,force_local_N=force.tolist(),moment_local_Nmm=moment.tolist(),section=s))
        add('Straight shank normal-contact beam screen',best[0],12,'sampled R5 walking',
            'Actual resolved foot normal,105mm toe point,axial+bending in centred shank beyondX51. Tangential friction,self-inertia and root sharing are not included.',best[1])
        walking['shank']=best[1]
    sources += [MESH/(name+'.stl') for name in CACHE]
    sources += [Path(__file__).resolve(),OUT/'write_r5_report.py']
    out=dict(status='conditional_analytical_screen_not_printed_validation',revision=m['revision'],
             solid_mass_kg=solid_mass,mass_kg=mass,mass_kind=mass_kind,slicing=slice_evidence,hip_x_mm=hip_x,
             assumptions=dict(XY_tension_MPa=12,Z_tension_MPa=4,shear_MPa=3,bearing_MPa=8,notch_factor=2,effective_section_factor=.5,
                              condition='Short duration near room temperature; engineering assumptions,not spool allowables'),
             sections=sections,main_root_scans=roots,post_scan=post,shank_scan=shank,results=rows,walking=walking,
             source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    (OUT/'r5_strength_results.json').write_text(json.dumps(out,indent=2)+'\n')
    for row in rows:print(f"{row['check']}: {row['demand_MPa']:.3f}MPa; margin{row['conditional_margin']:.3f}")


if __name__=='__main__':main()

