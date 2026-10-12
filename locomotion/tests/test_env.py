import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env
from mist_env import MistEnv
from servo import ServoBank
from model import NEUTRAL
from gait import CrawlController


def test_gym_and_seeded_reset():
    env=MistEnv(max_steps=10)
    try:
        check_env(env,skip_render_check=True)
        a,ia=env.reset(seed=123)
        b,ib=env.reset(seed=123)
        np.testing.assert_array_equal(a,b)
        assert ia['randomization']==ib['randomization']
        assert a.shape==(47,)
        assert env.step(np.zeros(12))[0].shape==(47,)
        with pytest.raises(ValueError):env.step(np.full(12,np.nan))
    finally:env.close()


def test_mass_and_inertia_randomization_active():
    env=MistEnv(terrain='mixed',max_steps=2)
    try:
        samples=[env.reset(seed=seed)[1] for seed in range(4)]
        assert len({tuple(s['randomization']['body_com_shift_m']) for s in samples})==4
        assert len({s['phone_mass_kg'] for s in samples})==2
        assert any(s['randomization']['mass_scales']['-1']!=1 for s in samples)
    finally:env.close()


def test_motor_delay_slew_and_envelope():
    q=np.tile(NEUTRAL,4)
    bank=ServoBank(q,np.random.default_rng(0),False)
    initial=bank.target.copy()
    for _ in range(bank.delay_steps):bank.advance(q+.2,q,np.zeros(12))
    np.testing.assert_allclose(bank.target,initial,atol=.001)
    tau=bank.advance(q+.2,q,np.zeros(12))
    assert np.max(np.abs(bank.target-initial))<=bank.speed*bank.dt+.001
    assert np.max(np.abs(tau))<=bank.cap+bank.friction
    for _ in range(100):tau=bank.advance(q+.2,q,np.full(12,10.))
    assert np.max(np.abs(tau))<=bank.friction+.0001


def test_gait_limits_four_directions_and_stop():
    gait=CrawlController()
    np.testing.assert_allclose(gait.targets(5,(0,0,0)),np.tile(NEUTRAL,4))
    for command in ((.01,0,0),(-.01,0,0),(0,.01,0),(0,-.01,0)):
        for t in np.linspace(0,10,100):
            target=gait.targets(t,command)
            assert target.shape==(12,) and np.all(np.isfinite(target))


def test_imu_uses_body_frame_not_principal_inertia_axes():
    env=MistEnv(command=(0,0,0),randomize=False)
    try:
        obs,info=env.reset(seed=0)
        assert abs(info['rpy'][1])<.05
        np.testing.assert_allclose(obs[:3],[0,0,-1],atol=.05)
        assert .08<info['position'][2]<.14
    finally:env.close()
