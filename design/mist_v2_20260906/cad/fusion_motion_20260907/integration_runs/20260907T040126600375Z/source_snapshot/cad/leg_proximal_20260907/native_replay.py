"""Replay the proximal candidate as editable Fusion feature components.

This entry point is unexecuted until Autodesk sign-in and a native script run.
It consumes the same saved recipes as the offline exporter; it does not certify
their load capacity, collision clearance or purchased hardware interfaces.
"""
from pathlib import Path
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
CAD=HERE.parent
for directory in (CAD,HERE):
    if str(directory) not in sys.path:
        sys.path.insert(0,str(directory))


def build_leg(root,params,leg_name='FL',specification=None,**pose):
    import adsk.core
    import native_parts as native
    import proximal_leg
    spec=specification or proximal_leg.leg_spec(params,leg_name,**pose)
    if spec['leg_name']!=leg_name:
        raise ValueError('The native leg and recipe identities disagree')
    names=[part['name'] for part in spec['parts']]
    if len(names)!=len(set(names)):
        raise ValueError('The recipe contains duplicate part names')
    assembly=root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    assembly.component.name='MIST_'+leg_name+'_proximal_candidate'
    components={}
    bodies={}
    occurrences={}
    for part in spec['parts']:
        ops=part['ops']
        if not ops or ops[0].get('mode')=='cut':
            raise ValueError('Part needs an initial positive solid: '+part['name'])
        occurrence=assembly.component.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        component=occurrence.component
        component.name=part['name']
        target=None
        for index,op in enumerate(ops):
            name=part['name']+'_'+str(index+1)
            kind=op['kind']
            if kind=='box':
                tool=native.box(component,name,op['center'],op['size'])
            elif kind=='cylinder':
                tool=native.cylinder(component,name,op['start'],op['end'],op['radius'])
            elif kind=='annulus':
                tool=native.annulus(component,name,op['start'],op['end'],op['radius'],op['inner'])
            elif kind=='polygon':
                tool=native.polygon(component,name,op['points'],op['thickness'],op['origin'],op['normal'],op['x_axis'])
            else:
                raise ValueError('Unknown solid operation: '+str(kind))
            if target is None:
                target=tool
            elif op['mode']=='cut':
                target=native.subtract(component,target,[tool],name+'_cut')
            elif op['mode'] in ('add','union'):
                target=native.union(component,target,[tool],name+'_join')
            else:
                raise ValueError('Unknown Boolean mode: '+str(op['mode']))
        if not target or not target.isSolid or target.volume<=0:
            raise RuntimeError('Native replay produced no solid: '+part['name'])
        if component.bRepBodies.count!=1:
            raise RuntimeError('Native part has more than one body: '+part['name'])
        target.name=part['name']
        transform=adsk.core.Matrix3D.create()
        for row in range(4):
            for column in range(4):
                value=part['transform'][row][column]
                transform.setCell(row,column,value/10 if column==3 and row<3 else value)
        occurrence.transform2=transform
        for key in ('category','material','rigid_group','mass_group','note'):
            if key in part:
                component.attributes.add('MIST',key,str(part[key]))
        component.attributes.add('MIST','recipe_sha256',hashlib.sha256(json.dumps(part,sort_keys=True).encode()).hexdigest())
        if part.get('color') in proximal_leg.COLORS:
            component.attributes.add('MIST','color_rgba',json.dumps(proximal_leg.COLORS[part['color']]))
        components[part['name']]=component
        bodies[part['name']]=target
        occurrences[part['name']]=occurrence
    return dict(occurrence=assembly,components=components,bodies=bodies,spec=spec,
                checks=dict(native_feature_replay_completed=True,native_motion_joints_created=False,
                            physical_fit_validated=False,production_release=False),
                recipe_sha256=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest())


def build_four_legs(root,params,specifications=None,**pose):
    names=params['geometry']['leg_names']
    if specifications is not None and [spec['leg_name'] for spec in specifications]!=names:
        raise ValueError('Native recipe order must match geometry.leg_names')
    return [build_leg(root,params,name,
                     specification=specifications[index] if specifications is not None else None,**pose)
            for index,name in enumerate(names)]
