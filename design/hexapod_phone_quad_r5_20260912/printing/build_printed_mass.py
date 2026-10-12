"""Assemble model-deposition mass properties in the actual robot link frames."""
from pathlib import Path
import copy
import hashlib
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
CAD=ROOT/'cad/output/assembly_manifest.json'
SLICES=ROOT/'manufacturing/slicing_r5/output/production_mass_properties.json'
OUT=ROOT/'cad/output/assembly_manifest_as_printed.json'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def matrix(t):
    if isinstance(t,list):
        return np.asarray(t,float)
    return np.array([[t['ixx'],t['ixy'],t['ixz']],
        [t['ixy'],t['iyy'],t['iyz']],[t['ixz'],t['iyz'],t['izz']]])


def tensor(t):
    return {name:float(t[i,j]) for name,i,j in [
        ('ixx',0,0),('iyy',1,1),('izz',2,2),('ixy',0,1),('ixz',0,2),('iyz',1,2)]}


def aggregate(parts):
    total=sum(p['mass_kg'] for p in parts)
    com=sum(p['mass_kg']*np.array(p['com_mm']) for p in parts)/total
    inertia=np.zeros((3,3))
    for p in parts:
        d=(np.array(p['com_mm'])-com)*.001
        inertia+=matrix(p['inertia_kg_m2'])+p['mass_kg']*(np.dot(d,d)*np.eye(3)-np.outer(d,d))
    assert np.linalg.eigvalsh(inertia).min()>0
    return total,com,inertia


def main():
    cad=json.loads(CAD.read_text()); slices=json.loads(SLICES.read_text())
    if slices['source_manifest_hash']!=sha(CAD):
        raise RuntimeError('Slices do not bind the current CAD manifest')
    by_sku={p['sku']:p for p in slices['parts']}
    assert len(by_sku)==len(cad['print_parts'])
    data=copy.deepcopy(cad)
    for p in data['parts']:
        if not p['printable']:
            continue
        s=by_sku[p['sku']]
        source=next(q for q in cad['print_parts'] if q['sku']==p['sku'])
        assert sha(CAD.parent/source['stl'])==s['source_stl_hash']
        t=np.array(p['print_to_link_transform'],float); r=t[:3,:3]
        assert np.allclose(r.T@r,np.eye(3),atol=1e-10)
        assert abs(np.linalg.det(r)-1)<1e-10
        com=r@np.array(s['com_mm'])+t[:3,3]
        inertia=r@matrix(s['inertia_kg_m2'])@r.T
        assert np.linalg.eigvalsh(inertia).min()>0
        assert np.all(np.isfinite(com))
        p['solid_CAD_properties']={k:p[k] for k in ('mass_kg','com_mm','inertia_kg_m2')}
        p['mass_kg']=s['mass_kg'];p['com_mm']=com.tolist();p['inertia_kg_m2']=tensor(inertia)
        p['mass_source']='Integrated Cura model deposition; support and adhesion excluded'
        p['deposition_source']={'sku':p['sku'],'source_stl_sha256':s['source_stl_hash'],
            'properties_json_sha256':sha(SLICES),
            'coordinate_frame':'Source print-STL frame transformed once into owning link',
            'support_mass_excluded_g':s['support_mass_g']}
    for link,row in data['links'].items():
        mass,com,inertia=aggregate([p for p in data['parts'] if p['link']==link])
        row['mass_kg']=mass;row['com_mm']=com.tolist();row['inertia_kg_m2']=tensor(inertia)
    data['total_mass_kg']=sum(p['mass_kg'] for p in data['parts'])
    data['printable_mass_solid_kg']=cad['printable_mass_solid_kg']
    data['printable_mass_deposited_kg']=sum(p['mass_kg'] for p in data['parts'] if p['printable'])
    expected=sum(s['mass_kg']*s['quantity'] for s in slices['parts'])
    assert abs(data['printable_mass_deposited_kg']-expected)<1e-10
    data['mass_model']={
        'kind':'Cura_model_deposition_high_fasteners',
        'as_sliced':True,'physical_measurement':False,
        'printed_parts':'Line-integrated commanded model deposition at layer mid-height',
        'fasteners':cad['mass_model']['fasteners'],'wire_allowance_kg':.150,
        'source_solid_manifest_sha256':sha(CAD),
        'source_production_properties_sha256':sha(SLICES),
        'integrator_sha256':sha(Path(__file__)),
        'notes':['Printed COM and full inertia tensors are transformed, not scaled from solid CAD.',
                 'Support and bed-adhesion material are not included on the robot.',
                 'These are toolpath estimates and nominal hardware geometry, not weighed parts.']}
    OUT.write_text(json.dumps(data,indent=2),encoding='utf-8')
    comparison={'status':'Mass reconciliation pass; physical weighing pending',
        'solid_CAD_manifest_sha256':sha(CAD),'printed_manifest_sha256':sha(OUT),
        'production_properties_sha256':sha(SLICES),'printed_SKUs':len(by_sku),
        'printed_pieces':sum(p['quantity'] for p in slices['parts']),
        'solid_robot_mass_kg':cad['total_mass_kg'],
        'deposition_robot_mass_kg':data['total_mass_kg'],
        'solid_PLA_kg':cad['printable_mass_solid_kg'],
        'model_deposition_PLA_kg':data['printable_mass_deposited_kg'],
        'difference_kg':cad['total_mass_kg']-data['total_mass_kg']}
    (ROOT/'printing/assembled_mass_comparison.json').write_text(json.dumps(comparison,indent=2),encoding='utf-8')
    print(json.dumps(comparison,indent=2))


if __name__=='__main__':
    main()
