"""Label the imported solid bodies so Fusion names match the print files."""
from pathlib import Path
import importlib.util,sys,json,hashlib
import adsk.core,adsk.fusion
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'

def run(context):
    app=adsk.core.Application.get();doc=app.activeDocument;design=adsk.fusion.Design.cast(app.activeProduct)
    digest=hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest()
    marker=doc.attributes.itemByName('single_leg_r7_wide_joints_20260914','input_sha256')
    assert marker and marker.value==digest,'Activate the current R7 assembly first'
    spec=importlib.util.spec_from_file_location('r7_label_helpers',ROOT.parent/'hexapod_phone_quad_r5_20260912/cad/fusion_import.py');h=importlib.util.module_from_spec(spec);sys.modules[spec.name]=h;spec.loader.exec_module(h)
    m=json.loads((OUT/'manifest.json').read_text());mapping=[]
    for occ in design.rootComponent.occurrences:
        name='base_mount' if occ.component.name=='base' else occ.component.name
        expected=[p for p in m['parts'] if p['link']==name]
        if not expected:continue
        bodies=[p.nativeObject or p for p in h._bodies(occ)]
        for part in [p for p in expected if p['material']!='servo']:
            body=min(bodies,key=lambda b:abs(part['volume_mm3']-b.volume*1000))
            assert abs(part['volume_mm3']-body.volume*1000)<max(.001,part['volume_mm3']*1e-6)
            mapping.append((body,part));bodies.remove(body)
        servos=[p for p in expected if p['material']=='servo']
        if servos:
            assert len(servos)==1
            part=servos[0]
            total=sum(b.getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume*1000 for b in bodies)
            assert abs(total-part['volume_mm3'])<max(.01,part['volume_mm3']*1e-4),(name,total,part['volume_mm3'])
            bodies.sort(key=lambda b:b.volume,reverse=True)
            for i,body in enumerate(bodies):mapping.append((body,dict(part,name=part['name']+('__housing' if i==0 else '__shaft_reference'))))
        else:assert not bodies
    assert sum(p['printable'] for b,p in mapping)==15
    source=h._appearance_source(app);appearances={}
    if source:
        for name,rgb in {'servo':(48,57,64),'metal':(179,191,194),'printed':(56,148,154),'cap':(211,166,93),'bench':(105,119,121)}.items():
            appearance=design.appearances.addByCopy(source,'R7_part_'+name)
            for prop in appearance.appearanceProperties:
                colour=adsk.core.ColorProperty.cast(prop)
                if colour:colour.value=adsk.core.Color.create(*rgb,255);break
            appearances[name]=appearance
    for body,p in mapping:
        body.name=p['name'];component=body.parentComponent
        if component.name not in ('base','coxa','femur','tibia') and component.bRepBodies.count==1:component.name=p['name']
        key=p['material'] if p['material'] in ('servo','metal') else 'bench' if 'bench' in p['name'] else 'cap' if 'cap' in p['name'] or 'spacer' in p['name'] else 'printed'
        if key in appearances:body.appearance=appearances[key]
    adsk.doEvents();app.activeViewport.refresh()
    design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(OUT/'fusion/Single_Leg_R7.f3d')))
    app.activeViewport.saveAsImageFile(str(OUT/'fusion/assembled.png'),1500,1100)
    path=OUT/'fusion/fusion_report.json';report=json.loads(path.read_text());report['named_bodies']=[p['name'] for b,p in mapping];report['body_names_match_print_parts']=True;path.write_text(json.dumps(report,indent=2))
    return {'status':'completed','named_body_count':len(mapping)}
