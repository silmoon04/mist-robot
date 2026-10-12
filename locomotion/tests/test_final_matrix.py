import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pytest
from final_matrix import json_native,worker
from provenance import source_hashes


def test_receipt_numpy_values_do_not_change_boolean_scores():
    item={'passed':np.bool_(False),'checks':{'progress':np.bool_(True)},'a':np.array([1.,2.])}
    restored=json.loads(json.dumps(item,allow_nan=False,default=json_native))
    assert restored=={'passed':False,'checks':{'progress':True},'a':[1.,2.]}
    with pytest.raises(TypeError):json.dumps({'unknown':object()},default=json_native)


def test_real_probe_receipt_serializes_and_cannot_qualify():
    case={'case_id':'two-step-probe','status':'ready','command_name':'stop','seed':6000000001,
          'env_kwargs':{'command':[0,0,0],'terrain':'flat','payload':.155,'sensor_mode':'mpu6050','randomize':False}}
    row=worker((case,2,None,'ppo',source_hashes()))
    restored=json.loads(json.dumps(row,allow_nan=False,default=json_native))
    assert restored['passed'] is False
    assert restored['checks']['duration'] is False
