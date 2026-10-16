# Volume profile over recent updates: traded volume per price bucket, the point
# of control (busiest bucket) and the value area holding VALUE_AREA of volume.
from typing import Any

from app.services.indicators.base import Indicator, Point

PERIOD = 30
BUCKETS = 24
VALUE_AREA = 0.7

EMPTY = {"vp_poc": None, "vp_vah": None, "vp_val": None}


def volume_profile(points: list[Point]) -> dict[str, float] | None:
    """POC, value-area high and low for `points`. None if nothing traded."""
    total = sum(point.volume for point in points)
    if total == 0:
        return None
    low = min(point.price for point in points)
    high = max(point.price for point in points)
    if high == low:
        return {"vp_poc": low, "vp_vah": low, "vp_val": low}

    width = (high - low) / BUCKETS
    volumes = [0.0] * BUCKETS
    for point in points:
        volumes[min(int((point.price - low) / width), BUCKETS - 1)] += point.volume

    poc = volumes.index(max(volumes))
    bottom = top = poc
    covered = volumes[poc]
    # Grow the value area toward the busier neighbour until it holds enough volume
    while covered < VALUE_AREA * total:
        below = volumes[bottom - 1] if bottom > 0 else -1
        above = volumes[top + 1] if top < BUCKETS - 1 else -1
        if above >= below:
            top += 1
            covered += above
        else:
            bottom -= 1
            covered += below

    return {
        "vp_poc": low + (poc + 0.5) * width,
        "vp_vah": low + (top + 1) * width,
        "vp_val": low + bottom * width,
    }


class VolumeProfile(Indicator):
    window = PERIOD

    def compute(
        self, points: list[Point], prev: dict[str, Any] | None
    ) -> dict[str, Any]:
        if len(points) < PERIOD:
            return dict(EMPTY)
        return volume_profile(points) or dict(EMPTY)
