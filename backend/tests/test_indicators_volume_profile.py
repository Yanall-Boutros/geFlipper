import pytest
from app.services.indicators.engine import INDICATORS
from app.services.indicators.volume_profile import (
    BUCKETS,
    VolumeProfile,
    volume_profile,
)

from tests.indicator_helpers import points


def test_registered():
    assert any(isinstance(indicator, VolumeProfile) for indicator in INDICATORS)


def test_needs_full_window():
    row = VolumeProfile().compute(points([1] * 29, volumes=[1] * 29), None)
    assert row == {"vp_poc": None, "vp_vah": None, "vp_val": None}


def test_no_volume():
    row = VolumeProfile().compute(points(range(30), volumes=[0] * 30), None)
    assert row == {"vp_poc": None, "vp_vah": None, "vp_val": None}


def test_flat_price():
    assert volume_profile(points([7, 7], volumes=[1, 2])) == {
        "vp_poc": 7,
        "vp_vah": 7,
        "vp_val": 7,
    }


def test_poc_and_value_area():
    # Prices 0..24 split into 24 buckets of width 1 (24 lands in the top one)
    prices = list(range(25))
    volumes = [1] * 25
    volumes[10] = 40  # busiest bucket
    volumes[11] = 20
    volumes[9] = 15
    profile = volume_profile(points(prices, volumes=volumes))
    assert sum(volumes) == 97  # value area needs 67.9
    # 40 (POC), + 20 above (busier than 15 below), + 15 below = 75
    assert profile["vp_poc"] == pytest.approx(10.5)
    assert profile["vp_vah"] == pytest.approx(12)
    assert profile["vp_val"] == pytest.approx(9)


def test_value_area_grows_to_edges():
    # Even volume: the area has to cover 70% of the buckets
    prices = [i * 1.0 for i in range(BUCKETS)]
    profile = volume_profile(points(prices, volumes=[1] * BUCKETS))
    covered = (profile["vp_vah"] - profile["vp_val"]) / ((BUCKETS - 1) / BUCKETS)
    assert covered >= 0.7 * BUCKETS


def test_full_window_uses_profile():
    row = VolumeProfile().compute(points([5] * 30, volumes=[1] * 30), None)
    assert row == {"vp_poc": 5, "vp_vah": 5, "vp_val": 5}
