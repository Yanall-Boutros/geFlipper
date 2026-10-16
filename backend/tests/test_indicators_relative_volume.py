import pytest
from app.services.indicators.engine import INDICATORS
from app.services.indicators.relative_volume import RelativeVolume

from tests.indicator_helpers import points


def test_registered():
    assert any(isinstance(indicator, RelativeVolume) for indicator in INDICATORS)


def test_needs_twenty_previous_updates():
    row = RelativeVolume().compute(points([1] * 20, volumes=[1] * 20), None)
    assert row == {"rel_volume": None}


def test_spike():
    row = RelativeVolume().compute(points([1] * 21, volumes=[10] * 20 + [30]), None)
    assert row["rel_volume"] == pytest.approx(3)


def test_no_previous_volume():
    row = RelativeVolume().compute(points([1] * 21, volumes=[0] * 20 + [5]), None)
    assert row == {"rel_volume": None}
