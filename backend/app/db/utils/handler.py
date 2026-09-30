# Base Class for each database handler, providing common CRUD operations
# A pydantic model will be used to validate the data before passing it to the handler
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
