from datetime import timedelta

import pytest
from app.models import PriceDataModel
from app.schemas.indicators import IndicatorSchema
from app.services.indicators.engine import IndicatorEngine

from tests.conftest import JAGEX_TIMESTAMP, price_row

# Enough daily updates for every indicator except EMA-200 to be warm
UPDATES = 31
DAYS = [JAGEX_TIMESTAMP + timedelta(days=i) for i in range(UPDATES)]


@pytest.fixture
async def computed(db, session_factory):
    """Item 1 with a zig-zag price over UPDATES days; indicators computed."""
    db.add_all(
        PriceDataModel(
            **price_row(1, day, price=1000 + (i % 5) * 10 + i, volume=10 + i % 3)
        )
        for i, day in enumerate(DAYS)
    )
    db.add(PriceDataModel(**price_row(2, DAYS[0])))
    await db.commit()
    engine = IndicatorEngine(session_factory=session_factory)
    assert await engine.process_pending(db) == UPDATES


async def test_engine_fills_every_indicator(client, computed):
    body = (
        await client.get("/api/v1/items/1/indicators", params={"offset": UPDATES - 1})
    ).json()
    [latest] = body["items"]
    assert latest["samples"] == UPDATES
    assert set(latest) == set(IndicatorSchema.model_fields)
    assert all(value is not None for value in latest.values())


async def test_early_rows_are_partial(client, computed):
    first = (await client.get("/api/v1/items/1/indicators")).json()["items"][0]
    assert first["samples"] == 1
    assert first["ema_5"] == first["ema_200"]
    assert first["rsi_14"] is None
    assert first["vp_poc"] is None


async def test_indicator_page(client, computed):
    body = (await client.get("/api/v1/items/1/indicators", params={"limit": 5})).json()
    assert body["total"] == UPDATES
    assert [row["samples"] for row in body["items"]] == [1, 2, 3, 4, 5]


async def test_indicator_range(client, computed):
    params = {"start": DAYS[10].isoformat(), "end": DAYS[12].isoformat()}
    body = (await client.get("/api/v1/items/1/indicators", params=params)).json()
    assert [row["samples"] for row in body["items"]] == [11, 12, 13]


async def test_indicators_unknown_item(client, computed):
    response = await client.get("/api/v1/items/42/indicators")
    assert response.status_code == 404


async def test_indicators_bad_range(client, computed):
    params = {"start": DAYS[2].isoformat(), "end": DAYS[1].isoformat()}
    response = await client.get("/api/v1/items/1/indicators", params=params)
    assert response.status_code == 422
