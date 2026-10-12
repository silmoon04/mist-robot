"""Read immutable vendor STEP solids alongside native dimensional recipes."""
from pathlib import Path
import hashlib
import cadquery as cq
import export_body

_ordinary_shape=export_body.tool_shape

def tool_shape(op):
    if op['kind']!='step_reference':
        return _ordinary_shape(op)
    path=Path(op['path'])
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=op['sha256']:
        raise ValueError('Vendor STEP hash does not match the frozen reference: '+str(path))
    shape=cq.importers.importStep(str(path)).val()
    if not shape.isValid() or len(shape.Solids())!=1 or shape.Volume()<=0:
        raise ValueError('Vendor STEP must import as one valid non-empty solid')
    return shape

def enable_step_references():
    export_body.tool_shape=tool_shape
