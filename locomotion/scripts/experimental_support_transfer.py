"""Experimental periodic support-reference planner; no measured contact input.

Only the common body-shift reference changes. Clearance, geometric gain 1.15,
phase, vertical lift, attitude compensation and the centred-COM load estimator
are inherited. This is a development controller, not a qualified gait.
"""
from __future__ import annotations

import math
import numpy as np

from experimental_clearance_recovery import clearance_along
from experimental_stride_gain import TranslationGainClearanceCrawl
from locomotion.gait import rz
from locomotion.kinematics import forward, inverse
from locomotion.model import LEGS, MOUNTS

KNOTS = 32
LOAD_MARGIN_N = .1
COEFFICIENT_BOUND_MM = 15.
REGULARIZATION = .1
FEASIBILITY_TOL = 2e-8
MAX_ACTIVE_ITERATIONS = 5000
MAX_REFINEMENTS = 12


class PlanningError(RuntimeError):
    """An explicit execution error, which MistEnv cannot turn into neutral IK."""


def periodic_basis(phase, derivative=0):
    """Cubic periodic B-spline basis; derivatives are per unit cycle phase."""
    if derivative not in (0, 1, 2):
        raise ValueError("Only position, velocity and acceleration are defined")
    z = (float(phase) % 1.) * KNOTS
    k = math.floor(z)
    u = z-k
    if derivative == 0:
        values = np.array([(1-u)**3, 3*u**3-6*u*u+4,
                           -3*u**3+3*u*u+3*u+1, u**3])/6.
    elif derivative == 1:
        values = KNOTS*np.array([-.5*(1-u)**2, 1.5*u*u-2*u,
                                -1.5*u*u+u+.5, .5*u*u])
    else:
        values = KNOTS*KNOTS*np.array([1-u, 3*u-2, -3*u+1, u])
    result = np.zeros(KNOTS)
    result[(np.arange(k-1, k+3) % KNOTS)] = values
    return result


def attitude_correction(attitude=None):
    """The exact inherited half-angle compensation, in its original frame."""
    if attitude is None:
        return np.eye(3)
    roll, pitch = np.clip(np.asarray(attitude)[:2], -.25, .25)
    cr, sr, cp, sp = math.cos(.5*roll), math.sin(.5*roll), math.cos(.5*pitch), math.sin(.5*pitch)
    return np.array([[cp, sp*sr, sp*cr], [0, cr, -sr], [-sp, cp*sr, cp*cr]]).T


def feet_from_angles(angles):
    return np.array([np.asarray(MOUNTS[leg]["xyz"])+rz(MOUNTS[leg]["yaw"])@forward(q)
                     for leg, q in zip(LEGS, np.asarray(angles).reshape(4, 3))])


def inherited_shift_reference(gait, time_s):
    """Reference shift and its first two derivatives for paired diagnostics."""
    values = np.zeros((3, 2))
    for leg in LEGS:
        phase = (time_s/gait.cycle_s-gait.offset[leg]) % 1.
        if phase <= .73:
            continue
        u = (phase-.73)/.27
        direction = gait.nominal[leg][:2]/np.linalg.norm(gait.nominal[leg][:2])
        factors = np.array([math.sin(math.pi*u)**2,
                            math.pi*math.sin(2*math.pi*u)/(.27*gait.cycle_s),
                            2*math.pi**2*math.cos(2*math.pi*u)/(.27*gait.cycle_s)**2])
        values -= gait.shift_m*factors[:, None]*direction
    ramp = min(1., max(0., time_s/1.5))
    rate = 1./1.5 if 0. <= time_s < 1.5 else 0.
    return {"shift_m": ramp*values[0], "shift_velocity_m_s": ramp*values[1]+rate*values[0],
            "shift_acceleration_m_s2": ramp*values[2]+2*rate*values[1],
            "periodic_shift_m": values[0], "periodic_shift_velocity_m_s": values[1],
            "periodic_shift_acceleration_m_s2": values[2], "ramp": ramp}


