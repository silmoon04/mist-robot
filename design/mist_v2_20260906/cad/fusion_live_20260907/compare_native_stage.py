"""Compare executed native bodies with their exact frozen offline recipes."""
import argparse
import hashlib
import json
from pathlib import Path


def compare(stage,reference,output):
    report=json.loads(reference.read_text())
    request=json.loads((stage/'request.json').read_text())
    leg=request['leg']
    frozen=json.loads((stage/'recipes_frozen.json').read_text())[leg]
    old={part['name']:part for part in report['specifications'][leg]['parts']}
    rows={part['name']:part for part in report['parts'] if part['group']==leg}
    native={part['name']:part for part in json.loads((stage/'geometry.json').read_text())}
    checks=[]
    for part in frozen['parts']:
        name=part['name']
        if part!=old.get(name):
            raise ValueError('The reference recipe differs from the native input: '+name)
        actual=native[name]
        expected=rows[name]
        bbox=max(abs(a-b) for r,s in zip(actual['bounds_world_mm'],expected['bounds_hipplane_mm']) for a,b in zip(r,s))
        volume=expected['volume_cm3']*1000
        volume_error=abs(actual['volume_mm3']-volume)
        supplier=any(op['kind']=='step_reference' for op in part['ops'])
        checks.append({'name':name,'bbox_max_error_mm':bbox,'volume_error_mm3':volume_error,
                       'volume_relative_error':volume_error/volume,'supplier_step':supplier,
                       'passed':actual['solid'] and bbox<=0.02 and
                                (volume_error<=max(.05,volume*.0005) if not supplier else False)})
    result={'stage':str(stage),'reference':str(reference),
            'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),
            'bbox_tolerance_mm':.02,'relative_volume_tolerance':.0005,'absolute_volume_floor_mm3':.05,
            'passed':all(row['passed'] for row in checks),'checked_parts':len(checks),
            'max_bbox_error_mm':max(row['bbox_max_error_mm'] for row in checks),
            'max_relative_volume_error':max(row['volume_relative_error'] for row in checks),
            'checks':checks,'scope':'One-pose bounds and integrated volume correspondence; not shape identity, motion or strength.'}
    output.write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',type=Path,required=True)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=compare(args.stage,args.reference,args.output)
    raise SystemExit(0 if result['passed'] else 1)
