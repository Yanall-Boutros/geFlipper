# Background task that appends a row of indicators per item for every Jagex
# update in price_data, as soon as the collector signals new data.
import asyncio
import logging
from collections import defaultdict
from contextlib import suppress
from datetime import datetime
from typing import Any

from sqlalchemy import distinct, func, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.events import price_data_updated
from app.core.lifecycle import LifecycleTask
from app.db.database import SessionLocal
from app.models import ItemIndicatorsModel, PriceDataModel
from app.services.indicators.base import Indicator, Point
from app.services.indicators.ema import EMA
from app.services.indicators.relative_volume import RelativeVolume
from app.services.indicators.rsi import RSI
from app.services.indicators.stochastic import Stochastic
from app.services.indicators.volume_profile import VolumeProfile
from app.services.indicators.vwap import VWAP

logger = logging.getLogger(__name__)

# Every indicator the engine computes, in column order
INDICATORS: list[Indicator] = [
    EMA(),
    RSI(),
    Stochastic(),
    VWAP(),
    VolumeProfile(),
    RelativeVolume(),
]

# Rows per INSERT; keeps bind parameters well under asyncpg's 32767 limit
INSERT_CHUNK_SIZE = 1000


class IndicatorEngine(LifecycleTask):
    name = "indicator_engine"
    # Catch up at least this often (seconds) in case a signal is missed
    fallback_interval = 60 * 60

    def __init__(
        self,
        indicators: list[Indicator] | None = None,
        event: asyncio.Event = price_data_updated,
        session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
    ):
        super().__init__()
        self.indicators = INDICATORS if indicators is None else indicators
        self.event = event
        self.session_factory = session_factory

    @property
    def window_size(self) -> int:
        return max((indicator.window for indicator in self.indicators), default=1)

    async def run(self) -> None:
        """Process pending updates, then sleep until new data is signalled."""
        while True:
            self.event.clear()
            try:
                async with self.session_factory() as db:
                    await self.process_pending(db)
            except Exception:
                logger.exception("indicator engine failed")
            with suppress(TimeoutError):
                await asyncio.wait_for(self.event.wait(), self.fallback_interval)

    async def process_pending(self, db: AsyncSession) -> int:
        """Compute every update newer than the latest indicators, oldest first."""
        pending = await self.pending_timestamps(db)
        for jagex_timestamp in pending:
            await self.process_update(db, jagex_timestamp)
        return len(pending)

    async def pending_timestamps(self, db: AsyncSession) -> list[datetime]:
        latest = await db.scalar(select(func.max(ItemIndicatorsModel.jagex_timestamp)))
        stmt = select(distinct(PriceDataModel.jagex_timestamp)).order_by(
            PriceDataModel.jagex_timestamp
        )
        if latest is not None:
            stmt = stmt.where(PriceDataModel.jagex_timestamp > latest)
        return list(await db.scalars(stmt))

    async def process_update(self, db: AsyncSession, jagex_timestamp: datetime) -> None:
        """Append one indicator row for every item priced in this update."""
        windows = await self.load_windows(db, jagex_timestamp)
        previous = await self.load_previous(db, jagex_timestamp)

        rows = []
        for item_id, points in windows.items():
            prev = previous.get(item_id)
            row: dict[str, Any] = {
                "id": item_id,
                "jagex_timestamp": jagex_timestamp,
                "samples": (prev["samples"] if prev else 0) + 1,
            }
            for indicator in self.indicators:
                row.update(indicator.compute(points, prev))
            rows.append(row)

        insert = (sqlite if db.bind.dialect.name == "sqlite" else postgresql).insert
        for start in range(0, len(rows), INSERT_CHUNK_SIZE):
            stmt = insert(ItemIndicatorsModel).values(
                rows[start : start + INSERT_CHUNK_SIZE]
            )
            await db.execute(stmt.on_conflict_do_nothing())
        await db.commit()
        logger.info(
            "computed indicators for %d items at %s",
            len(rows),
            jagex_timestamp.isoformat(),
        )

    async def load_windows(
        self, db: AsyncSession, jagex_timestamp: datetime
    ) -> dict[int, list[Point]]:
        """The latest `window_size` priced points per item, oldest first.

        Only items with a price in this update are returned.
        """
        rank = (
            func.row_number()
            .over(
                partition_by=PriceDataModel.id,
                order_by=PriceDataModel.jagex_timestamp.desc(),
            )
            .label("rank")
        )
        ranked = (
            select(
                PriceDataModel.id,
                PriceDataModel.jagex_timestamp,
                PriceDataModel.price,
                PriceDataModel.volume,
                rank,
            )
            .where(
                PriceDataModel.jagex_timestamp <= jagex_timestamp,
                PriceDataModel.price.is_not(None),
            )
            .subquery()
        )
        stmt = (
            select(
                ranked.c.id, ranked.c.jagex_timestamp, ranked.c.price, ranked.c.volume
            )
            .where(ranked.c.rank <= self.window_size)
            .order_by(ranked.c.id, ranked.c.jagex_timestamp)
        )
        windows: dict[int, list[Point]] = defaultdict(list)
        for item_id, timestamp, price, volume in await db.execute(stmt):
            windows[item_id].append(Point(timestamp, float(price), float(volume or 0)))
        return {
            item_id: points
            for item_id, points in windows.items()
            if points[-1].jagex_timestamp == jagex_timestamp
        }

    async def load_previous(
        self, db: AsyncSession, jagex_timestamp: datetime
    ) -> dict[int, dict[str, Any]]:
        """Each item's latest indicator row before this update."""
        model = ItemIndicatorsModel
        rank = (
            func.row_number()
            .over(partition_by=model.id, order_by=model.jagex_timestamp.desc())
            .label("rank")
        )
        ranked = (
            select(model, rank)
            .where(model.jagex_timestamp < jagex_timestamp)
            .subquery()
        )
        columns = [ranked.c[column.name] for column in model.__table__.columns]
        result = await db.execute(select(*columns).where(ranked.c.rank == 1))
        return {row["id"]: dict(row) for row in result.mappings()}
