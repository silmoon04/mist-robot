import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
import numpy as np
import pybullet as p
from sim_remote import Simulation


def test_invalid_resets_preserve_running_simulation():
    sim=Simulation()
    try:
        original=sim.env
        for data in ({'terrain':'unsupported'},{'seed':-1},{'payload':float('nan')},
                     {'controller':'unsupported'},{'randomize':'false'},[]):
            with pytest.raises((ValueError,TypeError)):sim.reset(data)
            assert sim.env is original
            assert p.isConnected(original.client)
            assert sim.thread.is_alive()
        with pytest.raises(ValueError):sim.command({'command':[float('nan'),0,0]})
        sim.command({'command':[.02,-.03,.2]})
        with sim.lock:np.testing.assert_allclose(sim.env.command,[.012,-.012,.06])
        sim.reset({'seed':123,'payload':0})
        assert sim.env is not original
        assert sim.state()['info']['phone_mass_kg']==0
    finally:sim.close()
