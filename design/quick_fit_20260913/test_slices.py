"""Time the revised jobs and the full original plate with identical settings."""
from concurrent.futures import ThreadPoolExecutor
import argparse
from pathlib import Path
import gzip
import json
import sys
import hashlib
from build_quick_fit import HERE,DESIGN,VALUES,GROUPS

sys.path.insert(0,str(DESIGN/'manufacturing/slicing_r5'))
from engine_runner import slice_one
from deposition_properties import parse_gcode


def run(name,path,values):
    folder=HERE/'analysis'/name
    r=slice_one(path,folder,name,values)
    raw=Path(r['raw_temporary_path']);text=raw.read_text(encoding='utf-8')
    parsed=parse_gcode(text,r['gcode_to_source_transform'],layer_height_mm=values['layer_height'])
    peak=max(p.get('peak_nominal_deposition_flow_mm3_s',0) for p in parsed['properties'].values())
    disabled='; ANALYSIS ONLY. DO NOT PRINT.\n'+'\n'.join(
        line if not line.strip() or line.lstrip().startswith(';') else '; DISABLED| '+line for line in text.splitlines())
    inert=folder/(name+'.ANALYSIS_ONLY.gcode.gz');inert.write_bytes(gzip.compress(disabled.encode()))
    assert raw.resolve().parent==folder.resolve();raw.unlink()
    result={'name':name,'estimated_hours':r['estimated_time_seconds']/3600,
        'model_g':parsed['properties']['model']['mass_g'],
        'support_g':parsed['properties']['support']['mass_g'],
        'adhesion_g':parsed['properties']['adhesion']['mass_g'],
        'peak_nominal_flow_mm3_s':peak,'motion_bounds_mm':r['motion_bounds_mm'],
        'within_bed':r['motion_inside_build_envelope'],'source_stl_sha256':r['source_sha256'],
        'layer_height_mm':values['layer_height'],'engine_version':r['engine_version'],
        'all_deposition_classified':parsed['unclassified_deposition_is_zero'],
        'analysis_archive_sha256':hashlib.sha256(inert.read_bytes()).hexdigest()}
    (folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--benchmark-full-plate',action='store_true')
    args=parser.parse_args()
    jobs=[(name,HERE/(name+'.stl'),dict(VALUES)) for name in GROUPS]
    if args.benchmark_full_plate:
        jobs.append(('original_full_plate_020',DESIGN/'printing/coupon_plate_01.stl',dict(VALUES)))
        coarse=dict(VALUES,layer_height=.3,infill_sparse_thickness=.3,top_layers=4,bottom_layers=4,
            support_z_distance=.3,support_top_distance=.3,support_bottom_distance=.3,
            speed_print=60,speed_wall=50,speed_wall_x=60,speed_infill=60,speed_support=50,speed_support_infill=50)
        jobs.append(('original_full_plate_030',DESIGN/'printing/coupon_plate_01.stl',coarse))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda j:run(*j),jobs))
    (HERE/'slice_comparison.json').write_text(json.dumps({'results':results,
        'method':'CuraEngine process overrides on the explicit numeric analysis stack. Live Cura and the physical printer can differ.',
        'machine_code_delivered':False},indent=2),encoding='utf-8')
