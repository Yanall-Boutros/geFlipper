import pytest
from app.services.indicators.engine import INDICATORS
from app.services.indicators.stochastic import Stochastic, percent_k

from tests.indicator_helpers import points


def test_registered():
    assert any(isinstance(indicator, Stochastic) for indicator in INDICATORS)


def test_percent_k():
    assert percent_k([10, 20, 15]) == pytest.approx(50)
    assert percent_k([5, 5, 5]) is None


def test_needs_fourteen_prices():
    assert Stochastic().compute(points(range(13)), None) == {
        "stoch_k": None,
        "stoch_d": None,
    }


def test_k_without_enough_for_d():
    row = Stochastic().compute(points(range(14)), None)
    assert row == {"stoch_k": pytest.approx(100), "stoch_d": None}


def test_k_and_d():
    # Rising 0..14, then a drop to 7: %K values 100, 100, 50
    row = Stochastic().compute(points([*range(15), 7]), None)
    assert row["stoch_k"] == pytest.approx(100 * (7 - 2) / (14 - 2))
    ks = [100, 100, 100 * 5 / 12]
    assert row["stoch_d"] == pytest.approx(sum(ks) / 3)


def test_flat_range_has_no_d():
    row = Stochastic().compute(points([5] * 16), None)
    assert row == {"stoch_k": None, "stoch_d": None}
