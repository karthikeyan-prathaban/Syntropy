from __future__ import annotations

from statistics import median

# 0.6745 converts MAD to a standard-deviation-equivalent scale for normal data.
MAD_SCALE = 0.6745
ROBUST_Z_THRESHOLD = 3.5


def mad(values: list[float], centre: float | None = None) -> float:
    """Median absolute deviation. Unlike stdev, a few huge outliers do not inflate it."""
    if not values:
        return 0.0
    mid = median(values) if centre is None else centre
    return median([abs(v - mid) for v in values])


def robust_z(value: float, values: list[float]) -> float:
    """Modified z-score. Returns 0 when the sample is too small or degenerate."""
    if len(values) < 4:
        return 0.0
    centre = median(values)
    deviation = mad(values, centre)
    if deviation == 0:
        # Every observation is identical; only a different value is notable.
        return 0.0 if value == centre else float("inf") if value > centre else 0.0
    return MAD_SCALE * (value - centre) / deviation


def coefficient_of_variation(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return (variance**0.5) / abs(mean)
