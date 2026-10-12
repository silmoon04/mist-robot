"""Experimental planned clearance window; no contact or velocity truth feedback.

Compared with VelocityMatchedCrawl, change only the horizontal recovery window
to phases .84--.96. Vertical lift, support weights, stance speed and servo
settings remain inherited. Before and after that window the toe follows the
stance-compatible horizontal velocity. The fixed window is a development
hypothesis based on earlier contact receipts, not a runtime contact detector.
"""
from __future__ import annotations

import math
import numpy as np
from experimental_recovery import VelocityMatchedCrawl, recovery_along
from locomotion.gait import rz
from locomotion.kinematics import forward, inverse
from locomotion.model import LEGS, MOUNTS

RECOVERY_START = .84
RECOVERY_END = .96


def clearance_along(phase):
    """Closed-form position and d(position)/d(cycle phase).

    Continue the stance line through release and extrapolate the next stance
    line backward through touchdown. A central cubic Hermite bridge joins
    those lines with slope -1/.8 at both ends.
    """
    slope = -1/.8
    if phase <= RECOVERY_START:
        return .5-phase/.8,slope
    if phase >= RECOVERY_END:
        return .5+(1.-phase)/.8,slope
    width = RECOVERY_END-RECOVERY_START
    s = (phase-RECOVERY_START)/width
    a = .5-RECOVERY_START/.8
    b = .5+(1.-RECOVERY_END)/.8
    delta = b-a
    tangent = slope*width
    quadratic,cubic = 3.*delta-3.*tangent,-2.*delta+2.*tangent
    position = a+tangent*s+quadratic*s*s+cubic*s*s*s
    derivative = (tangent+2.*quadratic*s+3.*cubic*s*s)/width
    return position,derivative


class ClearanceWindowCrawl(VelocityMatchedCrawl):
    """Use only planned phase, command and the existing measured attitude."""

    def targets(self,time_s,command,attitude=None):
        original = super().targets(time_s,command,attitude)
        cmd = np.asarray(command,dtype=float)
        if np.max(np.abs(cmd)) < 1e-8:
            return original
        ramp = min(1.,max(0.,time_s/1.5))
        correction = np.eye(3)
        if attitude is not None:
            roll,pitch = np.clip(np.asarray(attitude)[:2],-.25,.25)
            cr,sr,cp,sp = math.cos(.5*roll),math.sin(.5*roll),math.cos(.5*pitch),math.sin(.5*pitch)
            correction = np.array([[cp,sp*sr,sp*cr],[0,cr,-sr],[-sp,cp*sr,cp*cr]]).T
        changed = original.reshape(4,3).copy()
        for index,leg in enumerate(LEGS):
            phase = (time_s/self.cycle_s-self.offset[leg]) % 1.
            if phase < .8:
                continue
            u = (phase-.8)/.2
            stride = (np.r_[cmd[:2],0.]+cmd[2]*np.cross([0.,0.,1.],self.nominal[leg]))*self.cycle_s*.8
            length = np.linalg.norm(stride[:2])
            if length > .035:
                stride *= .035/length
            delta = correction @ (ramp*stride*(clearance_along(phase)[0]-recovery_along(u)))
            mount_rotation = rz(MOUNTS[leg]["yaw"])
            changed[index] = inverse(forward(changed[index])+mount_rotation.T@delta)
        return changed.ravel()
