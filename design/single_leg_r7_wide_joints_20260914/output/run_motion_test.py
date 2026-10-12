"""Run restrained, unloaded articulation and check gravity against potential energy."""
from pathlib import Path
import json,math,hashlib
import numpy as np
import pybullet as p
ROOT=Path(__file__).resolve().parent;OUT=ROOT

def main():
    p.connect(p.DIRECT);p.setGravity(0,0,-9.81);p.setTimeStep(1/240)
    robot=p.loadURDF(str(OUT/'Single_Leg_R7.urdf'),useFixedBase=True,flags=p.URDF_USE_INERTIA_FROM_FILE)
    assert p.getNumJoints(robot)==3
    q0=np.radians([0,30,81]);properties=json.loads((OUT/'urdf_properties.json').read_text())
    def setq(q):
        for j,x in enumerate(q):p.resetJointState(robot,j,float(x))
    def potential(q):
        setq(q)
        return sum(row['mass_kg']*9.81*p.getLinkState(robot,i,computeForwardKinematics=True)[0][2] for i,row in enumerate(properties['links'][1:]))
    epsilon=1e-5;finite=[]
    for i in range(3):
        delta=np.zeros(3);delta[i]=epsilon;finite.append((potential(q0+delta)-potential(q0-delta))/(2*epsilon))
    analytical=p.calculateInverseDynamics(robot,q0.tolist(),[0]*3,[0]*3)
    gravity_error=float(np.max(np.abs(np.array(finite)-analytical)));assert gravity_error<1e-5
    setq(q0);rows=[]
    for step in range(240*36):
        t=step/240;s=max(0,t-2);phase=(s-2+(s+2)*math.exp(-s))*2*math.pi/14
        centre=np.radians([0,17.5,60]);amplitude=np.radians([50,42.5,50]);offset=np.arcsin((q0-centre)/amplitude)
        target=centre+amplitude*np.sin(phase+offset)
        p.setJointMotorControlArray(robot,[0,1,2],p.POSITION_CONTROL,targetPositions=target.tolist(),forces=[.8]*3,positionGains=[.15]*3,velocityGains=[1]*3)
        p.stepSimulation()
        if step%8==0:
            states=p.getJointStates(robot,[0,1,2]);rows.append({'time_s':t,'target_rad':target.tolist(),'position_rad':[s[0] for s in states],'torque_Nm':[s[3] for s in states]})
    settled=[r for r in rows if r['time_s']>=2]
    error=max(max(abs(a-b) for a,b in zip(r['target_rad'],r['position_rad'])) for r in settled)
    torque=np.max(np.abs(np.array([r['torque_Nm'] for r in settled])),axis=0)
    report={'status':'pass' if error<.02 and float(torque.max())<.8 else 'fail',
        'urdf_sha256':hashlib.sha256((OUT/'Single_Leg_R7.urdf').read_bytes()).hexdigest(),
        'duration_s':36,'motion_profile':'Sinusoidal joint targets with continuous position, velocity and acceleration at startup; ideal position motors track them. This is not the physical servo firmware profile.','max_settled_tracking_error_deg':math.degrees(error),'peak_settled_joint_torque_Nm':torque.tolist(),
        'neutral_gravity_torque_Nm':list(analytical),'independent_potential_energy_derivative_Nm':finite,'gravity_check_max_error_Nm':gravity_error,
        'samples':rows,'scope':'Restrained unloaded single leg in gravity. Uniform full-solid link masses, ideal torque-limited position motors. No ground contact, motor heating, real backlash, layer fracture or full-robot balance validation.'}
    (OUT/'motion_test.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='samples'});p.disconnect()

if __name__=='__main__':main()
