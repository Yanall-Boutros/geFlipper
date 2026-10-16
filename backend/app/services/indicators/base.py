# Shared types for indicators. Each indicator is pure: it gets an item's recent
# price points and its previous indicator row, and returns new column values.
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, NamedTuple


class Point(NamedTuple):
    """One priced update of an item. volume is 0 when the dump leaves it out."""

    jagex_timestamp: datetime
    price: float
    volume: float


class Indicator(ABC):
    # How many of the latest points compute() needs, the current one included
    window: int = 1

    @abstractmethod
    def compute(
        self, points: list[Point], prev: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Column values for the last point in `points` (oldest first).

        `points` holds up to `window` points; fewer while history builds up.
        `prev` is the item's previous item_indicators row, or None for its first.
        """
