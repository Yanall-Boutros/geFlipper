from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.utils.handler import BaseHandler
from app.models import ItemIndicatorsModel, PriceDataModel
from app.schemas.indicators import IndicatorSchema
from app.schemas.pagination import Page
from app.schemas.rswiki.priceData import PriceDataSchema, PricePointSchema

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/{item_id}", response_model=PriceDataSchema)
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
    """The latest snapshot of a single item."""
    latest = await BaseHandler(db).list(
        PriceDataModel,
        limit=1,
        order_by=[PriceDataModel.jagex_timestamp.desc()],
        filters=[PriceDataModel.id == item_id],
    )
    if not latest:
        raise HTTPException(status_code=404, detail="Item not found")
    return latest[0]


async def item_time_series(
    db: AsyncSession,
    model,
    item_id: int,
    start: datetime | None,
    end: datetime | None,
    offset: int,
    limit: int,
) -> Page:
    """A page of an item's rows in `model`, oldest first, within [start, end]."""
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start must not be after end")

    item_filter = model.id == item_id
    filters = [item_filter]
    if start:
        filters.append(model.jagex_timestamp >= start)
    if end:
        filters.append(model.jagex_timestamp <= end)

    handler = BaseHandler(db)
    total = await handler.count(model, filters=filters)
    # An empty range is fine, an item with no rows at all is not
    if total == 0 and await handler.count(model, filters=[item_filter]) == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    items = await handler.list(
        model,
        offset=offset,
        limit=limit,
        order_by=[model.jagex_timestamp],
        filters=filters,
    )
    return Page(items=items, total=total, offset=offset, limit=limit)


START = Query(None, description="Earliest Jagex timestamp, inclusive")
END = Query(None, description="Latest Jagex timestamp, inclusive")
OFFSET = Query(0, ge=0)
LIMIT = Query(100, ge=1, le=1000)


@router.get("/{item_id}/history", response_model=Page[PricePointSchema])
async def get_item_history(
    item_id: int,
    start: datetime | None = START,
    end: datetime | None = END,
    offset: int = OFFSET,
    limit: int = LIMIT,
    db: AsyncSession = Depends(get_db),
):
    """An item's price history, oldest first, optionally limited to [start, end]."""
    return await item_time_series(
        db, PriceDataModel, item_id, start, end, offset, limit
    )


@router.get("/{item_id}/indicators", response_model=Page[IndicatorSchema])
async def get_item_indicators(
    item_id: int,
    start: datetime | None = START,
    end: datetime | None = END,
    offset: int = OFFSET,
    limit: int = LIMIT,
    db: AsyncSession = Depends(get_db),
):
    """An item's indicators per Jagex update, oldest first, within [start, end].

    Values are NULL until the item has enough history for that indicator.
    """
    return await item_time_series(
        db, ItemIndicatorsModel, item_id, start, end, offset, limit
    )
