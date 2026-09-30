from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.utils.handler import BaseHandler
from app.models import PriceDataModel
from app.schemas.pagination import Page
from app.schemas.rswiki.priceData import PriceDataSchema

router = APIRouter(prefix="/price-data", tags=["price-data"])

@router.get("", response_model=Page[PriceDataSchema])
async def list_price_data(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """List items from the price_data table, ordered by item id."""
    handler = BaseHandler(db)
    items = await handler.list(PriceDataModel, offset=offset, limit=limit)
    total = await handler.count(PriceDataModel)
    return Page(items=items, total=total, offset=offset, limit=limit)
