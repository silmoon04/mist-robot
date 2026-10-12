"""Build, account for, and export the new hexapod-derived quadruped."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import geom as g
from body import build_body
from leg import build_leg, build_coupons as leg_coupons
from phone import build_phone, build_coupons as phone_coupons

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cad' / 'output'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rotation(rpy):
    x,y,z = map(math.radians, rpy)
    rx=np.array([[1,0,0],[0,math.cos(x),-math.sin(x)],[0,math.sin(x),math.cos(x)]])
    ry=np.array([[math.cos(y),0,math.sin(y)],[0,1,0],[-math.sin(y),0,math.cos(y)]])
    rz=np.array([[math.cos(z),-math.sin(z),0],[math.sin(z),math.cos(z),0],[0,0,1]])
    return rz@ry@rx


def pose(xyz=(0,0,0), rpy=(0,0,0)):
    m=np.eye(4); m[:3,:3]=rotation(rpy); m[:3,3]=xyz
    return m


def shape_at(shape, m):
    from OCP.gp import gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    t=gp_Trsf()
    t.SetValues(*[float(m[i,j]) for i in range(3) for j in range(4)])
    return BRepBuilderAPI_Transform(shape,t,True).Shape()


def load_assembly():
    cfg=json.loads((ROOT/'settings.json').read_text())
    parts=build_body()+build_phone()
    poses={'base':np.eye(4), 'phone_pan':pose(cfg['phone_pan_origin_mm'])}
    joints={'phone_pan':dict(parent='base',origin_mm=cfg['phone_pan_origin_mm'],
             rpy_deg=[0,0,0],axis=[0,0,1],type='continuous',limits_rad=[-math.pi,math.pi],
             neutral_angle_rad=0)}
    qh=cfg['neutral_deg']['hip']; qk=cfg['neutral_deg']['knee']
    template=build_leg()
    for label,azimuth in cfg['leg_azimuth_deg'].items():
        a=math.radians(azimuth)
        mount=pose([cfg['yaw_radius_mm']*math.cos(a),cfg['yaw_radius_mm']*math.sin(a),cfg['yaw_height_mm']], [0,0,azimuth])
        coxa='coxa_'+label; femur='femur_'+label; tibia='tibia_'+label
        poses[coxa]=mount
        poses[femur]=mount@pose([cfg['coxa_mm'],0,0],[0,qh,0])
        poses[tibia]=poses[femur]@pose([cfg['femur_mm'],0,0],[0,qk,0])
        joints[coxa]=dict(parent='base',origin_mm=mount[:3,3].tolist(),rpy_deg=[0,0,azimuth],axis=[0,0,1],
                        type='revolute',limits_rad=[math.radians(-25),math.radians(25)],neutral_angle_rad=0)
        joints[femur]=dict(parent=coxa,origin_mm=[cfg['coxa_mm'],0,0],rpy_deg=[0,0,0],axis=[0,1,0],
                          type='revolute',limits_rad=[math.radians(3),math.radians(35)],neutral_angle_rad=math.radians(qh))
        joints[tibia]=dict(parent=femur,origin_mm=[cfg['femur_mm'],0,0],rpy_deg=[0,0,0],axis=[0,1,0],
                          type='revolute',limits_rad=[math.radians(30),math.radians(100)],neutral_angle_rad=math.radians(qk))
        for p in template:
            new=dict(p); new['sku']=p['name']; new['name']=label+'_'+p['name']
            if p['link']=='base_mount':
                new['link']='base'; new['shape']=shape_at(p['shape'],mount)
                new['print_shape']=p['shape']
            else:
                new['link']=p['link']+'_'+label
            parts.append(new)
    for p in parts:
        p.setdefault('sku',p['name'])
    # Explicit distributed allowance avoids pretending unmeasured leads are weightless.
    parts.append(dict(name='wiring_fastener_allowance',sku='wiring_fastener_allowance',
        shape=g.box(100,80,30,(0,0,20)),link='base',material='allowance',printable=False,
        allowance_only=True,mass_kg=.200,note='150 g wiring and protection, 50 g fasteners; replace with scale data.'))
    return cfg,parts,poses,joints


def properties(p):
    v=g.volume(p['shape'])
    density={'pla':1.24e-6,'metal':2.70e-6,'steel':7.85e-6}.get(p['material'],1.24e-6)
    mass=float(p.get('mass_kg',.055 if p['material']=='servo' else v*density))
    com=np.array(g.centroid(p['shape']))
    inertia=np.array(g.inertia(p['shape'])) * (mass/v) * 1e-6
    return mass,com,inertia


def inertia_dict(m):
    return dict(ixx=m[0,0],iyy=m[1,1],izz=m[2,2],ixy=m[0,1],ixz=m[0,2],iyz=m[1,2])


def aggregate(parts):
    values=[properties(p) for p in parts]
    total=sum(v[0] for v in values)
    com=sum(m*c for m,c,_ in values)/total
    tensor=np.zeros((3,3))
    for mass,c,inertia in values:
        d=(c-com)*.001
        tensor+=inertia+mass*(np.dot(d,d)*np.eye(3)-np.outer(d,d))
    return total,com,tensor


def overlaps(parts,poses):
    physical=[p for p in parts if not p.get('allowance_only')]
    shapes=[shape_at(p['shape'],poses[p['link']]) for p in physical]
    bboxes=[g.bounds(s) for s in shapes]
    collisions=[]; tests=0
    for i,a in enumerate(physical):
        for j in range(i):
            amin,amax=bboxes[i]; bmin,bmax=bboxes[j]
            if any(amax[k]<=bmin[k]+1e-5 or bmax[k]<=amin[k]+1e-5 for k in range(3)):
                continue
            tests+=1
            v=g.common_volume(shapes[i],shapes[j])
            if v>.01:
                collisions.append(dict(a=a['name'],b=physical[j]['name'],volume_mm3=v,
                                       same_link=a['link']==physical[j]['link']))
    return dict(boolean_pairs=tests,positive_intersections=collisions)


def export():
    OUT.mkdir(parents=True,exist_ok=True)
    for sub in ['links','parts_step','parts_mesh','print_stl','coupons_stl']:
        (OUT/sub).mkdir(exist_ok=True)
    cfg,parts,poses,joints=load_assembly()
    report=dict(units='mm',revision=cfg['revision'],parameters=cfg,parts=[],links={},
        status='Candidate geometry; physical fit and loaded walking unverified',
        source_hashes={name:sha(Path(__file__).parent/name)
            for name in ['geom.py','body.py','leg.py','phone.py','build.py']})
    records={}; printed_shapes={}
    for p in parts:
        assert g.valid(p['shape']),p['name']
        mass,com,inertia=properties(p)
        if not p.get('allowance_only'):
            g.export_stl(p['shape'],OUT/'parts_mesh'/f"{p['name']}.stl")
        report['parts'].append(dict(name=p['name'],sku=p['sku'],link=p['link'],material=p['material'],
            printable=p['printable'],allowance_only=p.get('allowance_only',False),mass_kg=mass,
            com_mm=com.tolist(),inertia_kg_m2=inertia_dict(inertia),volume_mm3=g.volume(p['shape']),
            bounds_mm=g.bounds(p['shape']),
            stl=None if p.get('allowance_only') else f"parts_mesh/{p['name']}.stl"))
        if p['printable']:
            sku=p['sku']
            if sku in records:
                records[sku]['quantity']+=1
                continue
            sh=p.get('print_shape',p['shape'])
            rot=p.get('print_rotation',(0,0,0))
            if 'print_rotation' not in p and p.get('print_axis')=='negative_z':
                rot=(180,0,0)
            sh=g.transform(sh,rpy_deg=rot)
            lo,hi=g.bounds(sh); sh=g.translate(sh,tuple(-v for v in lo))
            dims=[hi[k]-lo[k] for k in range(3)]
            g.export_stl(sh,OUT/'print_stl'/f'{sku}.stl')
            g.export_step(p.get('print_shape',p['shape']),OUT/'parts_step'/f'{sku}.step')
            records[sku]=dict(sku=sku,quantity=1,dimensions_mm=dims,solid_mass_g=mass*1000,
                stl=f'print_stl/{sku}.stl',print_rotation=list(rot),
                supports=p.get('supports',p.get('supports_required',p.get('assembly_note','Review orientation in print guide.'))))
            printed_shapes[sku]=sh
    for link,m in poses.items():
        lp=[p for p in parts if p['link']==link]
        mass,com,inertia=aggregate(lp)
        geometry=[p['shape'] for p in lp if not p.get('allowance_only')]
        g.export_step(geometry,OUT/'links'/f'{link}.step')
        g.export_stl(g.compound(geometry),OUT/'links'/f'{link}.stl')
        report['links'][link]=dict(mass_kg=mass,com_mm=com.tolist(),inertia_kg_m2=inertia_dict(inertia),
            stl=f'links/{link}.stl',step=f'links/{link}.step',assembly_transform=m.tolist(),
            **({'joint':joints[link]} if link in joints else {}))
    global_parts=[shape_at(p['shape'],poses[p['link']]) for p in parts if not p.get('allowance_only')]
    g.export_step(global_parts,OUT/'Hex_Quad_Phone_assembly.step')
    report['total_mass_kg']=sum(p['mass_kg'] for p in report['parts'])
    report['printable_mass_solid_kg']=sum(p['mass_kg'] for p in report['parts'] if p['printable'])
    report['print_parts']=list(records.values())
    report['assembly_bounds_mm']=g.bounds(g.compound(global_parts))
    report['coupons']=[]
    for p in leg_coupons()+phone_coupons():
        sh=g.transform(p['shape'],rpy_deg=p.get('print_rotation',(0,0,0)))
        lo,hi=g.bounds(sh); sh=g.translate(sh,tuple(-v for v in lo))
        assert g.valid(sh),p['name']
        g.export_stl(sh,OUT/'coupons_stl'/f"{p['name']}.stl")
        report['coupons'].append(dict(name=p['name'],stl=f"coupons_stl/{p['name']}.stl",
            dimensions_mm=[hi[k]-lo[k] for k in range(3)],note=p.get('assembly_note',p.get('note',''))))
    (OUT/'assembly_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with (OUT/'print_bom.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['part','quantity','X_mm','Y_mm','Z_mm','solid_mass_g_each','file'])
        for r in records.values():
            writer.writerow([r['sku'],r['quantity'],*r['dimensions_mm'],r['solid_mass_g'],r['stl']])
    audit=overlaps(parts,poses)
    audit['source_manifest_sha256']=sha(OUT/'assembly_manifest.json')
    (OUT/'static_interference.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps(dict(parts=len(parts),links=len(poses),mass_kg=report['total_mass_kg'],
        print_skus=len(records),coupons=len(report['coupons']),intersections=len(audit['positive_intersections']))))


if __name__=='__main__':
    export()
