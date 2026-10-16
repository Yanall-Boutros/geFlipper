# Relative Strength Index with Wilder smoothing. The running average gain and
# loss are stored with each row, so each update only needs the previous row.
from typing import Any

from app.services.indicators.base import Indicator, Point

PERIOD = 14

EMPTY = {"rsi_14": None, "rsi_avg_gain": None, "rsi_avg_loss": None}


def rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 50.0 if avg_gain == 0 else 100.0
    return 100 - 100 / (1 + avg_gain / avg_loss)


class RSI(Indicator):
    # PERIOD price changes need PERIOD + 1 prices to seed the averages
    window = PERIOD + 1

    def compute(
        self, points: list[Point], prev: dict[str, Any] | None
    ) -> dict[str, Any]:
        prices = [point.price for point in points]
        if prev and prev.get("rsi_avg_gain") is not None and len(prices) >= 2:
            change = prices[-1] - prices[-2]
            avg_gain = (prev["rsi_avg_gain"] * (PERIOD - 1) + max(change, 0)) / PERIOD
            avg_loss = (prev["rsi_avg_loss"] * (PERIOD - 1) + max(-change, 0)) / PERIOD
        elif len(prices) >= PERIOD + 1:
            changes = [b - a for a, b in zip(prices[-PERIOD - 1 :], prices[-PERIOD:])]
            avg_gain = sum(max(c, 0) for c in changes) / PERIOD
            avg_loss = sum(max(-c, 0) for c in changes) / PERIOD
        else:
            return dict(EMPTY)
        return {
            "rsi_14": rsi_from_averages(avg_gain, avg_loss),
            "rsi_avg_gain": avg_gain,
            "rsi_avg_loss": avg_loss,
        }
