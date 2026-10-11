from datetime import timedelta

import pytest
from app.models import PriceDataModel

from tests.conftest import JAGEX_TIMESTAMP, price_row

DAY_1 = JAGEX_TIMESTAMP
DAY_2 = JAGEX_TIMESTAMP + timedelta(days=1)
DAY_3 = JAGEX_TIMESTAMP + timedelta(days=2)


def iso(dt) -> str:
    return dt.isoformat()


def naive(value: str) -> str:
    """Response timestamp without its timezone (SQLite drops it)."""
    return value.removesuffix("Z").split("+")[0]


@pytest.fixture
async def seeded(db):
    # Item 1 has three daily snapshots, inserted out of order; item 2 has one
    db.add_all(
        PriceDataModel(**row)
        for row in (
            price_row(1, DAY_2, price=200),
            price_row(1, DAY_3, price=300, name="Item 1 renamed"),
            price_row(1, DAY_1, price=100),
            price_row(2, DAY_3, price=999),
        )
    )
    await db.commit()


async def test_item_latest_snapshot(client, seeded):
    response = await client.get("/api/v1/items/1")
    assert response.status_code == 200
    body = response.json()
    assert (body["id"], body["price"], body["name"]) == (1, 300, "Item 1 renamed")
    assert naive(body["jagex_timestamp"]) == iso(DAY_3.replace(tzinfo=None))
    assert set(body) == set(price_row(1))


async def test_item_not_found(client, seeded):
    response = await client.get("/api/v1/items/42")
    assert response.status_code == 404


async def test_item_bad_id(client):
    response = await client.get("/api/v1/items/abc")
    assert response.status_code == 422


async def test_history_oldest_first(client, seeded):
    response = await client.get("/api/v1/items/1/history")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert (body["offset"], body["limit"]) == (0, 100)
    assert [point["price"] for point in body["items"]] == [100, 200, 300]


async def test_history_point_shape(client, seeded):
    point = (await client.get("/api/v1/items/2/history")).json()["items"][0]
    assert set(point) == {
        "jagex_timestamp",
        "update_detected",
        "price",
        "last",
        "volume",
    }
    assert point["price"] == 999


async def test_history_pagination(client, seeded):
    body = (
        await client.get("/api/v1/items/1/history", params={"offset": 1, "limit": 1})
    ).json()
    assert body["total"] == 3
    assert [point["price"] for point in body["items"]] == [200]


@pytest.mark.parametrize(
    ("params", "prices"),
    [
        ({"start": iso(DAY_2)}, [200, 300]),
        ({"end": iso(DAY_2)}, [100, 200]),
        ({"start": iso(DAY_2), "end": iso(DAY_2)}, [200]),
    ],
)
async def test_history_range_is_inclusive(client, seeded, params, prices):
    body = (await client.get("/api/v1/items/1/history", params=params)).json()
    assert body["total"] == len(prices)
    assert [point["price"] for point in body["items"]] == prices


async def test_history_empty_range(client, seeded):
    later = DAY_3 + timedelta(days=1)
    response = await client.get("/api/v1/items/1/history", params={"start": iso(later)})
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


async def test_history_unknown_item(client, seeded):
    response = await client.get("/api/v1/items/42/history")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "params",
    [
        {"start": iso(DAY_3), "end": iso(DAY_1)},
        {"start": "yesterday"},
        {"offset": -1},
        {"limit": 0},
        {"limit": 1001},
    ],
)
async def test_history_rejects_bad_params(client, seeded, params):
    response = await client.get("/api/v1/items/1/history", params=params)
    assert response.status_code == 422
