import json
from pathlib import Path
import adsk.core
import adsk.fusion

OUTPUT=Path(r'/design/mist_v2_20260906/cad/fusion_live_20260907/native_body')


def run(_context: str):
    d=adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
    marker=d.rootComponent.attributes.itemByName('MIST','build_stage')
    if not marker or marker.value!='concealed_wheel_20260907':
        raise RuntimeError('Unexpected active design')
    o=d.rootComponent.occurrences.item(0)
    before={'ground_to_parent':o.isGroundToParent,'grounded':o.isGrounded,'z_cm':o.transform2.translation.z}
    o.isGroundToParent=False
    move=adsk.core.Matrix3D.create()
    move.translation=adsk.core.Vector3D.create(0,0,-3.5)
    o.transform2=move
    assigned=o.transform2.translation.z
    pending=d.snapshots.hasPendingSnapshot
    if pending:
        snapshot=d.snapshots.add()
        if snapshot is None:
            raise RuntimeError('Placement snapshot failed')
    if d.computeAll() is False:
        raise RuntimeError('Compute All failed')
    final=o.transform2.translation.z
    report={'before':before,'assigned_z_cm':assigned,'pending_snapshot':pending,
            'final_z_cm':final,'ground_to_parent':o.isGroundToParent,'snapshots':d.snapshots.count}
    print(json.dumps(report))
    if abs(final+3.5)>1e-9:
        raise RuntimeError('Placement still resets')
    (OUTPUT/'placement_fix_verified.json').write_text(json.dumps(report,indent=2))
