"""Export mesh-based single-leg URDF and conservative full-solid mass data."""
from pathlib import Path
import json,xml.etree.ElementTree as ET,hashlib
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'

def main():
    manifest=json.loads((OUT/'manifest.json').read_text());robot=ET.Element('robot',name='single_leg_r6');rows=[]
    for name in ('base_mount','coxa','femur','tibia'):
        link=ET.SubElement(robot,'link',name=name);parts=[]
        for p in manifest['parts']:
            if p['link']!=name:continue
            mesh=trimesh.load_mesh(OUT/p['assembly_stl']);mesh.apply_scale(.001)
            mass=p['solid_mass_kg'];com=mesh.center_mass;inertia=mesh.moment_inertia*mass/mesh.mass
            parts.append((mass,com,inertia))
            for kind in ('visual','collision'):
                item=ET.SubElement(link,kind,name=p['name']);geometry=ET.SubElement(item,'geometry');ET.SubElement(geometry,'mesh',filename=p['assembly_stl'],scale='0.001 0.001 0.001')
                if kind=='visual':
                    material=ET.SubElement(item,'material',name=p['name']+'_colour');ET.SubElement(material,'color',rgba='0.18 0.23 0.25 1' if p['material']=='servo' else '0.22 0.58 0.60 1')
        mass=sum(m for m,c,i in parts);com=sum(m*c for m,c,i in parts)/mass
        inertia=sum(i+m*(np.dot(c-com,c-com)*np.eye(3)-np.outer(c-com,c-com)) for m,c,i in parts)
        assert np.linalg.eigvalsh(inertia).min()>0
        item=ET.SubElement(link,'inertial');ET.SubElement(item,'origin',xyz=' '.join(map(str,com)));ET.SubElement(item,'mass',value=str(mass))
        ET.SubElement(item,'inertia',**{k:str(inertia[i,j]) for k,i,j in [('ixx',0,0),('ixy',0,1),('ixz',0,2),('iyy',1,1),('iyz',1,2),('izz',2,2)]})
        rows.append({'link':name,'mass_kg':mass,'com_m':com.tolist(),'inertia_kg_m2':inertia.tolist()})
    for name,parent,child,xyz,axis,lo,hi in [('yaw','base_mount','coxa','0 0 0','0 0 1',-55,55),('hip','coxa','femur','.082 0 0','0 1 0',-30,65),('knee','femur','tibia','.090 0 0','0 1 0',5,115)]:
        j=ET.SubElement(robot,'joint',name=name,type='revolute');ET.SubElement(j,'parent',link=parent);ET.SubElement(j,'child',link=child);ET.SubElement(j,'origin',xyz=xyz,rpy='0 0 0');ET.SubElement(j,'axis',xyz=axis)
        ET.SubElement(j,'limit',lower=str(np.radians(lo)),upper=str(np.radians(hi)),effort='0.8',velocity='0.5');ET.SubElement(j,'dynamics',damping='0.03',friction='0.0')
    ET.indent(robot);ET.ElementTree(robot).write(OUT/'Single_Leg_R7.urdf',encoding='utf-8',xml_declaration=True)
    report={'manifest_sha256':hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest(),'links':rows,
        'mass_model':'Uniform full-solid PLA as a conservative mass case, plus declared 55 g servos and aluminium horn geometry. Printed mass distribution, wires and fasteners are not measured.',
        'collision_limit':'Mesh collision interpretation depends on the simulator. The included Bullet test evaluates suspended motion without contact; it is not a walking or printed-material stress test.',
        'actuator_limit':'0.8 Nm effort and 0.5 rad/s are selected analysis bounds, not measured continuous servo ratings.'}
    (OUT/'urdf_properties.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
