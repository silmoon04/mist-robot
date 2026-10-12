"""Experimental development trajectory; never a frozen controller or policy contract.

The only trajectory change is horizontal swing interpolation. Matching the
stance endpoint velocity should reduce conflicting motion while a toe is still
loaded around release and touchdown. Lift, support weights, mass estimates,
servo limits and sensor use are inherited unchanged from CrawlController.
"""
from __future__ import annotations

import math
import numpy as np
from locomotion.gait import CrawlController, rz
from locomotion.kinematics import forward, inverse
from locomotion.model import LEGS, MOUNTS


def recovery_along(u):
    """Cubic from -.5 to +.5 with endpoint d(along)/du = -.25.

    Swing occupies .2 of the cycle and stance .8. Therefore -.25 in
    swing-u coordinates matches -1/.8 in cycle-phase coordinates.
    The small endpoint overshoot is part of this Hermite construction.
    """
    return -.5-.25*u+3.75*u*u-2.5*u*u*u


class VelocityMatchedCrawl(CrawlController):
    """Use hardware-available command and attitude only; no contact feedback."""

    def targets(self, time_s, command, attitude=None):
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
            old_along = -.5+u*u*(3.-2.*u)
            delta = correction @ (ramp*stride*(recovery_along(u)-old_along))
            mount_rotation = rz(MOUNTS[leg]["yaw"])
            local = forward(changed[index])+mount_rotation.T @ delta
            changed[index] = inverse(local)
        return changed.ravel()