def load_diagnostics(gait, time_s, command, geometric, phone_mass_kg):
    """Report both raw moments and the unchanged clipped/renormalized loads."""
    points = feet_from_angles(geometric)
    matrix = np.vstack([np.ones(4), points[:, 0], points[:, 1]])
    weights = gait.support_weights(time_s, command)
    force = (gait.model_mass_without_phone+phone_mass_kg)*9.81
    raw = weights*(matrix.T@np.linalg.solve((matrix*weights)@matrix.T, [force, 0., 0.]))
    clipped = gait.estimate_support_forces(time_s, command, geometric, phone_mass_kg)
    return {"geometric_body_feet_m": points, "scheduled_support_weights": weights,
            "raw_support_force_n": raw, "clipped_support_force_n": clipped,
            "raw_load_sum_error_n": float(raw.sum()-force),
            "raw_moment_nm": matrix[1:]@raw,
            "clipped_moment_nm": matrix[1:]@clipped}


def solve_convex_qp(hessian, rows, lower):
    """Minimize .5*x'H*x subject to A*x >= b, using a NumPy dual active set.

    This is a nonnegative quadratic dual working-set method. Each inner solve
    finds the equality optimum; a dual line search removes negative active
    multipliers. Primal feasibility, stationarity and complementarity are
    checked before returning. Infeasibility, degeneracy and iteration limits
    raise PlanningError; there is no alternate gait or silent relaxation.
    """
    hessian, rows, lower = map(lambda a: np.asarray(a, dtype=float), (hessian, rows, lower))
    if not all(np.isfinite(a).all() for a in (hessian, rows, lower)):
        raise PlanningError("Nonfinite support QP")
    inverse_rows = np.linalg.solve(hessian, rows.T)
    active, multipliers = [], np.empty(0)
    x = np.zeros(hessian.shape[0])
    for iteration in range(MAX_ACTIVE_ITERATIONS):
        gradient = lower-rows@x
        if active:
            gradient[active] = -np.inf
        entering = int(np.argmax(gradient))
        if gradient[entering] <= FEASIBILITY_TOL:
            primal = float(np.max(lower-rows@x))
            stationarity = float(np.max(np.abs(hessian@x-rows[active].T@multipliers))) if active else 0.
            complementarity = float(np.max(np.abs(multipliers*(rows[active]@x-lower[active])))) if active else 0.
            if primal > FEASIBILITY_TOL or stationarity > 1e-6 or complementarity > 1e-6:
                raise PlanningError(f"Support QP residuals {primal}, {stationarity}, {complementarity}")
            return x, {"iterations": iteration, "active_constraints": len(active),
                       "primal_violation_fraction": max(0., primal),
                       "stationarity": stationarity, "complementarity": complementarity,
                       "objective": float(.5*x@hessian@x)}
        active.append(entering)
        multipliers = np.r_[multipliers, 0.]
        for _ in range(MAX_ACTIVE_ITERATIONS):
            gram = rows[active]@inverse_rows[:, active]
            try:
                candidate = np.linalg.solve(gram, lower[active])
            except np.linalg.LinAlgError as error:
                raise PlanningError("Degenerate support QP working set") from error
            if np.max(np.abs(gram@candidate-lower[active])) > 1e-7:
                raise PlanningError("Ill-conditioned support QP working set")
            negative = candidate <= 0.
            if not negative.any():
                multipliers = candidate
                break
            fractions = multipliers[negative]/(multipliers[negative]-candidate[negative])
            alpha = float(np.min(fractions))
            multipliers += alpha*(candidate-multipliers)
            keep = multipliers > 1e-10
            active = [index for index, retain in zip(active, keep) if retain]
            multipliers = multipliers[keep]
            if not active:
                break
        else:
            raise PlanningError("Support QP inner iteration bound exceeded")
        x = inverse_rows[:, active]@multipliers if active else np.zeros_like(x)
    raise PlanningError("Support QP iteration bound exceeded")


