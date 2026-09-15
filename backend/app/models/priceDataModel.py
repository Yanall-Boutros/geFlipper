from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from db.base import Base

class PriceDataModel(Base):
    __tablename__ = 'price_data'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    examine = Column(String)
    price = Column(Integer)
    last = Column(Integer)
    volume = Column(Integer)
    members = Column(Boolean)
    lowalch = Column(Integer)
    highalch = Column(Integer)
    limit = Column(Integer)
    value = Column(Integer)
    icon = Column(String)