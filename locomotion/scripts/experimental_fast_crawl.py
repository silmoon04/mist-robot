"""Experimental faster simulation crawl; no physical-robot qualification.

Retain the existing clearance recovery, 5 mm body shift, source torque cap,
sensor contract and position bias. Cadence and translational gain are explicit
controller parameters. Servo command slew is a separate runtime configuration
parameter; this module never changes the source configuration file.
"""
from copy import deepcopy
import numpy as np
from experimental_stride_gain import TranslationGainClearanceCrawl
from locomotion.model import load_config, validate_config


def preview_config(command_speed_rad_s=1.8):
    """Return a validated copy changing only nominal servo target slew."""
    if command_speed_rad_s not in (1.8, 3.0):
        raise ValueError("Bounded preview slew must be 1.8 or 3.0 rad/s")
    config = deepcopy(load_config())
    config["actuator"]["command_speed_rad_s"] = float(command_speed_rad_s)
    return validate_config(config)


class FastClearanceCrawl(TranslationGainClearanceCrawl):
    def __init__(self, cycle_s=3.2, translational_stride_gain=1.15, config=None):
        if cycle_s not in (3.2, 1.6, 1.2):
            raise ValueError("Bounded preview cycle must be 3.2, 1.6 or 1.2 s")
        super().__init__(cycle_s=float(cycle_s), shift_m=.005, lift_m=.012,
                         translational_stride_gain=translational_stride_gain,
                         config=config)

    def stride_cap_ratios(self, command):
        """Use the effective geometry command, keeping yaw unscaled."""
        effective = self.effective_geometric_command(command)
        result = {}
        for leg, nominal in self.nominal.items():
            velocity = np.r_[effective[:2], 0.]+effective[2]*np.cross([0., 0., 1.], nominal)
            length = np.linalg.norm(velocity[:2])*self.cycle_s*.8
            result[leg] = min(1., .035/length) if length else 1.
        return result
