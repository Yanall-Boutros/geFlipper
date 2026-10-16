# Relative volume: this update's volume over the average of the previous
# PERIOD updates. A value well above 1 flags a volume spike; well below 1
# flags volume drying up (the "volume check" in docs/indicators.md).
from typing import Any

from app.services.indicators.base import Indicator, Point

PERIOD = 20


class RelativeVolume(Indicator):
    window = PERIOD + 1

    def compute(
        self, points: list[Point], prev: dict[str, Any] | None
    ) -> dict[str, Any]:
        if len(points) < PERIOD + 1:
            return {"rel_volume": None}
        average = sum(point.volume for point in points[-PERIOD - 1 : -1]) / PERIOD
        if average == 0:
            return {"rel_volume": None}
        return {"rel_volume": points[-1].volume / average}
