# Rolling volume-weighted average price, and how far the price is from it.
# A price well below VWAP suggests the item is trading at a discount.
from typing import Any

from app.services.indicators.base import Indicator, Point

PERIOD = 20


class VWAP(Indicator):
    window = PERIOD

    def compute(
        self, points: list[Point], prev: dict[str, Any] | None
    ) -> dict[str, Any]:
        total_volume = sum(point.volume for point in points)
        if len(points) < PERIOD or total_volume == 0:
            return {"vwap_20": None, "vwap_dev_pct": None}
        vwap = sum(point.price * point.volume for point in points) / total_volume
        return {
            "vwap_20": vwap,
            "vwap_dev_pct": 100 * (points[-1].price - vwap) / vwap,
        }
