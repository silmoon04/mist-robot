"""Remove only the failed, task-owned first-leg stage; preserve the body."""
import json
from pathlib import Path
import adsk.core
import adsk.fusion


def run(_context: str):
    app=adsk.core.Application.get()
    design=adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        raise RuntimeError('No active design')
    root=design.rootComponent
    marker=root.attributes.itemByName('MIST','build_stage')
    if not marker or marker.value!='concealed_wheel_20260907':
        raise RuntimeError('Task-owned body is not active')
    failed=[occ for occ in root.occurrences if occ.component.attributes.itemByName('MIST','concealed_leg')
            and occ.component.attributes.itemByName('MIST','concealed_leg').value=='FL']
    if len(failed)!=1:
        raise RuntimeError('Expected exactly one failed FL stage')
    occurrence=failed[0]
    status=occurrence.component.attributes.itemByName('MIST','build_status')
    if not status or status.value!='building':
        raise RuntimeError('Refusing to remove a completed leg')
    before=sum(item.component.bRepBodies.count for item in root.allOccurrences)
    if not occurrence.deleteMe():
        raise RuntimeError('Failed-stage removal did not succeed')
    if design.computeAll() is False:
        raise RuntimeError('Recompute after failed-stage removal failed')
    after=sum(item.component.bRepBodies.count for item in root.allOccurrences)
    if after!=33:
        raise RuntimeError('Unexpected remaining body count')
    report={'status':'completed','before_solids':before,'after_solids':after,'only_failed_FL_removed':True}
    path=Path(__file__).with_name('failed_FL_cleanup.json')
    path.write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
