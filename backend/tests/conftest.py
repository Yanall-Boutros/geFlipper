# Shared fixtures. Tests run against an in-memory SQLite database, so no
# Postgres is needed. Anything Postgres-specific is tested with mocks instead.
import os

# Settings are read at import time, so set these before importing app.*
os.environ.setdefault("DB_PASS", "test")
os.environ["ENABLE_COLLECTORS"] = "0"

from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: registers models on Base.metadata
from app.api.deps import get_db
from app.db.base import Base
from app.main import app as fastapi_app

JAGEX_TIMESTAMP = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
UPDATE_DETECTED = datetime(2026, 9, 30, 12, 2, tzinfo=timezone.utc)


def price_row(item_id: int, jagex_timestamp: datetime = JAGEX_TIMESTAMP, **overrides) -> dict:
    """Column values for one price_data row."""
    return {
        "id": item_id,
        "jagex_timestamp": jagex_timestamp,
        "update_detected": UPDATE_DETECTED,
        "name": f"Item {item_id}",
        "examine": "An item.",
        "price": 100,
        "last": 90,
        "volume": 5,
        "members": False,
        "lowalch": 1,
        "highalch": 2,
        "limit": 10,
        "value": 3,
        "icon": f"Item {item_id}.png",
        **overrides,
    }


@pytest.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
async def db(session_factory):
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(session_factory):
    """HTTP client for the app, with get_db pointed at the SQLite database."""
    async def override_get_db():
        async with session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        yield client
    fastapi_app.dependency_overrides.clear()
