from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.core.config import settings
from app.services.rswiki import priceData
from app.services.rswiki.priceData import (
    BASE_DATA_URL,
    JAGEX_TIMESTAMP_KEY,
    UPDATE_DETECTED_KEY,
    RSWikiPriceData,
)

JAGEX_EPOCH = 1790795575
DETECTED_EPOCH = 1790795704.08317


def item(item_id: int, **overrides) -> dict:
    """One item as it appears in os_dump.json."""
    return {
        "examine": "Fabulously ancient mage protection enchanted in the 3rd Age.",
        "id": item_id,
        "members": True,
        "lowalch": 20200,
        "limit": 8,
        "value": 50500,
        "highalch": 30300,
        "icon": "3rd Age amulet.png",
        "name": "3rd Age amulet",
        "price": 43791831,
        "last": 43791831,
        "volume": 16,
        **overrides,
    }


def dump(*items: dict, jagex=JAGEX_EPOCH, detected=DETECTED_EPOCH) -> dict:
    return {
        JAGEX_TIMESTAMP_KEY: jagex,
        UPDATE_DETECTED_KEY: detected,
        **{str(i["id"]): i for i in items},
    }


# --- parsing ---------------------------------------------------------------

def test_epoch_to_utc():
    assert RSWikiPriceData._epoch_to_utc(0) == datetime(1970, 1, 1, tzinfo=timezone.utc)
    assert RSWikiPriceData._epoch_to_utc("1.5").microsecond == 500000


def test_parse_stamps_update_times():
    [parsed] = RSWikiPriceData.parse_price_data(dump(item(10344)))
    assert parsed.id == 10344
    assert parsed.price == 43791831
    assert parsed.jagex_timestamp == datetime.fromtimestamp(JAGEX_EPOCH, tz=timezone.utc)
    assert parsed.update_detected == datetime.fromtimestamp(DETECTED_EPOCH, tz=timezone.utc)


def test_parse_skips_non_item_keys():
    items = RSWikiPriceData.parse_price_data(dump(item(1), item(2)))
    assert sorted(i.id for i in items) == [1, 2]


def test_parse_accepts_untraded_items():
    untraded = item(5)
    for key in ("price", "last", "volume", "lowalch", "highalch", "limit"):
        del untraded[key]
    [parsed] = RSWikiPriceData.parse_price_data(dump(untraded))
    assert parsed.price is None


def test_parse_skips_invalid_items(caplog):
    bad = item(2)
    del bad["name"]
    items = RSWikiPriceData.parse_price_data(dump(item(1), bad))
    assert [i.id for i in items] == [1]
    assert "skipping invalid item 2" in caplog.text


def test_parse_requires_timestamps():
    raw = dump(item(1))
    del raw[JAGEX_TIMESTAMP_KEY]
    with pytest.raises(KeyError):
        RSWikiPriceData.parse_price_data(raw)


# --- fetching --------------------------------------------------------------

def test_fetch_sends_user_agent(monkeypatch):
    response = MagicMock()
    response.json.return_value = {"ok": True}
    get = MagicMock(return_value=response)
    monkeypatch.setattr(priceData.requests, "get", get)

    assert RSWikiPriceData().fetch_price_data() == {"ok": True}
    get.assert_called_once_with(BASE_DATA_URL, headers={"User-Agent": settings.USER_AGENT}, timeout=30)
    response.raise_for_status.assert_called_once()


def test_fetch_raises_http_errors(monkeypatch):
    response = MagicMock()
    response.raise_for_status.side_effect = priceData.requests.HTTPError("503")
    monkeypatch.setattr(priceData.requests, "get", MagicMock(return_value=response))

    with pytest.raises(priceData.requests.HTTPError):
        RSWikiPriceData().fetch_price_data()


# --- collecting ------------------------------------------------------------

def make_db(latest: datetime | None):
    db = MagicMock()
    db.scalar = AsyncMock(return_value=latest)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


def collector_with(raw: dict) -> RSWikiPriceData:
    collector = RSWikiPriceData()
    collector.fetch_price_data = lambda: raw
    return collector


def inserted_ids(db) -> list[int]:
    ids = []
    for call in db.execute.call_args_list:
        stmt = call.args[0]
        params = stmt.compile(dialect=postgresql.dialect()).params
        ids += [v for k, v in params.items() if k.startswith("id_m") or k == "id"]
    return ids


async def test_collect_inserts_into_empty_table():
    db = make_db(latest=None)
    await collector_with(dump(item(1), item(2))).collect(db)

    assert db.execute.await_count == 1
    assert sorted(inserted_ids(db)) == [1, 2]
    db.commit.assert_awaited_once()


async def test_collect_never_overwrites_history():
    db = make_db(latest=None)
    await collector_with(dump(item(1))).collect(db)

    sql = str(db.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert sql.startswith("INSERT INTO price_data")
    assert "ON CONFLICT (id, jagex_timestamp) DO NOTHING" in sql


async def test_collect_inserts_newer_update():
    older = datetime.fromtimestamp(JAGEX_EPOCH - 86400, tz=timezone.utc)
    db = make_db(latest=older)
    await collector_with(dump(item(1))).collect(db)
    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.parametrize("offset", [0, 60])
async def test_collect_skips_unchanged_dump(offset):
    latest = datetime.fromtimestamp(JAGEX_EPOCH + offset, tz=timezone.utc)
    db = make_db(latest=latest)
    await collector_with(dump(item(1))).collect(db)
    db.execute.assert_not_awaited()
    db.commit.assert_not_awaited()


async def test_collect_chunks_large_dumps(monkeypatch):
    monkeypatch.setattr(priceData, "INSERT_CHUNK_SIZE", 2)
    db = make_db(latest=None)
    await collector_with(dump(*(item(i) for i in range(1, 6)))).collect(db)

    assert db.execute.await_count == 3  # 2 + 2 + 1
    assert sorted(inserted_ids(db)) == [1, 2, 3, 4, 5]
    db.commit.assert_awaited_once()


def test_chunk_size_fits_asyncpg_parameter_limit():
    columns = len(priceData.PriceDataModel.__table__.columns)
    assert priceData.INSERT_CHUNK_SIZE * columns <= 32767


# --- script entry point ----------------------------------------------------

@pytest.mark.filterwarnings("ignore:.*found in sys.modules:RuntimeWarning")
def test_main_block_prints_item_count(monkeypatch, capsys):
    import runpy

    response = MagicMock()
    response.json.return_value = dump(item(1), item(2))
    monkeypatch.setattr(priceData.requests, "get", MagicMock(return_value=response))

    runpy.run_module("app.services.rswiki.priceData", run_name="__main__")

    assert capsys.readouterr().out.splitlines()[0] == "2"
