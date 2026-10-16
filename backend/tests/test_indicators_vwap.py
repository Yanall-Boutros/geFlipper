import pytest
from app.services.indicators.engine import INDICATORS
from app.services.indicators.vwap import VWAP

from tests.indicator_helpers import points


def test_registered():
    assert any(isinstance(indicator, VWAP) for indicator in INDICATORS)


def test_needs_full_window():
    assert VWAP().compute(points([1] * 19, volumes=[1] * 19), None) == {
        "vwap_20": None,
        "vwap_dev_pct": None,
    }


def test_no_volume():
    row = VWAP().compute(points([1] * 20, volumes=[0] * 20), None)
    assert row["vwap_20"] is None


def test_weighted_by_volume():
    prices = [100] * 19 + [80]
    volumes = [1] * 19 + [19]
    row = VWAP().compute(points(prices, volumes=volumes), None)
    assert row["vwap_20"] == pytest.approx(90)
    assert row["vwap_dev_pct"] == pytest.approx(100 * (80 - 90) / 90)
