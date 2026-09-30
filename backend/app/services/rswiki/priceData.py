import asyncio
import logging
from datetime import datetime, timezone

import requests
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.priceDataModel import PriceDataModel
from app.schemas.rswiki.priceData import PriceDataSchemaCreate
from app.services.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

BASE_DATA_URL = "https://chisel.weirdgloop.org/gazproj/gazbot/os_dump.json"

# asyncpg allows at most 32767 bind parameters per statement (14 columns per row)
INSERT_CHUNK_SIZE = 1000

# Non-item keys in the dump, both Unix epoch seconds
JAGEX_TIMESTAMP_KEY = "%JAGEX_TIMESTAMP%"  # when Jagex published the GE prices
UPDATE_DETECTED_KEY = "%UPDATE_DETECTED%"  # when the wiki noticed the update

"""
EXAMPLE DATA STRUCTURE FROM RSWIKI API:

"10344": {
    "examine": "Fabulously ancient mage protection enchanted in the 3rd Age.",
    "id": 10344,
    "members": true,
    "lowalch": 20200,
    "limit": 8,
    "value": 50500,
    "highalch": 30300,
    "icon": "3rd Age amulet.png",
    "name": "3rd Age amulet",
    "price": 43791831,
    "last": 43791831,
    "volume": 16
  }

The dump also holds the non-item keys "%JAGEX_TIMESTAMP%": 1790795575 and
"%UPDATE_DETECTED%": 1790795704.08317, which are stamped onto every row.
"""

class RSWikiPriceData(BaseCollector):
    """Appends one row per item each time Jagex publishes new GE prices (~daily)."""
    name = "rswiki_price_data"
    # Jagex's update time drifts, so poll often; unchanged dumps are skipped
    interval = 30 * 60

    def __init__(self):
        super().__init__()
        self.base_url = BASE_DATA_URL

    def fetch_price_data(self) -> dict:
        """Fetches the latest price data from the RSWiki API"""
        response = requests.get(
            self.base_url,
            headers={"User-Agent": settings.USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _epoch_to_utc(value) -> datetime:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)

    @classmethod
    def parse_price_data(cls, raw: dict) -> list[PriceDataSchemaCreate]:
        """Validate each item in the dump, stamping it with the dump's update times."""
        jagex_timestamp = cls._epoch_to_utc(raw[JAGEX_TIMESTAMP_KEY])
        update_detected = cls._epoch_to_utc(raw[UPDATE_DETECTED_KEY])

        items = []
        for key, value in raw.items():
            if not isinstance(value, dict):
                continue
            try:
                items.append(PriceDataSchemaCreate.model_validate({
                    **value,
                    "jagex_timestamp": jagex_timestamp,
                    "update_detected": update_detected,
                }))
            except ValueError:
                logger.warning("skipping invalid item %s", key, exc_info=True)
        return items

    async def collect(self, db: AsyncSession) -> None:
        # requests is blocking, so keep it off the event loop
        raw = await asyncio.to_thread(self.fetch_price_data)
        jagex_timestamp = self._epoch_to_utc(raw[JAGEX_TIMESTAMP_KEY])

        latest = await db.scalar(select(func.max(PriceDataModel.jagex_timestamp)))
        if latest is not None and jagex_timestamp <= latest:
            logger.info("price data unchanged since %s, skipping", latest.isoformat())
            return

        rows = [item.model_dump() for item in self.parse_price_data(raw)]
        for start in range(0, len(rows), INSERT_CHUNK_SIZE):
            stmt = insert(PriceDataModel).values(rows[start:start + INSERT_CHUNK_SIZE])
            # Existing rows are history; never overwrite them
            await db.execute(stmt.on_conflict_do_nothing(
                index_elements=[PriceDataModel.id, PriceDataModel.jagex_timestamp],
            ))
        await db.commit()
        logger.info("inserted %d items for Jagex update %s", len(rows), jagex_timestamp.isoformat())

if __name__ == "__main__":
    price_data_service = RSWikiPriceData()
    items = price_data_service.parse_price_data(price_data_service.fetch_price_data())
    print(len(items))
    print(items[0])
