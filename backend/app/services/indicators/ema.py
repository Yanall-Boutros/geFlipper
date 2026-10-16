# Exponential moving averages, and an envelope around the fastest one.
# Mean reversion signal from docs/indicators.md: price below the lower envelope
# suggests a dip, above the upper envelope suggests it will fall back.
from typing import Any

from app.services.indicators.base import Indicator, Point

PERIODS = (5, 20, 200)
ENVELOPE_PERIOD = 5
# Envelope half-width as a fraction of the EMA
ENVELOPE_PCT = 0.02


def ema_step(prev: float | None, price: float, period: int) -> float:
    """The next EMA value. The first value is the price itself."""
    if prev is None:
        return price
    return prev + 2 / (period + 1) * (price - prev)


class EMA(Indicator):
    window = 1

    def compute(
        self, points: list[Point], prev: dict[str, Any] | None
    ) -> dict[str, Any]:
        price = points[-1].price
        prev = prev or {}
        row = {f"ema_{n}": ema_step(prev.get(f"ema_{n}"), price, n) for n in PERIODS}
        middle = row[f"ema_{ENVELOPE_PERIOD}"]
        row["env_upper"] = middle * (1 + ENVELOPE_PCT)
        row["env_lower"] = middle * (1 - ENVELOPE_PCT)
        return row
