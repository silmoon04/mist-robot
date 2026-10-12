"""Check the actual second-plate toolpath without sending it to a printer."""
from pathlib import Path
import gzip
import hashlib
import json
import math
import re
import sys

HERE=Path(__file__).resolve().parent
DESIGN=HERE.parent/'hexapod_phone_quad_r5_20260912'
sys.path.insert(0,str(DESIGN/'manufacturing/slicing_r5'))
from engine_runner import slice_one
from deposition_properties import parse_gcode


def feed_samples(text):
    """Read deposition speeds at known roof layers, without changing the path."""
    xyz=[0.,0.,0.];e=0.;feed=0.;kind='';rows=[]
    for line in text.splitlines():
        if line.startswith(';TYPE:'):kind=line[6:]
        code=line.split(';')[0].strip()
        fields={k:float(v) for k,v in re.findall(r'([XYZEF])(-?[\d.]+)',code)}
        op=code.split(' ')[0]
        if op=='G92':e=fields.get('E',e);continue
        if op not in ('G0','G1'):continue
        target=[fields.get(k,xyz[i]) for i,k in enumerate('XYZ')]
        newe=fields.get('E',e);feed=fields.get('F',feed)
        if newe>e and math.dist(target,xyz)>.01 and kind.startswith('WALL'):
            mid=[(a+b)/2 for a,b in zip(xyz,target)]
            rows.append({'mid':mid,'speed_mm_s':feed/60,'length_mm':math.dist(target,xyz),'type':kind})
        xyz=target;e=newe
    return rows


def main():
    path=HERE/'second_fit_validation.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    values=data['profile']['settings']
    run=slice_one(HERE/data['plate']['stl'],HERE/'analysis','second_full_clamp',values)
    raw=Path(run['raw_temporary_path']);text=raw.read_text(encoding='utf-8')
    parsed=parse_gcode(text,run['gcode_to_source_transform'],layer_height_mm=.28)
    rows=feed_samples(text)
    # The saddle occupies the left side. Roof bands include both screw and
    # nut closures, in the unchanged supplied print orientation.
    slow=[p for p in rows if p['mid'][0]<110 and p['mid'][2]>8 and p['speed_mm_s']<=20]
    support=parsed['properties']['support']['mass_g']
    peak=max(p.get('peak_nominal_deposition_flow_mm3_s',0) for p in parsed['properties'].values())
    assert support==0
    assert run['motion_inside_build_envelope']
    assert parsed['unclassified_deposition_is_zero']
    assert slow,'No slow wall segments found in the saddle region'
    disabled='; ANALYSIS ONLY. ALL MACHINE COMMANDS DISABLED. DO NOT PRINT.\n'
    disabled+='\n'.join(line if not line.strip() or line.lstrip().startswith(';') else '; DISABLED| '+line for line in text.splitlines())
    archive=HERE/'analysis/second_full_clamp.ANALYSIS_ONLY.gcode.gz'
    archive.write_bytes(gzip.compress(disabled.encode('utf-8')))
    assert raw.resolve().parent==(HERE/'analysis').resolve();raw.unlink()
    data['slice_trial']={'engine_version':run['engine_version'],'return_code':run['return_code'],
        'source_stl_sha256':run['source_sha256'],'model_PLA_g':parsed['properties']['model']['mass_g'],
        'support_PLA_g':support,'adhesion_PLA_g':parsed['properties']['adhesion']['mass_g'],
        'estimated_hours':run['estimated_time_seconds']/3600,'peak_nominal_flow_mm3_s':peak,
        'motion_bounds_mm':run['motion_bounds_mm'],'within_225mm_bed':True,
        'saddle_slow_wall_segments_at_or_below20_mm_s':len(slow),
        'saddle_slow_wall_length_mm':sum(p['length_mm'] for p in slow),
        'settings_overrides':values,'analysis_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'method':'Profile process values on the explicit numeric CuraEngine analysis stack; no live frontend import or hardware test.'}
    path.write_text(json.dumps(data,indent=2),encoding='utf-8')
    (HERE/'analysis/slice_run.json').write_text(json.dumps(run,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in data['slice_trial'].items() if k!='settings_overrides'},indent=2))
    assert peak<8.1
    assert run['estimated_time_seconds']/3600<=3


if __name__=='__main__':main()
