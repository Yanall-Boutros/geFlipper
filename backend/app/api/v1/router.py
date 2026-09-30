from fastapi import APIRouter

from app.api.v1.endpoints import priceData

api_router = APIRouter()
api_router.include_router(priceData.router)

@api_router.get("/health")
async def health():
    return {"status": "ok"}
