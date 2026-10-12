"""Build frozen concealed-leg recipes with editable features and supplier solids.

Identical parts reuse native component definitions. Assembly bindings retain each
leaf occurrence's complete root context, including imported supplier wrappers.
"""
import hashlib
import json
import time
import adsk.core
import adsk.fusion
import native_parts as native
import purchased_step


def recipe_key(part):
    fields={key:part.get(key) for key in ('name','ops','material','category','color')}
    return hashlib.sha256(json.dumps(fields,sort_keys=True).encode()).hexdigest()


def matrix_mm(values):
    matrix=adsk.core.Matrix3D.create()
    for row in range(4):
        for column in range(4):
            value=values[row][column]
            matrix.setCell(row,column,value/10 if column==3 and row<3 else value)
    return matrix


def cache_from_design(root):
    cache={}
    for occurrence in root.allOccurrences:
        component=occurrence.component
        marker=component.attributes.itemByName('MIST','native_recipe_key')
        if marker:
            cache[marker.value]=component
    return cache


def leaf_body(component):
    candidates=[component]+[item.component for item in component.allOccurrences]
    bodies=[body for item in candidates for body in item.bRepBodies]
    if len(bodies)!=1 or not bodies[0].isSolid:
        raise RuntimeError('A physical recipe part must contain exactly one solid')
    return bodies[0]


def build_part(component,part):
    operations=part['ops']
    if not operations or operations[0].get('mode')=='cut':
        raise ValueError('Part lacks an initial positive solid: '+part['name'])
    if any(op['kind']=='step_reference' for op in operations):
        if len(operations)!=1 or operations[0].get('mode') not in ('add','union'):
            raise ValueError('Supplier reference must be a standalone purchased part')
        return purchased_step.import_single_solid(component,part['name'],operations[0])
    target=None
    positive=[]
    def flush_positive(target):
        if not positive:
            return target
        members=([target] if target is not None else [])+positive[:]
        positive.clear()
        return native.union(component,members[0],members[1:],part['name']+'_positive_group') if len(members)>1 else members[0]
    for index,op in enumerate(operations):
        # Some printed recipes add disconnected ribs before their connecting
        # web. Build a contiguous additive run before joining it; this preserves
        # the CSG order while avoiding a false single-solid intermediate demand.
        if op['mode']=='cut':
            target=flush_positive(target)
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
            raise ValueError('Unsupported native recipe operation: '+kind)
        if op['mode']=='cut':
            target=native.subtract(component,target,[tool],name+'_cut')
        elif op['mode'] in ('add','union'):
            positive.append(tool)
        else:
            raise ValueError('Unknown Boolean operation: '+op['mode'])
    target=flush_positive(target)
    if component.bRepBodies.count!=1 or not target.isSolid or target.volume<=0:
        raise RuntimeError('Native recipe did not finish as one solid: '+part['name'])
    target.name=part['name']
    return target


def appearance(design,rgba):
    key='MIST RGB '+'-'.join(str(value) for value in rgba[:3])
    found=design.appearances.itemByName(key)
    if found:
        return found
    library=adsk.core.Application.get().materialLibraries.itemByName('Fusion Appearance Library')
    base=library.appearances.itemByName('Plastic - Matte (White)')
    found=design.appearances.addByCopy(base,key)
    for property_id in ('opaque_albedo','surface_albedo'):
        prop=adsk.core.ColorProperty.cast(found.appearanceProperties.itemById(property_id))
        if prop:
            prop.value=adsk.core.Color.create(*rgba[:3],255)
    return found


def build_leg(root,spec,palette,progress=None,extend=False,max_build_seconds=None):
    started=time.monotonic()
    leg=spec['leg_name']
    existing=[item for item in root.occurrences
              if item.component.attributes.itemByName('MIST','concealed_leg') and
              item.component.attributes.itemByName('MIST','concealed_leg').value==leg]
    if len(existing)>1 or (existing and not extend):
        raise RuntimeError('Concealed leg already present; inspect before rebuilding: '+leg)
    names=[part['name'] for part in spec['parts']]
    if len(names)!=len(set(names)):
        raise ValueError('Duplicate frozen part name in '+leg)
    cache=cache_from_design(root)
    assembly=existing[0] if existing else root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    if not existing:
        assembly.component.name='MIST_'+leg+'_concealed_drive'
        assembly.component.attributes.add('MIST','concealed_leg',leg)
    placed={}
    expected={part['name']:recipe_key(part) for part in spec['parts']}
    for occurrence in assembly.component.occurrences:
        key=occurrence.component.attributes.itemByName('MIST','native_recipe_key')
        name=occurrence.component.name
        if name not in expected or key is None or key.value!=expected[name]:
            raise RuntimeError('Existing native stage differs from frozen final recipe: '+leg+'/'+name)
        placed[name]=occurrence
    assembly.component.attributes.add('MIST','build_status','building')
    records=[]
    for index,part in enumerate(spec['parts']):
        key=recipe_key(part)
        already_placed=part['name'] in placed
        if (not already_placed and records and max_build_seconds is not None
                and time.monotonic()-started>max_build_seconds):
            break
        reused=key in cache or already_placed
        if progress:
            progress({'leg':leg,'part':part['name'],'index':index,'reused':reused})
        if already_placed:
            outer=placed[part['name']]
            body=leaf_body(outer.component)
        elif reused:
            outer=assembly.component.occurrences.addExistingComponent(cache[key],adsk.core.Matrix3D.create())
            body=leaf_body(outer.component)
        else:
            outer=assembly.component.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            outer.component.name=part['name']
            body=build_part(outer.component,part)
            for component in (outer.component,body.parentComponent):
                for attr in ('category','material','rigid_group','mass_group','note'):
                    if attr in part:
                        component.attributes.add('MIST',attr,str(part[attr]))
            outer.component.attributes.add('MIST','native_recipe_key',key)
            body.appearance=appearance(root.parentDesign,palette[part['color']])
            cache[key]=outer.component
        target_matrix=matrix_mm(part['transform'])
        outer_context=outer.createForAssemblyContext(assembly)
        if already_placed and not outer_context.transform2.isEqualTo(target_matrix):
            raise RuntimeError('Existing native stage placement differs: '+leg+'/'+part['name'])
        if not already_placed:
            native.place_occurrence(outer_context,target_matrix)
        records.append({'part':part,'outer':outer,'body':body,'reused':reused})
    if root.parentDesign.computeAll() is False:
        raise RuntimeError('Native concealed leg recompute failed: '+leg)
    components={}
    bodies={}
    bindings={}
    root_occurrences=[(item,item.fullPathName,item.component) for item in root.allOccurrences]
    for record in records:
        name=record['part']['name']
        outer=record['outer'].createForAssemblyContext(assembly)
        prefix=outer.fullPathName
        matches=[item for item,path,component in root_occurrences
                 if (path==prefix or path.startswith(prefix+'+'))
                 and component==record['body'].parentComponent]
        if len(matches)!=1:
            raise RuntimeError('Ambiguous physical leaf binding: '+leg+'/'+name)
        components[name]=record['body'].parentComponent
        bodies[name]=record['body']
        bindings[name]=matches[0]
    complete=len(records)==len(spec['parts'])
    assembly.component.attributes.add('MIST','build_status','completed' if complete else 'partial')
    return {'occurrence':assembly,'components':components,'bodies':bodies,'part_occurrences':bindings,
            'spec':spec,'complete':complete,'records':[{'name':r['part']['name'],'reused':r['reused'],
                       'path':bindings[r['part']['name']].fullPathName} for r in records]}
