from sqlalchemy import BigInteger, Column, Integer, String, Boolean
from app.db.base import Base

class PriceDataModel(Base):
    __tablename__ = 'price_data'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    examine = Column(String)
    # BigInteger: the most expensive items trade above the 32-bit limit (~2.1b)
    price = Column(BigInteger)
    last = Column(BigInteger)
    volume = Column(BigInteger)
    members = Column(Boolean)
    lowalch = Column(Integer)
    highalch = Column(Integer)
    limit = Column(Integer)
    value = Column(Integer)
    icon = Column(String)
