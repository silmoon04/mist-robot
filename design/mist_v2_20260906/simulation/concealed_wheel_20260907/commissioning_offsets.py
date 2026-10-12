"""Choose fixed mathematical shaft references from required joint-angle spans.

This module does not run physics, alter parameters, or commission hardware.
Offsets cannot change a required span. Midrange centering maximizes the smaller
endpoint margin within the existing +/-175 degree shaft interval.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np

LEG_NAMES = ("FL", "FR", "RL", "RR")
JOINT_NAMES = ("yaw", "hip", "knee")
TOL_DEG = 1e-8
WORLD_TOL_M = 1e-7


def _array(value, shape, label):
    result = np.asarray(value, dtype=float)
    if result.shape != shape or not np.isfinite(result).all():
        raise ValueError(f"{label}: expected finite shape {shape}")
    return result


def _samples(value, label):
    result = np.asarray(value, dtype=float)
    if result.shape == (4, 3):
        result = result[None, ...]
    if result.ndim != 3 or result.shape[1:] != (4, 3) or not len(result) or not np.isfinite(result).all():
        raise ValueError(f"{label}: expected finite Nx4x3 or 4x3 radians")
    return result


def _physical_limits(parameters):
    geometry = parameters["geometry"]
    if "joint_limits_by_leg_deg" in geometry:
        if "joint_limits_per_leg_deg" in geometry:
            raise ValueError("Two per-leg joint-limit formats are present; choose one explicit source")
        per_leg = geometry["joint_limits_by_leg_deg"]
        if not isinstance(per_leg, dict) or set(per_leg) != set(LEG_NAMES):
            raise ValueError("Per-leg physical bounds must contain FL, FR, RL and RR exactly")
        limits = np.asarray([per_leg[name] for name in LEG_NAMES], dtype=float)
    else:
        limits = np.asarray(geometry.get("joint_limits_per_leg_deg", geometry["joint_limits_deg"]), dtype=float)
    if limits.shape == (3, 2):
        limits = np.broadcast_to(limits, (4, 3, 2)).copy()
    if limits.shape != (4, 3, 2) or not np.isfinite(limits).all() or np.any(limits[..., 0] >= limits[..., 1]):
        raise ValueError("Expected finite physical joint bounds, shape 3x2 or 4x3x2")
    return limits


def _contract(parameters, ratios):
    if tuple(parameters["geometry"]["leg_names"]) != LEG_NAMES:
        raise ValueError("Reference files require physical leg order FL, FR, RL, RR")
    tr = parameters["transmission"]
    if tr["topology"] != "proximal_femur_relative_knee" or tr.get("knee_motor_mount") != "femur":
        raise ValueError("Independent offsets require the diagonal femur-relative knee transmission")
    r = _array(ratios, (3,), "ratios")
    if np.any(r <= 0):
        raise ValueError("Only positive normalized actuator ratios are supported")
    bounds = _array(tr["motor_travel_limits_deg"], (3, 2), "motor shaft bounds")
    if not np.array_equal(bounds, np.tile([-175., 175.], (3, 1))):
        raise ValueError("This contract preserves the existing +/-175 degree, 350 degree total shaft span")
    return r, bounds, _physical_limits(parameters)


def assess_angle_samples(parameters, samples_q_rad, *, ratios=(2., 3., 3.), labels=None):
    """Use one static reference per physical joint over the entire sample set.

    Returned ``travel_reference_q_rad`` and ``travel_reference_shaft_rad`` are
    mathematical zeros, not encoder register values. All twelve joints retain
    the same references for fixture, flat and reference poses. Physical hard
    stops are intersected with the shaft corridor; targets are never clipped.
    """
    r, shaft_bounds, physical = _contract(parameters, ratios)
    q = np.degrees(_samples(samples_q_rad, "required joint samples"))
    labels = list(labels) if labels is not None else [f"sample[{i}]" for i in range(len(q))]
    if len(labels) != len(q):
        raise ValueError("One source label is required for every sample")
    low, high = q.min(axis=0), q.max(axis=0)
    center = (low + high) / 2
    corridor = np.stack([center + shaft_bounds[:, 0] / r, center + shaft_bounds[:, 1] / r], axis=-1)
    intersected = np.stack([np.maximum(corridor[..., 0], physical[..., 0]),
                            np.minimum(corridor[..., 1], physical[..., 1])], axis=-1)
    required_output = high - low
    required_shaft = required_output * r
    span_conflict = required_shaft > 350 + TOL_DEG
    physical_conflict = (low < physical[..., 0] - TOL_DEG) | (high > physical[..., 1] + TOL_DEG)
    records = []
    for leg, name in enumerate(LEG_NAMES):
        for axis, joint in enumerate(JOINT_NAMES):
            records.append({"leg": name, "joint": joint, "ratio": float(r[axis]),
                "required_output_min_deg": float(low[leg, axis]), "required_output_max_deg": float(high[leg, axis]),
                "required_output_span_deg": float(required_output[leg, axis]),
                "available_output_span_deg": float(350 / r[axis]),
                "required_shaft_span_deg": float(required_shaft[leg, axis]), "available_shaft_span_deg": 350.,
                "minimum_centered_shaft_margin_deg": float((350 - required_shaft[leg, axis]) / 2),
                "travel_reference_q_deg": float(center[leg, axis]),
                "travel_reference_shaft_deg": float(r[axis] * center[leg, axis]),
                "required_shaft_offsets_deg": [float(-required_shaft[leg, axis] / 2), float(required_shaft[leg, axis] / 2)],
                "raw_output_corridor_deg": corridor[leg, axis].tolist(),
                "physical_output_limits_deg": physical[leg, axis].tolist(),
                "intersected_output_limits_deg": intersected[leg, axis].tolist(),
                "span_conflict": bool(span_conflict[leg, axis]), "physical_limit_conflict": bool(physical_conflict[leg, axis]),
                "minimum_source": labels[int(q[:, leg, axis].argmin())],
                "maximum_source": labels[int(q[:, leg, axis].argmax())]})
    fits = not np.any(span_conflict) and not np.any(physical_conflict)
    return {"status": "ANGLE_ENVELOPE_FITS" if fits else "ANGLE_ENVELOPE_CONFLICT",
        "sample_count": len(q), "leg_order": list(LEG_NAMES), "joint_order": list(JOINT_NAMES),
        "ratios": r.tolist(), "all_required_angles_fit": bool(fits),
        "all_required_shaft_spans_fit": not bool(np.any(span_conflict)),
        "all_required_angles_within_physical_limits": not bool(np.any(physical_conflict)),
        "travel_reference_q_rad": np.radians(center).tolist(),
        "travel_reference_shaft_rad": np.radians(center * r).tolist(),
        "per_leg_output_limits_deg": intersected.tolist(),
        "raw_per_leg_output_corridor_deg": corridor.tolist(),
        "original_shaft_limits_deg": shaft_bounds.tolist(), "joints": records,
        "span_conflicts": [item for item in records if item["span_conflict"]],
        "physical_limit_conflicts": [item for item in records if item["physical_limit_conflict"]],
        "commissioned": False,
        "interpretation": "One static reference per physical joint; no per-mode recentering, clipping or angular wrapping. Offsets maximize endpoint reserve but cannot reduce required span."}


def reference_pitch_rotation(pitch_deg):
    """Saved pitch_search.py convention: standard active Ry(-pitch)."""
    angle = float(pitch_deg)
    if not np.isfinite(angle):
        raise ValueError("Reference pitch must be finite")
    c, s = np.cos(np.radians(angle)), np.sin(np.radians(angle))
    return np.array([[c, 0., -s], [0., 1., 0.], [s, 0., c]])


def _read(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return json.loads(raw), {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}


def _records(dense, rear):
    samples = dense["samples"]
    if len(samples) != 815 or dense["verification"]["dense_count"] != 815:
        raise ValueError("Expected the frozen 815-sample dense front-leg reference")
    if dense["verification"]["dense_feasible"] is not True or rear["result"]["feasible"] is not True:
        raise ValueError("Expected the saved feasible reference candidates")
    records = []
    for index, item in enumerate(samples):
        records.append({"label": f"old_front[{index}]", "q_rad": np.radians(_array(item["q_deg"], (4, 3), "front q")),
                        "body": _array(item["body_m"], (3,), "front body"),
                        "feet": _array(item["feet_m"], (4, 3), "front axle targets"),
                        "rotation": reference_pitch_rotation(item.get("pitch_deg", 0.))})
    item = rear["result"]
    records.append({"label": "old_rear_feasible_pose", "q_rad": np.radians(_array(item["q_deg"], (4, 3), "rear q")),
                    "body": _array(item["body_m"], (3,), "rear body"),
                    "feet": _array(item["feet_axle_m"], (4, 3), "rear axle targets"),
                    "rotation": reference_pitch_rotation(item["pitch_deg"])})
    return records


def analyze_commissioning(parameters, model, dense_reference_path, rear_reference_path,
                          reference_parameters_path, *, fixture_q_rad=None, flat_q_rad=None,
                          reproject_old_targets=False, ratios=(2., 3., 3.)):
    """Assess original angles separately from optional current-geometry IK.

    ``parameters`` must contain the current physical geometry, before adding a
    hypothetical shaft corridor. The caller freezes the three input files.
    ``fixture_q_rad`` and ``flat_q_rad`` accept 4x3 or Nx4x3 radians; the current
    neutral pose is included when no fixture samples are supplied. Returned
    alternatives require an explicit caller choice and are never merged.
    """
    _contract(parameters, ratios)
    p = copy.deepcopy(parameters)
    dense, dense_source = _read(dense_reference_path)
    rear, rear_source = _read(rear_reference_path)
    old, old_source = _read(reference_parameters_path)
    expected = dense["verification"]["source_hashes"]["parameters_snapshot.json"]
    if old_source["sha256"] != expected:
        raise ValueError("Old reference parameter hash does not match the dense source receipt")
    if tuple(old["geometry"]["leg_names"]) != LEG_NAMES:
        raise ValueError("Old reference leg order differs")
    records = _records(dense, rear)
    current_samples = _samples(model.neutral(p) if fixture_q_rad is None else fixture_q_rad, "current fixture envelope")
    current_labels = [f"current_fixture[{i}]" for i in range(len(current_samples))]
    if flat_q_rad is not None:
        flat = _samples(flat_q_rad, "current flat reference")
        current_samples = np.concatenate([current_samples, flat])
        current_labels += [f"current_flat[{i}]" for i in range(len(flat))]
    labels = [item["label"] for item in records] + current_labels
    exact_q = np.concatenate([np.array([item["q_rad"] for item in records]), current_samples])
    exact = assess_angle_samples(p, exact_q, ratios=ratios, labels=labels)
    differences = {key: {"reference": old["geometry"].get(key), "current": p["geometry"].get(key)}
                   for key in sorted(old["geometry"].keys() | p["geometry"].keys())
                   if old["geometry"].get(key) != p["geometry"].get(key)}
    exact["basis"] = "Original saved joint angles plus the current fixture/flat envelope"
    exact["reference_geometry_mismatch"] = bool(differences)
    # Verify the target interpretation independently, including the rear pitch sign.
    old_residuals, current_exact_residuals = [], []
    for item in records:
        for leg in range(4):
            predicted = item["body"] + item["rotation"] @ model.fk(old, leg, item["q_rad"][leg])["axle"]
            old_residuals.append(float(np.linalg.norm(predicted - item["feet"][leg])))
            current = item["body"] + item["rotation"] @ model.fk(p, leg, item["q_rad"][leg])["axle"]
            current_exact_residuals.append(float(np.linalg.norm(current - item["feet"][leg])))
    old_max = max(old_residuals)
    exact["maximum_current_geometry_world_target_error_m"] = max(current_exact_residuals)
    exact["old_geometry_angles_do_not_reproduce_current_world_targets"] = max(current_exact_residuals) > WORLD_TOL_M
    report = {"schema_version": 1, "status": "mathematical_commissioning_reference_analysis_not_hardware_calibration",
        "sources": {"dense_front": dense_source, "rear_pose": rear_source, "old_geometry_parameters": old_source},
        "current_parameters_sha256": hashlib.sha256(json.dumps(parameters, sort_keys=True, allow_nan=False).encode()).hexdigest(),
        "geometry_differences": differences,
        "reference_counts": {"old_front": 815, "old_rear": 1, "current_fixture_and_flat": len(current_samples)},
        "old_target_interpretation": {"max_world_FK_residual_m": old_max, "passed": old_max <= WORLD_TOL_M,
            "pitch_convention": "pitch_search.rotation(p): standard active Ry(-p)",
            "rear_geometry_provenance": "Caller-supplied shared old geometry; rear JSON has no embedded parameter hash."},
        "old_exact_angle_assessment": exact, "reprojected_world_target_assessment": None,
        "source_sha256": {Path(__file__).name: hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        "limitations": ["Only required angle envelopes are assessed. No load, mass, contact, collision, speed, thermal or stair validation.",
            "The old dense front motion and rear pose are separate references, not a verified continuous four-leg stair sequence.",
            "Static offsets are normalized mathematical references; encoder zeros, signs and hardware homing remain uncommissioned."]}
    if getattr(model, "__file__", None):
        report["source_sha256"]["model.py"] = hashlib.sha256(Path(model.__file__).read_bytes()).hexdigest()
    if reproject_old_targets:
        if old_max > WORLD_TOL_M:
            report["reprojected_world_target_assessment"] = {"status": "REFERENCE_TARGET_INTERPRETATION_FAILED", "usable_for_required_reference": False}
            return report
        projected, failures = [], []
        physical = _physical_limits(p)
        maximum_residual = 0.
        geometry_failed_count = physical_failed_count = ik_failed_count = 0
        for item in records:
            pose = []
            for leg in range(4):
                target = item["rotation"].T @ (item["feet"][leg] - item["body"])
                q, ok = model.ik(p, leg, target)
                q = _array(q, (3,), "reprojected IK")
                error = float(np.linalg.norm(model.fk(p, leg, q)["axle"] - target))
                maximum_residual = max(maximum_residual, error)
                angles = np.degrees(q)
                physical_ok = bool(np.all(angles >= physical[leg, :, 0] - TOL_DEG) and np.all(angles <= physical[leg, :, 1] + TOL_DEG))
                reached = error <= WORLD_TOL_M
                geometry_failed_count += int(not reached)
                physical_failed_count += int(not physical_ok)
                ik_failed_count += int(not ok)
                if not ok or not physical_ok or not reached:
                    failures.append({"source": item["label"], "leg": LEG_NAMES[leg], "ik_valid": bool(ok),
                        "world_target_reached": reached, "physical_limits_valid": physical_ok,
                        "FK_residual_m": error, "attempted_q_deg": angles.tolist()})
                pose.append(q)
            projected.append(pose)
        assessment = assess_angle_samples(p, np.concatenate([np.asarray(projected), current_samples]), ratios=ratios, labels=labels)
        assessment.update(basis="Current-geometry IK of the unchanged old body poses and world axle targets, plus current fixture/flat angles",
            reference_geometry_mismatch=bool(differences), maximum_world_FK_residual_m=maximum_residual,
            geometric_reach_failure_count=geometry_failed_count, physical_limit_failure_count=physical_failed_count,
            ik_invalid_leg_pose_count=ik_failed_count, failed_leg_poses=failures,
            usable_for_required_reference=not failures and assessment["all_required_angles_fit"],
            attempted_IK_angles_retained_without_clipping_by_this_helper=True)
        if failures:
            assessment["status"] = "REPROJECTED_REFERENCE_INVALID"
        report["reprojected_world_target_assessment"] = assessment
    return report


def _self_test():
    """Small deterministic math contracts; no files, physics or old mass input."""
    import unittest

    class Contracts(unittest.TestCase):
        def setUp(self):
            self.p = {"geometry": {"leg_names": list(LEG_NAMES), "joint_limits_deg": [[-100, 100], [-40, 125], [-150, -15]]},
                      "transmission": {"topology": "proximal_femur_relative_knee", "knee_motor_mount": "femur", "motor_travel_limits_deg": [[-175, 175]] * 3}}
            self.q = np.radians(np.tile([0., 30., -80.], (2, 4, 1)))

        def test_neutral_is_not_the_zero(self):
            self.q[:, :, 1] = np.radians([10., 110.])[:, None]
            result = assess_angle_samples(self.p, self.q)
            self.assertTrue(np.allclose(np.degrees(result["travel_reference_q_rad"])[:, 1], 60.))
            self.assertEqual(result["joints"][1]["required_shaft_span_deg"], 300.)

        def test_exact_span_and_excess_are_distinct(self):
            self.q[:, :, 2] = np.radians([-140., -140. + 350 / 3])[:, None]
            self.assertTrue(assess_angle_samples(self.p, self.q)["all_required_shaft_spans_fit"])
            self.q[1, 0, 2] += np.radians(.001)
            result = assess_angle_samples(self.p, self.q)
            self.assertEqual(len(result["span_conflicts"]), 1)
            self.assertLess(result["span_conflicts"][0]["minimum_centered_shaft_margin_deg"], 0.)

        def test_single_static_center_for_combined_modes(self):
            self.q[:, :, 1] = np.radians([0., 120.])[:, None]
            separate = [assess_angle_samples(self.p, sample) for sample in self.q]
            self.assertTrue(all(r["all_required_shaft_spans_fit"] for r in separate))
            self.assertFalse(assess_angle_samples(self.p, self.q)["all_required_shaft_spans_fit"])

        def test_physical_limit_failures_do_not_disappear(self):
            self.q[:, 0, 1] = np.radians([124., 126.])
            result = assess_angle_samples(self.p, self.q)
            self.assertTrue(result["all_required_shaft_spans_fit"])
            self.assertFalse(result["all_required_angles_fit"])
            self.assertEqual(result["per_leg_output_limits_deg"][0][1][1], 125.)

        def test_coupled_topology_and_increased_span_rejected(self):
            self.p["transmission"]["topology"] = "proximal_reduction_absolute_tibia"
            with self.assertRaises(ValueError):
                assess_angle_samples(self.p, self.q)
            self.p["transmission"]["topology"] = "proximal_femur_relative_knee"
            self.p["transmission"]["motor_travel_limits_deg"] = [[-176, 176]] * 3
            with self.assertRaises(ValueError):
                assess_angle_samples(self.p, self.q)

        def test_explicit_leg_dictionary_limits_are_honored(self):
            per_leg = {name: copy.deepcopy(self.p["geometry"]["joint_limits_deg"]) for name in LEG_NAMES}
            per_leg["FL"][1] = [-40., 29.]
            self.p["geometry"]["joint_limits_by_leg_deg"] = per_leg
            result = assess_angle_samples(self.p, self.q)
            self.assertEqual([(item["leg"], item["joint"]) for item in result["physical_limit_conflicts"]], [("FL", "hip")])
            self.assertEqual(result["per_leg_output_limits_deg"][0][1][1], 29.)

        def test_saved_pitch_convention(self):
            np.testing.assert_allclose(reference_pitch_rotation(90.) @ [0., 0., 1.], [-1., 0., 0.], atol=1e-12)

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Contracts))
    return result.wasSuccessful()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("Import analyze_commissioning from the frozen wrapper, or use --self-test")
    raise SystemExit(0 if _self_test() else 1)
