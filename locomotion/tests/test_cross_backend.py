import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
pytest.importorskip('mujoco')
from cross_backend import compare_leg,export_mjcf
import mujoco


def test_mujoco_source_mass_frames_and_finite_leg():
    result=compare_leg(.2,0.)
    assert result['finite']
    assert result['fk_error_m']<1e-10
    assert abs(result['source_mass_kg']-result['mujoco_mass_kg'])<1e-10
    assert max(result['joint_trajectory_difference_rmse_rad'])<.005


def test_mjcf_free_robot_twelve_actuators(tmp_path):
    files=export_mjcf(tmp_path)
    model=mujoco.MjModel.from_xml_path(str(files['quadruped']))
    assert model.nq==19 and model.nu==12
