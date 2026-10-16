import asyncio
from datetime import timedelta

import pytest
from app.models import ItemIndicatorsModel, PriceDataModel
from app.services.indicators.base import Indicator
from app.services.indicators.engine import IndicatorEngine
from sqlalchemy import func, select

from tests.conftest import JAGEX_TIMESTAMP, price_row

DAYS = [JAGEX_TIMESTAMP + timedelta(days=i) for i in range(4)]


class Recorder(Indicator):
    """Records what the engine passes in, and adds no columns."""

    def __init__(self, window: int):
        self.window = window
        self.calls = []

    def compute(self, points, prev):
        self.calls.append((points, prev))
        return {}


async def add_prices(db, *rows):
    db.add_all(PriceDataModel(**row) for row in rows)
    await db.commit()


async def indicator_rows(db):
    result = await db.scalars(
        select(ItemIndicatorsModel).order_by(
            ItemIndicatorsModel.jagex_timestamp, ItemIndicatorsModel.id
        )
    )
    return [(row.id, row.samples) for row in result]


def engine_for(session_factory, *indicators):
    return IndicatorEngine(
        indicators=list(indicators),
        event=asyncio.Event(),
        session_factory=session_factory,
    )


async def test_processes_every_update_in_order(db, session_factory):
    await add_prices(
        db, *(price_row(1, day) for day in DAYS[:3]), price_row(2, DAYS[1])
    )
    engine = engine_for(session_factory)

    assert await engine.process_pending(db) == 3
    assert await indicator_rows(db) == [(1, 1), (1, 2), (2, 1), (1, 3)]


async def test_rerun_adds_nothing(db, session_factory):
    await add_prices(db, price_row(1, DAYS[0]))
    engine = engine_for(session_factory)
    await engine.process_pending(db)

    assert await engine.process_pending(db) == 0
    assert await db.scalar(select(func.count()).select_from(ItemIndicatorsModel)) == 1


async def test_only_new_updates_are_processed(db, session_factory):
    engine = engine_for(session_factory)
    await add_prices(db, price_row(1, DAYS[0]))
    await engine.process_pending(db)

    await add_prices(db, price_row(1, DAYS[1]))
    assert await engine.process_pending(db) == 1
    assert await indicator_rows(db) == [(1, 1), (1, 2)]


async def test_reprocessing_an_update_is_idempotent(db, session_factory):
    await add_prices(db, price_row(1, DAYS[0]))
    engine = engine_for(session_factory)
    # Use the timestamp as the database returns it (SQLite drops the timezone)
    [update] = await engine.pending_timestamps(db)
    await engine.process_update(db, update)
    await engine.process_update(db, update)
    assert await indicator_rows(db) == [(1, 1)]


async def test_untraded_items_are_skipped(db, session_factory):
    await add_prices(
        db,
        price_row(1, DAYS[0]),
        price_row(1, DAYS[1], price=None),
        price_row(1, DAYS[2]),
    )
    await engine_for(session_factory).process_pending(db)
    # No row for the unpriced update, and it doesn't count as a sample
    assert await indicator_rows(db) == [(1, 1), (1, 2)]


async def test_indicators_get_window_and_previous_row(db, session_factory):
    await add_prices(
        db,
        *(
            price_row(1, day, price=10 * (i + 1), volume=None)
            for i, day in enumerate(DAYS)
        ),
    )
    recorder = Recorder(window=2)
    await engine_for(session_factory, recorder).process_pending(db)

    first_points, first_prev = recorder.calls[0]
    assert [p.price for p in first_points] == [10.0]
    assert first_prev is None

    last_points, last_prev = recorder.calls[-1]
    # Limited to the window, oldest first; missing volume reads as 0
    assert [(p.price, p.volume) for p in last_points] == [(30.0, 0.0), (40.0, 0.0)]
    assert last_prev["samples"] == 3


def test_window_size_is_largest_indicator_window():
    assert IndicatorEngine(indicators=[]).window_size == 1
    engine = IndicatorEngine(indicators=[Recorder(3), Recorder(7)])
    assert engine.window_size == 7


async def test_run_waits_for_signal(session_factory):
    engine = engine_for(session_factory)
    runs = []

    async def fake_process(db):
        runs.append(db)
        return 0

    engine.process_pending = fake_process
    engine.start()
    await asyncio.sleep(0.01)
    assert len(runs) == 1

    engine.event.set()
    await asyncio.sleep(0.01)
    assert len(runs) == 2
    await engine.stop()


async def test_run_survives_failures_and_falls_back_to_interval(
    session_factory, caplog
):
    engine = engine_for(session_factory)
    engine.fallback_interval = 0.01
    runs = []

    async def failing(db):
        runs.append(db)
        raise RuntimeError("boom")

    engine.process_pending = failing
    engine.start()
    await asyncio.sleep(0.05)
    await engine.stop()
    assert len(runs) >= 2
    assert "indicator engine failed" in caplog.text


@pytest.fixture(autouse=True)
def _quiet_default_event():
    # The shared event is process-wide; keep tests from leaking a set flag
    from app.core.events import price_data_updated

    yield
    price_data_updated.clear()
