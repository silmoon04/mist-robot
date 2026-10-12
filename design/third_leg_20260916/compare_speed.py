"""Compare process changes on the exact previously printed eight-part plate."""
from pathlib import Path
import sys, json, gzip, importlib.util, concurrent.futures

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent
OLD = PROJECT / 'design/print_dfm_20260914'
sys.path.insert(0, str(OLD))
import prepare_prints as p

# Keep the historical 8 mm3/s runner immutable. This local runner explicitly
# permits a candidate 11 mm3/s process; extrusion quality remains unmeasured.
source = PROJECT / 'design/hexapod_phone_quad_r5_20260912/manufacturing/slicing_r5/engine_runner.py'
code = source.read_text().replace("BASE_PROFILE = Path(__file__).resolve().parents[1] / 'orientation/slicer/resolved_analysis.def.json'", "BASE_PROFILE = Path(" + repr(str(source.parent.parent / 'orientation/slicer/resolved_analysis.def.json')) + ")")
code = code.replace("<= 8:", "<= 11:").replace('no greater than 8 mm3/s.', 'no greater than 11 mm3/s.')
(ROOT / 'engine_runner_candidate.py').write_text(code)
spec = importlib.util.spec_from_file_location('candidate_runner', ROOT / 'engine_runner_candidate.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

def settings(fast=True):
    s = p.profile(True)
    s.update(support_xy_distance=4.3)
    if fast:
        s.update(material_max_flowrate=11, speed_print=90, speed_wall=65,
                 speed_wall_0=50, speed_wall_x=90, speed_infill=90,
                 speed_topbottom=50, speed_travel=190,
                 adhesion_type='skirt', skirt_gap=3, skirt_line_count=2,
                 material_print_temperature=215, material_print_temperature_layer_0=210,
                 material_initial_print_temperature=215, material_final_print_temperature=215)
    return s

def run(name, source, s):
    e = runner.slice_one(source, ROOT / 'analysis', name, s)
    raw = Path(e['raw_temporary_path'])
    text = raw.read_text()
    d = p.parse_gcode(text, e['gcode_to_source_transform'], layer_height_mm=s['layer_height'])
    archive = raw.with_name(name + '.analysis_only.gcode.gz')
    with gzip.open(archive, 'wt') as f:
        f.writelines(line if line.startswith(';') else '; DISABLED ' + line for line in text.splitlines(keepends=True))
    raw.unlink()
    e['raw_file_disposition'] = 'Commands disabled, compressed, temporary raw file removed.'
    r = {'engine': e, 'deposition': d, 'settings': s}
    (ROOT / 'analysis' / (name + '.json')).write_text(json.dumps(r, indent=2))
    print(name, 'hours', e['estimated_time_seconds']/3600, 'grams', d['total_deposited_mass_g'], flush=True)
    return r

if __name__ == '__main__':
    run('old_eight_fast', OLD / 'print/R7_DFM_Overnight.stl', settings())
