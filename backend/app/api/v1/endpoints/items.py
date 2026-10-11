from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.utils.handler import BaseHandler
from app.models import PriceDataModel
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


@router.get("/{item_id}/history", response_model=Page[PricePointSchema])
async def get_item_history(
    item_id: int,
    start: datetime | None = Query(
        None, description="Earliest Jagex timestamp, inclusive"
    ),
    end: datetime | None = Query(None, description="Latest Jagex timestamp, inclusive"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """An item's price history, oldest first, optionally limited to [start, end]."""
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start must not be after end")

    item_filter = PriceDataModel.id == item_id
    filters = [item_filter]
    if start:
        filters.append(PriceDataModel.jagex_timestamp >= start)
    if end:
        filters.append(PriceDataModel.jagex_timestamp <= end)

    handler = BaseHandler(db)
    total = await handler.count(PriceDataModel, filters=filters)
    # An empty range is fine, an item with no rows at all is not
    if total == 0 and await handler.count(PriceDataModel, filters=[item_filter]) == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    items = await handler.list(
        PriceDataModel,
        offset=offset,
        limit=limit,
        order_by=[PriceDataModel.jagex_timestamp],
        filters=filters,
    )
    return Page(items=items, total=total, offset=offset, limit=limit)
