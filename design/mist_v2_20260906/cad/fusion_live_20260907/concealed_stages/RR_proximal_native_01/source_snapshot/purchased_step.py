"""Import one traceable purchased solid without replacing printed feature recipes."""
import hashlib
from pathlib import Path
import adsk.core
import adsk.fusion


def import_single_solid(component, name, operation):
    path = Path(operation['path'])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != operation['sha256']:
        raise ValueError('Purchased STEP hash mismatch: ' + name)
    if component.bRepBodies.count or component.occurrences.count:
        raise ValueError('Purchased STEP needs a new, empty component')
    app = adsk.core.Application.get()
    options = app.importManager.createSTEPImportOptions(str(path))
    imported = app.importManager.importToTarget2(options, component)
    if imported is None:
        raise RuntimeError('Fusion failed to import purchased STEP: ' + name)
    components = [component] + [occ.component for occ in component.allOccurrences]
    bodies = [body for item in components for body in item.bRepBodies]
    if len(bodies) != 1 or not bodies[0].isSolid or bodies[0].volume <= 0:
        raise RuntimeError('Purchased reference must contain exactly one solid: ' + name)
    body = bodies[0]
    body.name = name
    body.parentComponent.name = name + '_supplier_solid'
    for target in (component, body.parentComponent):
        target.attributes.add('MIST', 'source_step_sha256', digest)
        target.attributes.add('MIST', 'source_step_path', str(path))
        target.attributes.add('MIST', 'geometry_origin', 'imported manufacturer STEP; purchased part')
    return body
