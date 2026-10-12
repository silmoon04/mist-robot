"""Explicit control uncertainty proxies; no structural material model."""
import math


def feedback_deadband(error_rad, half_width_rad):
    """A continuous dead zone in position feedback, with the outer slope retained."""
    if not math.isfinite(error_rad) or not math.isfinite(half_width_rad) or half_width_rad < 0:
        raise ValueError("Feedback error and a nonnegative deadband must be finite")
    return math.copysign(max(abs(error_rad)-half_width_rad,0.0),error_rad)


def describe_case(stiffness_scale, damping_scale, deadband_deg):
    if not 0 < stiffness_scale <= 1 or not 0 < damping_scale <= 1 or not 0 <= deadband_deg <= 2:
        raise ValueError("Sensitivity scales must be positive and no greater than one; deadband must be 0 to 2 degrees")
    return {
        "position_stiffness_scale":stiffness_scale,
        "derivative_damping_scale":damping_scale,
        "feedback_deadband_half_width_deg":deadband_deg,
        "feedback_deadband_full_width_deg":2*deadband_deg,
        "scope":"Finite actuator and fixture response sensitivity represented by joint control gains and a position-feedback dead zone. Links remain rigid.",
        "material_properties_measured":False,
        "structural_flexibility_simulated":False,
        "mechanical_backlash_simulated":False,
        "note":"The dead zone is a feedback uncertainty proxy. It does not simulate separate motor and output shafts, contact between backlash flanks, anisotropic printed material, creep, fracture or joint separation. Gravity feedforward remains active.",
    }
