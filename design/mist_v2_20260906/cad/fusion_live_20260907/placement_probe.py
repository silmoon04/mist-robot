import json
from pathlib import Path
import adsk.core
import adsk.fusion

OUTPUT=Path(r'/design/mist_v2_20260906/cad/fusion_live_20260907/native_body')


def run(_context: str):
    d=adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
    marker=d.rootComponent.attributes.itemByName('MIST','build_stage')
    if not marker or marker.value!='concealed_wheel_20260907':
        raise RuntimeError('Unexpected active document')
    occ=d.rootComponent.occurrences.item(0)
    move=adsk.core.Matrix3D.create()
    move.translation=adsk.core.Vector3D.create(0,0,-3.5)
    occ.transform2=move
    pending_before=d.snapshots.hasPendingSnapshot
    d.computeAll()
    without_capture=occ.transform2.translation.z
    occ.transform2=move
    pending_captured=d.snapshots.hasPendingSnapshot
    if pending_captured:
        snap=d.snapshots.add()
        if snap is None:
            raise RuntimeError('Could not capture body placement')
    d.computeAll()
    with_capture=occ.transform2.translation.z
    report={'pending_before':pending_before,'without_capture_z_cm':without_capture,
            'pending_before_capture':pending_captured,'with_capture_z_cm':with_capture,
            'snapshot_count':d.snapshots.count}
    (OUTPUT/'placement_regression.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
    if abs(with_capture+3.5)>1e-9:
        raise RuntimeError('Captured placement did not survive Compute All')
