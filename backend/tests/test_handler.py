from datetime import timedelta

from app.db.utils.handler import BaseHandler
from app.models import PriceDataModel
from tests.conftest import JAGEX_TIMESTAMP, price_row


async def add_rows(db, *rows):
    db.add_all(PriceDataModel(**row) for row in rows)
    await db.commit()


async def test_create_and_read(db):
    handler = BaseHandler(db)
    created = await handler.create(PriceDataModel(**price_row(1)))
    assert created.name == "Item 1"

    found = await handler.read(PriceDataModel, (1, JAGEX_TIMESTAMP))
    assert found is created


async def test_read_missing_returns_none(db):
    assert await BaseHandler(db).read(PriceDataModel, (999, JAGEX_TIMESTAMP)) is None


async def test_update(db):
    handler = BaseHandler(db)
    item = await handler.create(PriceDataModel(**price_row(1)))
    item.price = 555
    await handler.update(item)

    db.expunge_all()
    assert (await handler.read(PriceDataModel, (1, JAGEX_TIMESTAMP))).price == 555


async def test_delete(db):
    handler = BaseHandler(db)
    item = await handler.create(PriceDataModel(**price_row(1)))
    await handler.delete(item)
    assert await handler.count(PriceDataModel) == 0


async def test_count(db):
    handler = BaseHandler(db)
    assert await handler.count(PriceDataModel) == 0
    await add_rows(db, price_row(1), price_row(2), price_row(3))
    assert await handler.count(PriceDataModel) == 3


async def test_list_orders_by_primary_key(db):
    later = JAGEX_TIMESTAMP + timedelta(days=1)
    await add_rows(db, price_row(2, later), price_row(1, later), price_row(2), price_row(1))

    items = await BaseHandler(db).list(PriceDataModel)
    assert [item.id for item in items] == [1, 1, 2, 2]
    # SQLite drops the timezone, so compare without it
    assert [item.jagex_timestamp.replace(tzinfo=None) for item in items[:2]] == [
        JAGEX_TIMESTAMP.replace(tzinfo=None),
        later.replace(tzinfo=None),
    ]


async def test_list_offset_and_limit(db):
    await add_rows(db, *(price_row(i) for i in range(1, 11)))
    items = await BaseHandler(db).list(PriceDataModel, offset=3, limit=4)
    assert [item.id for item in items] == [4, 5, 6, 7]


async def test_list_past_end_is_empty(db):
    await add_rows(db, price_row(1))
    assert await BaseHandler(db).list(PriceDataModel, offset=5) == []


async def test_list_custom_order(db):
    await add_rows(db, price_row(1, price=30), price_row(2, price=10), price_row(3, price=20))
    items = await BaseHandler(db).list(PriceDataModel, order_by=[PriceDataModel.price.desc()])
    assert [item.id for item in items] == [1, 3, 2]
