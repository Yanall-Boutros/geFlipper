# Builders for indicator unit tests
from datetime import timedelta

from app.services.indicators.base import Point

from tests.conftest import JAGEX_TIMESTAMP


def points(prices, volumes=None) -> list[Point]:
    """Daily points, oldest first. Volume defaults to 1 per update."""
    prices = list(prices)
    volumes = [1] * len(prices) if volumes is None else list(volumes)
    return [
        Point(JAGEX_TIMESTAMP + timedelta(days=i), float(price), float(volume))
        for i, (price, volume) in enumerate(zip(prices, volumes, strict=True))
    ]
