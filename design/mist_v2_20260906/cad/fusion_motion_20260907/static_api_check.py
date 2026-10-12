"""Read installed Autodesk declarations without importing its native DLLs."""
from pathlib import Path
import ast
import hashlib
import json

DEFAULT = Path('<LOCAL_HOME>/AppData/Local/Autodesk/webdeploy/production/61bf25b220a2d0307c84c301e65a59ac225d9a1e/API/Python/packages/adsk/defs/adsk')
REQUIRED = {
    'Component': {'allOccurrencesByComponent':['self','component'], 'asBuiltJoints':None, 'rigidGroups':None,
                  'constructionPlanes':None, 'sketches':None, 'xYConstructionPlane':None, 'xZConstructionPlane':None,
                  'yZConstructionPlane':None},
    'RigidGroups': {'add':['self','occurrences','includeChildren']},
    'AsBuiltJoints': {'createInput':['self','occurrenceOne','occurrenceTwo','geometry'], 'add':['self','input']},
    'AsBuiltJointInput': {'setAsRevoluteJointMotion':['self','rotationAxis','customRotationAxisEntity'], 'setAsRigidJointMotion':['self']},
    'AsBuiltJoint': {'jointMotion':None,'name':None,'isSuppressed':None},
    'JointGeometry': {'createByPoint':['point']},
    'RevoluteJointMotion': {'cast':['arg'],'rotationValue':None,'rotationLimits':None,'rotationAxisVector':None},
    'JointLimits': {'minimumValue':None,'maximumValue':None,'isMinimumValueEnabled':None,'isMaximumValueEnabled':None,'isRestValueEnabled':None},
    'Occurrence': {'transform2':None,'assemblyContext':None,'sourceComponent':None,'isGrounded':None,'isGroundToParent':None},
    'ConstructionPlanes': {'createInput':['self','occurrenceForCreation'],'add':['self','input']},
    'ConstructionPlaneInput': {'setByOffset':['self','planarEntity','offset']},
    'ConstructionPlane': {'geometry':None,'isLightBulbOn':None},
    'Sketches': {'add':['self','planarEntity','occurrenceForCreation']},
    'Sketch': {'modelToSketchSpace':['self','modelCoordinate'],'geometricConstraints':None,'sketchCurves':None,'sketchPoints':None,'isLightBulbOn':None},
    'SketchPoints': {'add':['self','point']},
    'SketchLines': {'addByTwoPoints':['self','startPoint','endPoint']},
    'SketchLine': {'createForAssemblyContext':['self','occurrence'],'startSketchPoint':None},
    'SketchPoint': {'createForAssemblyContext':['self','occurrence']},
    'SketchEntity': {'isFixed':None},
    'Design': {'computeAll':['self'],'rootComponent':None,'designType':None},
}


def check(directory=DEFAULT):
    path=Path(directory)/'fusion.py'
    raw=path.read_bytes();tree=ast.parse(raw)
    classes={node.name:node for node in tree.body if isinstance(node,ast.ClassDef)}
    def definitions_for(name):
        node=classes.get(name)
        if node is None:return {}
        definitions={}
        for base in node.bases:
            if isinstance(base,ast.Name):definitions.update(definitions_for(base.id))
        definitions.update({f.name:f for f in node.body if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef))})
        return definitions
    checks=[]
    for cls,members in REQUIRED.items():
        definitions=definitions_for(cls)
        for member,args in members.items():
            fn=definitions.get(member)
            actual=None if fn is None else [a.arg for a in fn.args.args]
            # Properties have separate getter/setter AST definitions; membership
            # is checked here while mutation semantics remain a native test.
            okay=fn is not None and (args is None or actual==args)
            checks.append(dict(api=cls+'.'+member,passed=okay,expected_args=args,actual_args=actual))
    result=dict(scope='Installed primary declaration/signature check only; no Autodesk native DLL imported or Fusion API executed.',
                native_execution=False,source=str(path),source_sha256=hashlib.sha256(raw).hexdigest(),
                passed=all(c['passed'] for c in checks),checked_members=len(checks),checks=checks)
    return result


if __name__=='__main__':
    result=check()
    destination=Path(__file__).with_name('static_api_check.json')
    destination.write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
    for c in result['checks']:
        if not c['passed']:print(json.dumps(c))
    raise SystemExit(0 if result['passed'] else 1)
