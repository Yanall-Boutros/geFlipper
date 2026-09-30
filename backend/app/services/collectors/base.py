# Base class for background collectors: fetch data on a fixed interval and
# write it to the database. Subclasses set name/interval and implement collect().
import asyncio
import logging
from abc import abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.lifecycle import LifecycleTask
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)


class BaseCollector(LifecycleTask):
    interval: float  # seconds between the start of one run and the next

    @abstractmethod
    async def collect(self, db: AsyncSession) -> None:
        """Fetch data and write it using the given session."""

    async def run_once(self) -> None:
        """Run a single collection in its own session."""
        async with SessionLocal() as db:
            await self.collect(db)

    async def run(self) -> None:
        """Collect every `interval` seconds. A failed run is logged, never raised."""
        loop = asyncio.get_running_loop()
        while True:
            started = loop.time()
            try:
                await self.run_once()
            except Exception:
                logger.exception("collector %s failed", self.name)
            elapsed = loop.time() - started
            await asyncio.sleep(max(0.0, self.interval - elapsed))
