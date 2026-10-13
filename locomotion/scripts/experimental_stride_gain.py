"""Experimental translational geometric stride gain on clearance recovery.

Only the internal geometric command's vx/vy are multiplied. Requested command,
yaw command, observations, acceptance, phase, lift, attitude and servo settings
are unchanged. Inherited position_targets computes its support/gravity bias
from the resulting geometric joint targets, so the load estimate uses the same
modified feet. That load redistribution is a consequence of the geometry
change, not a separately adjusted gain or feedforward parameter.
"""
from __future__ import annotations

import numpy as np
from experimental_clearance_recovery import ClearanceWindowCrawl


class TranslationGainClearanceCrawl(ClearanceWindowCrawl):
    """Use the requested command only, with no simulated truth feedback."""

    def __init__(self,*args,translational_stride_gain=1.,**kwargs):
        if translational_stride_gain not in (1.,1.15):
            raise ValueError("This bounded factorial owns stride gains 1.0 and 1.15")
        self.translational_stride_gain = float(translational_stride_gain)
        super().__init__(*args,**kwargs)

    def effective_geometric_command(self,command):
        value = np.asarray(command,dtype=float).copy()
        if value.shape!=(3,) or not np.isfinite(value).all():
            raise ValueError("command must contain finite vx, vy, yaw_rate")
        value[:2] *= self.translational_stride_gain
        return value

    def targets(self,time_s,command,attitude=None):
        # Each inherited horizontal construction receives the same command.
        # position_targets passes its computed q into the support estimate;
        # the geometric gain is therefore applied once, not again for bias.
        effective = self.effective_geometric_command(command)
        return super().targets(time_s,effective,attitude)
