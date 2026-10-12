"""Recompute explicit checks without editing source runs or claiming human quality."""
import argparse
import copy
import json
from pathlib import Path

import runner

VERSION='2026-09-23.unicode-hyphen'


def rescore(source, output):
    source=Path(source)
    output=Path(output)
    if output.exists():
        raise ValueError('Use a new output path; original checks must remain available')
    raw=source.read_bytes()
    run=json.loads(raw)
    suite, digest=runner.checked_suite(source.parent/'cases.frozen.json')
    if digest != run['manifest']['suite_sha256']:
        raise ValueError('Frozen cases do not match this run')
    lookup={c['id']:c for c in suite['cases']}
    changes=[]
    scored=copy.deepcopy(run)
    for sample in scored['samples']:
        sample['checks']=[]
        steps=lookup[sample['case_id']]['turns']
        for turn in sample['turns']:
            expected=steps[int(turn['turn_id'])-1].get('expect',{})
            before=turn['checks']
            checks=runner.objective_checks(expected,turn['text'],turn['tools'],turn['state_before'],turn['state_after'])
            # Runtime capture failures are independent of text assertion code.
            checks += [c for c in before if c['name']=='event_capture']
            turn['original_checks']=before
            turn['checks']=checks
            sample['checks'].extend({**c,'name':turn['turn_id']+':'+c['name']} for c in checks)
            if checks != before:
                changes.append({'case_id':sample['case_id'],'repeat':sample['repeat'],'turn_id':turn['turn_id'],'before':before,'after':checks})
    scorer=(runner.HERE/'runner.py').read_bytes()
    scored['manifest']['regrading']={'version':VERSION,'parent_run_sha256':runner.sha(raw),'scorer_sha256':runner.sha(scorer),
        'note':'Normalize hyphen, nonbreaking hyphen and whitespace in literal spoken-word checks. Preserve all tool requirements, events and original checks. This is a derived scoring record, not a new model run.'}
    scored['scoring_changes']=changes
    runner.save(output,scored)
    output.with_suffix('.scorer.py').write_bytes(scorer)
    return changes


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(rescore(args.run,args.output),indent=2))
