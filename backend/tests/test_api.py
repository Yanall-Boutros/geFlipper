import pytest

from app.models import PriceDataModel
from tests.conftest import price_row


@pytest.fixture
async def seeded(db):
    db.add_all(PriceDataModel(**price_row(i)) for i in range(1, 6))
    await db.commit()


async def test_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_price_data_empty(client):
    response = await client.get("/api/v1/price-data")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "offset": 0, "limit": 100}


async def test_price_data_page(client, seeded):
    response = await client.get("/api/v1/price-data", params={"offset": 1, "limit": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert (body["offset"], body["limit"]) == (1, 2)
    assert [item["id"] for item in body["items"]] == [2, 3]


async def test_price_data_item_shape(client, seeded):
    item = (await client.get("/api/v1/price-data", params={"limit": 1})).json()["items"][0]
    expected = price_row(1)
    assert set(item) == set(expected)
    for key in ("id", "name", "examine", "price", "last", "volume", "members", "limit", "icon"):
        assert item[key] == expected[key]


@pytest.mark.parametrize("params", [
    {"offset": -1},
    {"limit": 0},
    {"limit": 1001},
    {"limit": "abc"},
])
async def test_price_data_rejects_bad_params(client, params):
    response = await client.get("/api/v1/price-data", params=params)
    assert response.status_code == 422


async def test_price_data_max_limit(client, seeded):
    response = await client.get("/api/v1/price-data", params={"limit": 1000})
    assert response.status_code == 200
    assert len(response.json()["items"]) == 5
