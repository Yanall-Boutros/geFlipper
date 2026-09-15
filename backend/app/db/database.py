from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# Async PostgreSQL requires the 'postgresql+asyncpg://' driver scheme
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Automatically tests dead connections
    echo=False
)

SessionLocal = async_sessionmaker(
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession
)