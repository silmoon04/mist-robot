"""Auditable ideal constraints for the body-remote architecture study.

These are conditional mechanism contracts, not fitted geometry or controllers.
Rows of A are motor coordinates; columns are q0, hip, knee, wheel. Gear signs
are explicitly chosen for each proposed physical route. Losses are excluded.
"""
from pathlib import Path
import json
import numpy as np

def contracts():
    ratios=np.diag([2.,2.,2.,1.])
    models={
        'strict_independent_pickups':dict(
            A=ratios@np.array([[1,0,0,0],[1,1,0,0],[1,1,1,0],[1,1,1,1]],float),
            assumption='Three1:1 carrier-relative bevel pickups; beta=alpha-q0. Actual signs and offsets must be embodied.'),
        'internal_three_motor_plate':dict(
            A=ratios@np.array([[1,0,0,0],[0,1,0,0],[0,1,1,0],[0,1,1,1]],float),
            assumption='H/K/W housings rotate with the fully enclosed first-joint plate; equal open belts.'),
        'internal_HK_fixed_W_hybrid':dict(
            A=ratios@np.array([[1,0,0,0],[0,1,0,0],[0,1,1,0],[1,1,1,1]],float),
            assumption='Only the fixed-body continuous wheel channel crosses first joint through1:1 pickup.'),
        'internal_pitch_differential_hybrid':dict(
            A=ratios@np.array([[1,0,0,0],[0,1,1,0],[0,1,-1,0],[1,1,1,1]],float),
            assumption='Equal side gears; carrier drives h; sideA drives absolute tibia via1:1 belt; fixed-body wheel feed.'),
    }
    paper_R=np.array([[.5,-.5,0,0],[.25,.25,0,0],[0,-.5,.5,0],[0,0,-.5,.5]])
    models['strict_spatial_typeI_duplicate_wheel']=dict(
        A=np.linalg.inv(paper_R),
        assumption='Published TypeI first3rows at[1,1,2,2]; fourth row is OUR proposed identical independent A2 transport for wheel. No extra motor reduction implied.',
        source='https://doi.org/10.1109/TRO.2025.3543262',
        continuous_wheel_note='Literal duplicated2:1 route halves wheel speed; a different real ratio or speed-up needs a new contract.')
    return models

def validate_and_export(output=None):
    rng=np.random.default_rng(2709)
    result={}
    for name,item in contracts().items():
        A=item['A'];R=np.linalg.inv(A)
        assert np.linalg.matrix_rank(A)==4
        max_error=0.
        for _ in range(100):
            qdot=rng.normal(size=4);tau=rng.normal(size=4)
            mdot=A@qdot;mu=np.linalg.solve(A.T,tau)
            error=abs(float(tau@qdot-mu@mdot))
            max_error=max(max_error,error)
            assert error<1e-11
        result[name]={k:v for k,v in item.items() if k!='A'}
        result[name].update(joint_order=['q0','hip','knee','wheel'],A_motor_from_joint=A.tolist(),
                            R_joint_from_motor=R.tolist(),motor_torque_from_joint=np.linalg.inv(A.T).tolist(),
                            virtual_work_test_max_error=max_error,
                            validation='Algebra and ideal power only; no physical packaging or performance assertion')
        result[name]['motor_order']=(['a0','a1','a2','a3'] if name.startswith('strict_spatial') else
                                     ['mY','mA','mB','mW'] if name=='internal_pitch_differential_hybrid' else
                                     ['mY','mH','mK','mW'])
        result[name]['first_axis_scope']=('Abduction/adduction in the source paper; yaw reorientation is not verified here.'
                                          if name.startswith('strict_spatial') else
                                          'First-axis carrier with the stated ideal pickup signs; yaw/roll geometry must be chosen explicitly.')
    record=dict(status='preliminary_conditional_mechanism_contracts',models=result)
    path=Path(output or Path(__file__).with_name('coupling_contracts.json'))
    path.write_text(json.dumps(record,indent=2))
    return record

if __name__=='__main__':
    record=validate_and_export()
    print(json.dumps({name:row['virtual_work_test_max_error'] for name,row in record['models'].items()},indent=2))
