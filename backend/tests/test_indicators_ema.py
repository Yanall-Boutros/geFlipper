import pytest
from app.services.indicators.ema import EMA, ema_step
from app.services.indicators.engine import INDICATORS

from tests.indicator_helpers import points


def test_registered():
    assert any(isinstance(indicator, EMA) for indicator in INDICATORS)


def test_ema_step_seeds_with_price():
    assert ema_step(None, 42.0, 5) == 42.0


def test_ema_step_sequence():
    # period 3 -> alpha 0.5
    value = None
    for price in (10, 20, 30):
        value = ema_step(value, price, 3)
    assert value == pytest.approx(22.5)


def test_first_row_is_price_with_envelope():
    row = EMA().compute(points([100]), None)
    assert row == {
        "ema_5": 100,
        "ema_20": 100,
        "ema_200": 100,
        "env_upper": pytest.approx(102),
        "env_lower": pytest.approx(98),
    }


def test_continues_from_previous_row():
    prev = {"ema_5": 10.0, "ema_20": 10.0, "ema_200": None}
    row = EMA().compute(points([10, 16]), prev)
    assert row["ema_5"] == pytest.approx(12)  # alpha 1/3
    assert row["ema_20"] == pytest.approx(10 + 6 * 2 / 21)
    # A missing previous value (column added later) reseeds from the price
    assert row["ema_200"] == 16
