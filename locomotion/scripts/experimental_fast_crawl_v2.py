"""One experimental change: scale common body-shift amplitude with cadence.

The frozen prior fast controller and its receipts are retained. Requested
speed, recovery/clearance window, gain, lift and motor configuration remain
identical to their matched fast-reference profiles.
"""
from experimental_fast_crawl import FastClearanceCrawl


class CadenceShiftFastCrawl(FastClearanceCrawl):
    def __init__(self, cycle_s=1.2, shift_m=None, translational_stride_gain=1.15, config=None):
        scaled = .005*cycle_s/3.2
        selected = scaled if shift_m is None else float(shift_m)
        if selected not in (.005, scaled):
            raise ValueError("Bounded shift is .005 m or .005*cycle_s/3.2")
        super().__init__(cycle_s=cycle_s, translational_stride_gain=translational_stride_gain, config=config)
        self.shift_m = selected
