import pytest
from app.services.indicators.engine import INDICATORS
from app.services.indicators.rsi import RSI, rsi_from_averages

from tests.indicator_helpers import points


def test_registered():
    assert any(isinstance(indicator, RSI) for indicator in INDICATORS)


def test_needs_fifteen_prices_to_seed():
    assert RSI().compute(points(range(14)), None) == {
        "rsi_14": None,
        "rsi_avg_gain": None,
        "rsi_avg_loss": None,
    }


def test_seed_from_window():
    # 10 rises of 2 and 4 falls of 1
    prices = [100]
    for change in [2] * 10 + [-1] * 4:
        prices.append(prices[-1] + change)
    row = RSI().compute(points(prices), None)
    assert row["rsi_avg_gain"] == pytest.approx(20 / 14)
    assert row["rsi_avg_loss"] == pytest.approx(4 / 14)
    assert row["rsi_14"] == pytest.approx(100 - 100 / 6)


def test_wilder_smoothing_from_previous_row():
    prev = {"rsi_avg_gain": 1.0, "rsi_avg_loss": 0.5}
    row = RSI().compute(points([100, 93]), prev)
    assert row["rsi_avg_gain"] == pytest.approx(13 / 14)
    assert row["rsi_avg_loss"] == pytest.approx((0.5 * 13 + 7) / 14)


@pytest.mark.parametrize(
    ("gain", "loss", "expected"), [(0, 0, 50), (1, 0, 100), (0, 1, 0), (1, 1, 50)]
)
def test_rsi_edges(gain, loss, expected):
    assert rsi_from_averages(gain, loss) == pytest.approx(expected)
