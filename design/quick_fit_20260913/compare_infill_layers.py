"""Compare material and time for the unchanged first saddle-and-cap plate."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import math
import sys
from build_quick_fit import HERE,VALUES
import test_slices

OUT=HERE/'infill_layer_options'


def variants():
    result={
        '020_5walls_15infill':dict(VALUES,infill_sparse_density=15),
        '020_6walls_10infill':dict(VALUES,infill_sparse_density=10,
            wall_line_count=6,wall_thickness=2.52),
    }
    for h,speed in ((.28,65),(.3,60)):
        v=dict(VALUES,layer_height=h,infill_sparse_thickness=h,infill_sparse_density=15,
            speed_print=speed,speed_wall=50,speed_wall_0=45,speed_wall_x=speed,
            speed_infill=speed,speed_support=50,speed_support_infill=50,
            speed_topbottom=35,support_z_distance=h,support_top_distance=h,
            support_bottom_distance=h)
        count=math.ceil(1.2/h-1e-9)
        v.update(top_layers=count,bottom_layers=count,top_thickness=count*h,
            bottom_thickness=count*h,top_bottom_thickness=count*h,
            support_roof_height=math.ceil(.6/h-1e-9)*h,
            support_interface_height=math.ceil(.6/h-1e-9)*h)
        result[f'{round(h*100):03}_5walls_15infill']=v
    return result


def main():
    OUT.mkdir(exist_ok=True)
    test_slices.HERE=OUT
    cases=variants()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda kv:test_slices.run(kv[0],HERE/'01_servo_case_fit.stl',kv[1]),cases.items()))
    for row in results:
        row['wall_count']=cases[row['name']]['wall_line_count']
        row['infill_percent']=cases[row['name']]['infill_sparse_density']
        row['settings']=cases[row['name']]
    baseline=json.loads((HERE/'slice_comparison.json').read_text())['results'][0]
    report={'source':'Unchanged R5 first servo saddle and cap. This comparison is for fit screening.',
        'baseline_020_5walls_35infill':baseline,'cases':results,
        'limits':['Slicer estimates, not physical print times or measured strength.',
            'Higher layers change supported surfaces and vertical feature approximation.',
            'Changing infill or layer height does not preserve the previous structural process qualification.']}
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert all(p['within_bed'] and p['peak_nominal_flow_mm3_s']<=8.1 for p in results)


if __name__=='__main__':main()
