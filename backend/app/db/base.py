from sqlalchemy.orm import declarative_base

# The unified base class for all database tables
Base = declarative_base()

# Explicitly import your models here so Alembic can track updates
#from app.models.item import Item  # noqa
#from app.models.user import User  # noqa
from models.priceDataModel import PriceDataModel  # noqa