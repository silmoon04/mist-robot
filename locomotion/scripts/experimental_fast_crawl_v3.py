"""Final bounded fast-preview variant: earlier horizontal recovery only.

Start the C1 horizontal recovery bridge at .82 instead of .84; retain its .96
end, vertical lift, support schedule and the cadence-scaled common body shift.
This is planned timing, never a measured-contact detector.
"""
import numpy as np
from experimental_fast_crawl_v2 import CadenceShiftFastCrawl
from experimental_clearance_recovery import clearance_along
from experimental_support_transfer import attitude_correction
from locomotion.gait import rz
from locomotion.kinematics import forward, inverse
from locomotion.model import LEGS, MOUNTS


def wider_along(phase, start=.82):
    end, slope = .96, -1./.8
    if phase <= start:
        return .5-phase/.8, slope
    if phase >= end:
        return .5+(1.-phase)/.8, slope
    width = end-start
    u = (phase-start)/width
    a, b = .5-start/.8, .5+(1.-end)/.8
    tangent, delta = slope*width, b-a
    quadratic, cubic = 3*delta-3*tangent, -2*delta+2*tangent
    return a+tangent*u+quadratic*u*u+cubic*u*u*u, (tangent+2*quadratic*u+3*cubic*u*u)/width


class WideRecoveryFastCrawl(CadenceShiftFastCrawl):
    def __init__(self, *args, recovery_start=.82, **kwargs):
        if recovery_start not in (.82, .84):
            raise ValueError("Bounded recovery start must be .82 or reference .84")
        self.recovery_start = recovery_start
        super().__init__(*args, **kwargs)

    def targets(self, time_s, command, attitude=None):
        original = super().targets(time_s, command, attitude)
        if self.recovery_start == .84 or np.max(np.abs(command)) < 1e-8:
            return original
        effective = self.effective_geometric_command(command)
        correction = attitude_correction(attitude)
        ramp = min(1., max(0., time_s/1.5))
        changed = original.reshape(4, 3).copy()
        for index, leg in enumerate(LEGS):
            phase = (time_s/self.cycle_s-self.offset[leg]) % 1.
            if phase <= .82 or phase >= .96:
                continue
            stride = (np.r_[effective[:2], 0.]+effective[2]*np.cross([0., 0., 1.], self.nominal[leg]))*self.cycle_s*.8
            length = np.linalg.norm(stride[:2])
            if length > .035:
                stride *= .035/length
            delta = correction@(ramp*stride*(wider_along(phase)[0]-clearance_along(phase)[0]))
            changed[index] = inverse(forward(changed[index])+rz(MOUNTS[leg]["yaw"]).T@delta)
        return changed.ravel()
