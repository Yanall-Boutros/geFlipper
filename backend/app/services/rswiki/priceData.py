import asyncio
import logging

import requests
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.priceDataModel import PriceDataModel
from app.schemas.rswiki.priceData import PriceDataSchemaCreate
from app.services.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

BASE_DATA_URL = "https://chisel.weirdgloop.org/gazproj/gazbot/os_dump.json"

# asyncpg allows at most 32767 bind parameters per statement (12 columns per row)
UPSERT_CHUNK_SIZE = 1000

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

The dump also holds non-item keys such as "%JAGEX_TIMESTAMP%" and
"%UPDATE_DETECTED%" whose values are numbers, not objects.
"""

class RSWikiPriceData(BaseCollector):
    name = "rswiki_price_data"
    interval = 24 * 60 * 60  # the item catalogue changes slowly; refresh daily

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
    def parse_price_data(raw: dict) -> list[PriceDataSchemaCreate]:
        """Validate each item in the dump, skipping metadata keys and bad items."""
        items = []
        for key, value in raw.items():
            if not isinstance(value, dict):
                continue
            try:
                items.append(PriceDataSchemaCreate.model_validate(value))
            except ValueError:
                logger.warning("skipping invalid item %s", key, exc_info=True)
        return items

    async def collect(self, db: AsyncSession) -> None:
        # requests is blocking, so keep it off the event loop
        raw = await asyncio.to_thread(self.fetch_price_data)
        items = self.parse_price_data(raw)
        rows = [item.model_dump() for item in items]

        for start in range(0, len(rows), UPSERT_CHUNK_SIZE):
            stmt = insert(PriceDataModel).values(rows[start:start + UPSERT_CHUNK_SIZE])
            stmt = stmt.on_conflict_do_update(
                index_elements=[PriceDataModel.id],
                set_={col: stmt.excluded[col] for col in rows[0] if col != "id"},
            )
            await db.execute(stmt)
        await db.commit()
        logger.info("upserted %d items into price_data", len(rows))


if __name__ == "__main__":
    price_data_service = RSWikiPriceData()
    items = price_data_service.parse_price_data(price_data_service.fetch_price_data())
    print(len(items))
    print(items[0])
