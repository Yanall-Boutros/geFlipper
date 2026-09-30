import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.lifecycle import LifecycleTask
from app.services.rswiki.priceData import RSWikiPriceData

logging.basicConfig(level=logging.INFO)


def build_tasks() -> list[LifecycleTask]:
    """Every background task that runs for the lifetime of the app."""
    if not settings.ENABLE_COLLECTORS:
        return []
    return [
        RSWikiPriceData(),
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = build_tasks()
    for task in tasks:
        task.start()
    app.state.tasks = tasks
    yield
    await asyncio.gather(*(task.stop() for task in tasks))


app = FastAPI(title="geFlipper", lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")
