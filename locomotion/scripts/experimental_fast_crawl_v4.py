"""Bounded speed-ceiling preview retaining the selected recovery geometry.

Extend the selected 1.2 s profile to 1.0 and 0.8 s without changing the saved
controller modules. Common body shift follows the same cadence scaling. The
35 mm stride cap, lift, gain, recovery, support and motor model stay intact.
"""
from experimental_fast_crawl_v3 import WideRecoveryFastCrawl


class SpeedCeilingCrawl(WideRecoveryFastCrawl):
    def __init__(self, cycle_s=1.2, shift_m=None, recovery_start=.82,
                 translational_stride_gain=1.15, config=None):
        if cycle_s not in (1.2, 1.0, .8):
            raise ValueError("Speed-ceiling preview cycle must be 1.2, 1.0 or 0.8 s")
        if recovery_start != .82:
            raise ValueError("Speed-ceiling preview retains recovery start .82")
        scaled = .005*cycle_s/3.2
        if shift_m is not None and float(shift_m) != scaled:
            raise ValueError("Speed-ceiling preview shift must equal .005*cycle_s/3.2")
        # Parent validation keeps its receipt-bound cycle choices. Its other
        # initialized state is independent of cadence, so extend that value here.
        super().__init__(cycle_s=1.2, shift_m=.005*1.2/3.2,
                         recovery_start=recovery_start,
                         translational_stride_gain=translational_stride_gain,
                         config=config)
        self.cycle_s = float(cycle_s)
        self.shift_m = scaled

    def uncapped_translation_m_s(self):
        return .035/(.8*self.cycle_s*self.translational_stride_gain)
