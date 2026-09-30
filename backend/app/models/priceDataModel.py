from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, String, Boolean
from app.db.base import Base

class PriceDataModel(Base):
    """One row per item per Jagex GE update: a time series keyed on (id, jagex_timestamp)."""
    __tablename__ = 'price_data'

    id = Column(Integer, primary_key=True)  # item id
    # When Jagex published this set of GE prices (the dump's %JAGEX_TIMESTAMP%)
    jagex_timestamp = Column(DateTime(timezone=True), primary_key=True)
    # When the wiki noticed the update (the dump's %UPDATE_DETECTED%)
    update_detected = Column(DateTime(timezone=True), nullable=False)
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

    __table_args__ = (
        # "every item at update X" and "latest update" queries
        Index('ix_price_data_jagex_timestamp', 'jagex_timestamp'),
    )
