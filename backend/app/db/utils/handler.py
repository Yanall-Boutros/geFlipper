# Base Class for each database handler, providing common CRUD operations
# A pydantic model will be used to validate the data before passing it to the handler
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

class BaseHandler:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(self, model_instance):
        """Create a new record in the database."""
        self.db_session.add(model_instance)
        await self.db_session.commit()
        await self.db_session.refresh(model_instance)
        return model_instance

    async def read(self, model_class, record_id):
        """Read a record from the database by its ID."""
        return await self.db_session.get(model_class, record_id)

    async def update(self, model_instance):
        """Update an existing record in the database."""
        await self.db_session.commit()
        await self.db_session.refresh(model_instance)
        return model_instance

    async def delete(self, model_instance):
        """Delete a record from the database."""
        await self.db_session.delete(model_instance)
        await self.db_session.commit()

    async def list(self, model_class, offset: int = 0, limit: int = 100, order_by=None):
        """Read a page of records, ordered by `order_by` (defaults to the primary key)."""
        if order_by is None:
            order_by = model_class.__mapper__.primary_key
        stmt = select(model_class).order_by(*order_by).offset(offset).limit(limit)
        result = await self.db_session.scalars(stmt)
        return result.all()

    async def count(self, model_class):
        """Count every record of a model."""
        return await self.db_session.scalar(select(func.count()).select_from(model_class))
