"""Shared benchmark metrics used by runners and report generators."""
from __future__ import annotations

import math


def percentile(values, p: float):
    """Return the nearest-rank percentile, or ``None`` for no samples."""
    xs = sorted(x for x in values if x is not None)
    if not xs:
        return None
    if not 0 <= p <= 1:
        raise ValueError(f"percentile must be in [0, 1], got {p}")
    rank = max(1, min(len(xs), math.ceil(p * len(xs))))
    return xs[rank - 1]
