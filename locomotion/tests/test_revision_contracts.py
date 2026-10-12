import copy
import json
import math
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
from locomotion import provenance as prov
from locomotion.model import load_config,export_models,validate_config
from locomotion.servo import ServoBank
from locomotion.mist_env import MistEnv
from locomotion.hardware.bridge import Bridge,InterlockError,TICKS_PER_RAD
from locomotion.hardware.sensors import BodyIMU,SensorError,G
from locomotion.acceptance import score


def test_checkpoint_and_replay_hash_contract(tmp_path):
    ck=tmp_path/'policy.zip';ck.write_bytes(b'policy');replay=tmp_path/'replay';replay.write_bytes(b'replay')
    env=prov.envelope({'sensor':{'mode':'none','profile':None}})
    prov.bind_checkpoint(ck,env,'sac','smoke',replay,1042)
    assert prov.verify_checkpoint(ck,'sac',replay=replay)['continuation_seed']==1042
    with pytest.raises(ValueError):prov.verify_checkpoint(ck,'ppo')
    with pytest.raises(ValueError):prov.verify_checkpoint(ck,'sac',sensor_mode='phone')
    with pytest.raises(ValueError):prov.verify_checkpoint(ck,'sac',expected_experiment={'changed':True})
    replay.write_bytes(b'changed')
    with pytest.raises(ValueError):prov.verify_checkpoint(ck,'sac',replay=replay)
    ck.write_bytes(b'changed')
    with pytest.raises(ValueError):prov.verify_checkpoint(ck)


def test_required_sources_fail_closed_and_mutation_detected(tmp_path,monkeypatch):
    expected=prov.source_hashes()
    for name in ('hardware/sensors.py','sensor_sim.py','config.json','requirements.lock.txt','profiles/r7_direct.json','validation_cases.json'):
        assert 'locomotion/'+name in expected
    original=prov.digest
    key=next(k for k in expected if k.endswith('.stl'))
    monkeypatch.setattr(prov,'digest',lambda p:'0'*64 if str(p).endswith(key) else original(p))
    with pytest.raises(RuntimeError):prov.check_sources(expected)
    monkeypatch.setattr(prov,'REQUIRED',prov.REQUIRED+('missing_required.py',))
    with pytest.raises(FileNotFoundError):prov.source_hashes()


def test_config_reaches_servo_and_restitution():
    cfg=load_config();cfg['randomization'].update(voltage_v=[10.,10.],kp_scale=[1.5,1.5],deadband_deg=[1.,1.]);cfg['actuator']['thermal_proxy'].update(ambient_c=31.,heating_c_s_at_rated_torque=5.,cooling_s_inv=.1);cfg['simulation']['contact_restitution']=.4
    b=ServoBank(np.zeros(12),np.random.default_rng(1),config=cfg)
    assert b.voltage==10 and np.all(b.temperature==31)
    np.testing.assert_allclose(b.kp,np.tile(cfg['actuator']['kp_nm_rad'],4)*1.5)
    np.testing.assert_allclose(b.deadband,np.radians(1))
    env=MistEnv(config=cfg,randomize=False,payload=0)
    try:
        env.reset(seed=1)
        import pybullet as p
        assert env._call(p.getDynamicsInfo,env.robot,-1)[5]==.4
    finally:env.close()
    cfg['simulation']['physics_hz']=999
    with pytest.raises(ValueError):validate_config(cfg)


def test_source_rotation_and_coordinated_tibia_rejected(tmp_path):
    cfg=load_config();src=prov.REPO/cfg['sources']['leg_urdf'];dest=tmp_path/'source.urdf';dest.write_text(src.read_text().replace('rpy="0 0 0"','rpy=".2 0 0"',1));cfg['sources']['leg_urdf']=str(dest)
    with pytest.raises(ValueError):export_models(tmp_path/'model',config=cfg)
    cfg=load_config();manifest=json.loads((prov.REPO/cfg['sources']['leg_manifest']).read_text());manifest['lengths_mm'][2]=140;dest=tmp_path/'manifest.json';dest.write_text(json.dumps(manifest));cfg['sources']['leg_manifest']=str(dest);cfg['geometry']['tibia_m']=.14
    with pytest.raises(ValueError):export_models(tmp_path/'model',config=cfg)
    assert not (tmp_path/'model').exists()


