"""Compare conservative and modestly faster hub profiles with actual Cura slices."""
from pathlib import Path
import sys,json,zipfile,gzip,hashlib,configparser,concurrent.futures
import numpy as np,trimesh
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'
sys.path.insert(0,str(ROOT.parent/'single_leg_r7_wide_joints_20260914'))
import prepare_prints as helper
from engine_runner import slice_one
from deposition_properties import parse_gcode
from pack_prints import three_mf

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def settings(faster=False):
    v=helper.profile(False)
    v.update(adhesion_type='brim',brim_width=3,brim_line_count=8,brim_gap=.15,support_enable=False,
        support_interface_enable=False,support_roof_enable=False,support_brim_enable=False,brim_location='outside')
    if faster:v.update(speed_wall_0=46,speed_topbottom=46,speed_travel=175)
    return v

def profile():
    v=settings(True);helper.pt.NAME='Main hub PLA 0.28 balanced speed';schema=helper.pt.flatten(json.loads((helper.pt.CURA/'share/cura/resources/definitions/fdmprinter.def.json').read_text())['settings'])
    gv={};ev={}
    for k,value in v.items():
        entry=schema[k]
        if entry['type']=='enum':assert value in entry['options'],(k,value)
        (ev if entry.get('settable_per_extruder',True) else gv)[k]=value
    path=OUT/'Neptune4Pro_Hub_PLA_028.curaprofile'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('hub_global',helper.pt.serialize(gv,False));z.writestr('hub_extruder_0',helper.pt.serialize(ev,True))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None;merged={}
        for n in z.namelist():
            c=configparser.ConfigParser(interpolation=None);c.read_string(z.read(n).decode());merged.update(c['values'])
        assert merged=={k:str(value) for k,value in v.items()}
    return path

def run_slice(stl,name,faster):
    r=slice_one(stl,ROOT/'analysis',name,settings(faster));raw=Path(r['raw_temporary_path']);txt=raw.read_text();d=parse_gcode(txt,r['gcode_to_source_transform'],layer_height_mm=.28)
    assert d['unclassified_deposition_is_zero'] and d['properties']['support']['mass_g']==0
    assert d['properties']['model']['peak_nominal_deposition_flow_mm3_s']<8.1
    with gzip.open(ROOT/'analysis'/(name+'.analysis_only.gcode.gz'),'wt') as f:f.writelines(line if line.startswith(';') else '; DISABLED '+line for line in txt.splitlines(keepends=True))
    raw.unlink();r['raw_file_disposition']='Consumed for analysis, all commands disabled, compressed, raw temporary removed.'
    result={'engine':r,'deposition':d};print(name,r['estimated_time_seconds']/3600,d['total_deposited_mass_g'],flush=True);return result

def main():
    profile()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        values=list(pool.map(lambda fast:run_slice(OUT/'Main_Hub_4Leg.stl','hub_fast' if fast else 'hub_baseline',fast),[False,True]))
    data={'baseline':values[0],'faster':values[1],'time_reduction_percent':100*(1-values[1]['engine']['estimated_time_seconds']/values[0]['engine']['estimated_time_seconds']),
        'changes':'Outer walls and top/bottom surfaces increase from40 to46mm/s. Travel150 to175mm/s. Inner walls and infill stay65mm/s to retain the8mm3/s flow envelope. First layer, bridges, cooling and acceleration remain unchanged.'}
    (OUT/'Speed_Comparison.json').write_text(json.dumps(data,indent=2));print('time reduction',data['time_reduction_percent'])

if __name__=='__main__':main()
