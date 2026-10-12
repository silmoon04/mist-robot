"""Read native construction coordinates during joint setup."""
import json
from pathlib import Path
import adsk.core
import adsk.fusion


def run(_context: str):
    app=adsk.core.Application.get()
    design=None
    for doc in app.documents:
        if doc.name.startswith('Hexapod reference quadruped phone'):
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
