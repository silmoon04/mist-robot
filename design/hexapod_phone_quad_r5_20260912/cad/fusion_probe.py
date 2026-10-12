"""Read native construction coordinates during joint setup."""
import json
import importlib.util
from pathlib import Path
import adsk.core
import adsk.fusion


def run(_context: str):
    source = Path(__file__).resolve().with_name('fusion_runtime_r5.py')
    spec = importlib.util.spec_from_file_location('hex_quad_r5_runtime_loader', source)
    loader = importlib.util.module_from_spec(spec)
    exec(compile(source.read_bytes(), str(source), 'exec'), loader.__dict__)
    runtime = loader.load_runtime()
    _, _, _, _, digest = runtime._preflight()
    app=adsk.core.Application.get()
    design=None
    for doc in app.documents:
        marker = doc.attributes.itemByName('hexapod_phone_quad_r5_20260912','input_sha256')
        if marker and marker.value == digest:
            candidate=adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
            if candidate and candidate.rootComponent.occurrences.count==14:
                design=candidate
                break
    if design is None:
        raise RuntimeError('Imported quadruped document not found')
    data={'probe_version':3,'design_type':design.designType,'document':design.parentDocument.name,'components':[], 'root_points':[]}
    for p in design.rootComponent.constructionPoints:
        data['root_points'].append({'name':p.name,'point':p.geometry.asArray()})
    for o in design.rootComponent.occurrences:
        row={'name':o.component.name,'pose':o.transform2.asArray(),'points':[],'axes':[]}
        for p in o.component.constructionPoints:
            row['points'].append({'name':p.name,'point':p.geometry.asArray(),'proxy_point':p.createForAssemblyContext(o).geometry.asArray()})
        for a in o.component.constructionAxes:
            row['axes'].append({'name':a.name,'origin':a.geometry.origin.asArray(),'direction':a.geometry.direction.asArray()})
        data['components'].append(row)
    Path(__file__).with_name('output').joinpath('fusion','construction_probe.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps(data))
    return {'status':'read_only_probe_complete'}