class PlannedSupportTransferCrawl(TranslationGainClearanceCrawl):
    """Plan once per requested command and known payload; use no truth state.

    The spline is optimized in millimetres, with centred COM and zero attitude.
    During each planned .80--1 swing, the three other feet each carry at least
    .1 N in the nominal model. All-phase constraints also keep the original
    scheduled weighted solve nonnegative before its clipping step. A smooth
    reference can start shifting while all four feet are down; it need not
    return to zero in the .16 s gap between adjacent swings.

    Attitude compensation and the inherited startup ramp remain unchanged.
    Their support feasibility is diagnosed separately: nominal constraints
    are not a guarantee for tilted, dynamic or randomized physical states.
    """
    def __init__(self, *args, phone_mass_kg=.155, **kwargs):
        if not np.isfinite(phone_mass_kg) or phone_mass_kg < 0:
            raise ValueError("Known payload must be finite and nonnegative")
        if kwargs.get("shift_m", 0.) != 0.:
            raise ValueError("The planned reference replaces the inherited shift")
        kwargs["shift_m"] = 0.
        kwargs["translational_stride_gain"] = 1.15
        super().__init__(*args, **kwargs)
        if self.cycle_s != 3.2 or self.lift_m != .012:
            raise ValueError("This experiment retains cycle 3.2 s and lift .012 m")
        self.phone_mass_kg = float(phone_mass_kg)
        self.plans = {}

    def unshifted_points(self, phase, command, ramp=1.):
        effective = self.effective_geometric_command(command)
        result = []
        for leg in LEGS:
            own_phase = (phase-self.offset[leg]) % 1.
            stride = (np.r_[effective[:2], 0.]+effective[2]*np.cross([0., 0., 1.], self.nominal[leg]))*self.cycle_s*.8
            length = np.linalg.norm(stride[:2])
            if length > .035:
                stride *= .035/length
            lift = 0. if own_phase < .8 else self.lift_m*math.sin(math.pi*(own_phase-.8)/.2)**2
            result.append(self.nominal[leg]+ramp*(stride*clearance_along(own_phase)[0]+[0., 0., lift]))
        return np.array(result)

    def constraints_at(self, phase, command):
        points = self.unshifted_points(phase, command)
        basis = periodic_basis(phase)*.001
        rows, lower, labels = [], [], []
        phases = np.array([(phase-self.offset[leg]) % 1. for leg in LEGS])
        margin = LOAD_MARGIN_N/((self.model_mass_without_phone+self.phone_mass_kg)*9.81)
        # A point s within the unshifted triangle places centred COM within
        # the translated triangle p-s. Its barycentric loads are affine in s.
        swinging = np.flatnonzero(phases >= .8)
        if len(swinging) > 1:
            raise PlanningError("Unexpected overlapping planned swings")
        if len(swinging):
            stance = [i for i in range(4) if i != swinging[0]]
            inverse_matrix = np.linalg.inv(np.vstack([np.ones(3), points[stance, 0], points[stance, 1]]))
            for index, affine in zip(stance, inverse_matrix):
                rows.append(np.r_[affine[1]*basis, affine[2]*basis])
                lower.append(margin+1e-6-affine[0])
                labels.append(f"triangle:{LEGS[index]}")
        weights = self.support_weights(phase*self.cycle_s, command)
        centre = (weights[:, None]*points[:, :2]).sum(axis=0)/weights.sum()
        delta = points[:, :2]-centre
        covariance = delta.T@(weights[:, None]*delta)
        slopes = weights[:, None]*np.linalg.solve(covariance, delta.T).T
        intercept = weights/weights.sum()-slopes@centre
        for index in np.flatnonzero(weights > 1e-10):
            rows.append(np.r_[slopes[index, 0]*basis, slopes[index, 1]*basis])
            lower.append(-intercept[index])
            labels.append(f"scheduled:{LEGS[index]}")
        return np.array(rows), np.array(lower), labels

    def plan(self, command):
        command = np.asarray(command, dtype=float)
        self.effective_geometric_command(command)
        key = tuple(command)
        if key in self.plans:
            return self.plans[key]
        if np.max(np.abs(command)) < 1e-8:
            result = {"coefficients_mm": np.zeros((2, KNOTS)), "solver": {"stop": True}}
            self.plans[key] = result
            return result
        objective_grid = np.arange(512)/512.
        basis = np.array([periodic_basis(p) for p in objective_grid])
        derivative = np.array([periodic_basis(p, 1) for p in objective_grid])
        one = (derivative.T@derivative+REGULARIZATION*basis.T@basis)/(len(basis)*self.cycle_s**2)
        hessian = np.kron(np.eye(2), one)
        phases = list(np.arange(128)/128.)
        for offset in self.offset.values():
            phases += [(offset+p) % 1. for p in (.76, .8, .82, .84, .96, .97, 1.-1e-8)]
        rows, lower = [], []
        for phase in phases:
            a, b, _ = self.constraints_at(phase, command)
            rows.extend(a)
            lower.extend(b)
        rows.extend(np.eye(2*KNOTS))
        rows.extend(-np.eye(2*KNOTS))
        lower.extend(np.full(4*KNOTS, -COEFFICIENT_BOUND_MM))
        validation_grid = (np.arange(4096)+.3819660112501051)/4096.
        checked = [self.constraints_at(p, command)[:2] for p in validation_grid]
        checked_rows = np.vstack([a for a, _ in checked])
        checked_lower = np.concatenate([b for _, b in checked])
        for refinement in range(MAX_REFINEMENTS):
            solution, report = solve_convex_qp(hessian, np.array(rows), np.array(lower))
            violation = checked_lower-checked_rows@solution
            if np.max(violation) <= FEASIBILITY_TOL:
                report.update({"refinements": refinement, "dense_validation_phases": len(validation_grid),
                               "dense_primal_violation_fraction": float(max(0., np.max(violation))),
                               "constraint_count": len(rows), "load_margin_n": LOAD_MARGIN_N,
                               "coefficient_bound_mm": COEFFICIENT_BOUND_MM,
                               "objective_definition": "mean phase-derivative squared plus .1 mean position squared, divided by cycle_s squared; coefficients in mm",
                               "frame": "nominal zero-attitude body frame; centred COM"})
                result = {"coefficients_mm": solution.reshape(2, KNOTS), "solver": report}
                self.plans[key] = result
                return result
            # Add the largest dense violations, rather than relax the margin.
            worst = np.argsort(violation)[-24:]
            for index in worst:
                if violation[index] > FEASIBILITY_TOL:
                    rows.append(checked_rows[index])
                    lower.append(checked_lower[index])
        raise PlanningError("Support QP dense-grid refinement bound exceeded")

    def reference(self, time_s, command):
        plan = self.plan(command)
        phase = (time_s/self.cycle_s) % 1.
        values = [plan["coefficients_mm"]@periodic_basis(phase, d)*.001/self.cycle_s**d for d in range(3)]
        ramp = min(1., max(0., time_s/1.5))
        ramp_rate = 1./1.5 if 0. <= time_s < 1.5 else 0.
        # The linear startup ramp has an inherited derivative corner at 1.5 s.
        return {"shift_m": ramp*values[0], "shift_velocity_m_s": ramp*values[1]+ramp_rate*values[0],
                "shift_acceleration_m_s2": ramp*values[2]+2*ramp_rate*values[1],
                "periodic_shift_m": values[0], "periodic_shift_velocity_m_s": values[1],
                "periodic_shift_acceleration_m_s2": values[2], "ramp": ramp}

    def targets(self, time_s, command, attitude=None):
        original = super().targets(time_s, command, attitude)
        if np.max(np.abs(command)) < 1e-8:
            return original
        reference = self.reference(time_s, command)
        delta = attitude_correction(attitude)@np.r_[reference["shift_m"], 0.]
        changed = original.reshape(4, 3).copy()
        try:
            for index, leg in enumerate(LEGS):
                changed[index] = inverse(forward(changed[index])-rz(MOUNTS[leg]["yaw"]).T@delta)
        except ValueError as error:
            raise PlanningError(f"Planned support reference violates IK: {error}") from error
        return changed.ravel()
