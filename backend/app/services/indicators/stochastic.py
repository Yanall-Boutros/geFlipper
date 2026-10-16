# Stochastic oscillator (%K, %D). The GE data has one price per update and no
# high/low, so the range comes from the last K_PERIOD prices.
from typing import Any

from app.services.indicators.base import Indicator, Point

K_PERIOD = 14
D_PERIOD = 3


def percent_k(prices: list[float]) -> float | None:
    """Where the last price sits in the range of `prices`, 0-100. None if flat."""
    low, high = min(prices), max(prices)
    if high == low:
        return None
    return 100 * (prices[-1] - low) / (high - low)


class Stochastic(Indicator):
    # %D averages the last D_PERIOD %K values
    window = K_PERIOD + D_PERIOD - 1

    def compute(
        self, points: list[Point], prev: dict[str, Any] | None
    ) -> dict[str, Any]:
        prices = [point.price for point in points]
        ks = [
            percent_k(prices[end - K_PERIOD : end])
            for end in range(K_PERIOD, len(prices) + 1)
        ]
        stoch_k = ks[-1] if ks else None
        recent = ks[-D_PERIOD:]
        stoch_d = (
            sum(recent) / D_PERIOD
            if len(recent) == D_PERIOD and None not in recent
            else None
        )
        return {"stoch_k": stoch_k, "stoch_d": stoch_d}