def test_stop_invalidates_delayed_arm_and_clear():
    b=Bridge()
    try:
        old=b.intent_generation;b.handle({'op':'disarm'})
        for op in ('arm','clear'):
            with pytest.raises(InterlockError):b.handle({'op':op,'intent_generation':old})
        b.handle({'op':'arm','intent_generation':b.intent_generation})
        with pytest.raises(InterlockError):b.handle({'op':'arm','intent_generation':b.intent_generation})
        b.handle({'op':'estop'})
        assert not b.armed
    finally:b.close()


def test_sensor_gap_reboot_recovers_observation_only():
    b=BodyIMU(np.eye(3))
    def packet(t):return {'kind':'imu','source':'mpu6050','valid':True,'t_ms':t,'accel_m_s2':[0,0,G],'gyro_rad_s':[0,0,0]}
    b.ingest(packet(100),1.)
    with pytest.raises(SensorError):b.ingest(packet(100),1.01)
    b.ingest(packet(1),2.) # reboot after stale receive gap
    assert b.observation(2.)['valid']
    with pytest.raises(SensorError):b.observation(2.2)


def test_dropout_latches_simulation_stop_and_none_is_explicit():
    env=MistEnv(randomize=False,payload=0,sensor_profile={'dropout_probability':1.})
    try:
        obs,_=env.reset(seed=1);assert np.all(obs[:6]==0)
        _,_,done,_,info=env.step(np.zeros(12));assert done and info['sensor_fault']
        env.sensor.profile['dropout_probability']=0
        assert env.step(np.zeros(12))[2]
    finally:env.close()


def test_short_or_drifting_stop_cannot_pass():
    initial={'time_s':0.,'position':[0,0,.1],'rpy':[0,0,0],'body_velocity':[0,0,0],'fell':False,'body_ground_contact':False,'nonfoot_ground_contact':False}
    row=dict(initial,time_s=.02,body_angular_velocity=[0,0,0],tracking_error_rad=0,torque_saturation_fraction=0)
    assert not score(initial,[row],[0,0,0])['passed']
    row.update(time_s=20.,position=[.1,0,.1]);assert not score(initial,[row],[0,0,0])['checks']['path']

@pytest.mark.parametrize('rate',[10,50,500])
def test_slew_quantization_credit_is_not_renewed(rate):
    from locomotion.hardware.test_bridge import fixture,load,FakeLink
    calibration=load(fixture());link=FakeLink(calibration);b=Bridge(calibration,link)
    b.running=False;b.thread.join(1)
    try:
        with patch('locomotion.hardware.bridge.time.monotonic',return_value=10.):
            b.handle({'op':'arm','intent_generation':b.intent_generation,'unloaded_fixture_confirmed':True})
        start=b.q[0]
        for i in range(1,rate+1):
            q=b.q[:];q[0]=start+.5*i/rate
            with patch('locomotion.hardware.bridge.time.monotonic',return_value=10.+i/rate):b.handle({'op':'q','q':q})
        q=b.q[:];q[0]+=2/TICKS_PER_RAD
        with patch('locomotion.hardware.bridge.time.monotonic',return_value=11.):
            b.handle({'op':'q','q':q})
            q=q[:];q[0]+=1/TICKS_PER_RAD
            with pytest.raises(InterlockError):b.handle({'op':'q','q':q})
        assert b.q[0]-start<=.5+2/TICKS_PER_RAD+1e-10
    finally:b.running=False
