"""Run a temporary, non-machine-ready first-plate trial with the profile values."""
from pathlib import Path
import json
import sys
from build_profile import HERE,VALUES

DESIGN=HERE.parent/'hexapod_phone_quad_r5_20260912'
sys.path.insert(0,str(DESIGN/'manufacturing/slicing_r5'))
from engine_runner import slice_one

if __name__=='__main__':
    result=slice_one(DESIGN/'printing/coupon_plate_01.stl',HERE/'analysis','first_plate',VALUES)
    (HERE/'analysis/slice_run.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    from verify_profile import main
    main()
