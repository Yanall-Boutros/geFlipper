from sqlalchemy.orm import declarative_base

# The unified base class for all database tables.
# Models are registered for Alembic in app/models/__init__.py
Base = declarative_base()
