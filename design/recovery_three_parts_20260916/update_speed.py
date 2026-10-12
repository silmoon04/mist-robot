"""Revise supported deposition speeds without changing recovery geometry."""
from pathlib import Path
import sys,json,zipfile,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'third_leg_20260916'))
import compare_speed as c,prepare_plate as profile_tools
c.ROOT=ROOT
OUT=ROOT/'balanced_profile';OUT.mkdir(exist_ok=True);profile_tools.OUT=OUT
old=json.loads((ROOT/'print/Print_Check.json').read_text())
settings=dict(old['result']['settings'])
settings.update(speed_print=90,speed_wall=65,speed_wall_0=50,speed_wall_x=90,
 speed_infill=90,speed_topbottom=60,material_max_flowrate=11,
 material_print_temperature=215,material_initial_print_temperature=215,material_final_print_temperature=215,
 wall_overhang_speed_factors='[20, 16.6667, 13.3333]')
# Preserve first-layer temperature, adhesion, travel, acceleration, cooling,
# wall count, infill density, layer heights and support geometry/settings.
changes={k:{'before':old['result']['settings'][k],'after':v} for k,v in settings.items() if old['result']['settings'][k]!=v}
for k,v in old['result']['settings'].items():
 if k.startswith(('acceleration','support','brim','bridge','cool','retraction')) or 'layer_0' in k:
  assert settings[k]==v,k
profile=profile_tools.profile(settings,'Neptune4Pro_Recovery_Balanced_028')
plate=ROOT/'print/Recovery_Three_Parts_With_Supports.stl'
result=c.run('recovery_balanced',plate,settings)
assert result['engine']['motion_inside_build_envelope'] and result['deposition']['unclassified_deposition_is_zero']
lo,hi=np.array(result['engine']['motion_bounds_mm']);assert min(lo[:2].min(),(225-hi[:2]).min())>2
before=old['result']['engine']['estimated_time_seconds'];after=result['engine']['estimated_time_seconds']
report={'profile_file':profile,'profile_sha256':profile_tools.sha(OUT/profile),'plate_sha256':profile_tools.sha(plate),
 'before_seconds':before,'after_seconds':after,'saved_minutes':(before-after)/60,'saved_percent':100*(1-after/before),
 'changes':changes,'result':result,'limits':'Slicer estimate only. The 11 mm3/s process is not physically qualified on this filament. Recovery adhesion, supports and low acceleration retained.'}
(OUT/'Profile_Check.json').write_text(json.dumps(report,indent=2))
print('SAVED_MINUTES',(before-after)/60,flush=True)
