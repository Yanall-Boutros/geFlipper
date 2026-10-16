from sqlalchemy import Column, DateTime, Float, ForeignKeyConstraint, Index, Integer

from app.db.base import Base


class ItemIndicatorsModel(Base):
    """Indicator values for one item at one Jagex update, keyed like price_data."""

    __tablename__ = "item_indicators"

    id = Column(Integer, primary_key=True)  # item id
    jagex_timestamp = Column(DateTime(timezone=True), primary_key=True)
    # How many priced updates of this item the indicators have seen, this one included.
    # Indicators with a period n are only meaningful once samples >= n.
    samples = Column(Integer, nullable=False)

    # running EMAs, seeded with the first price; reliable once samples >= period
    ema_5 = Column(Float)
    ema_20 = Column(Float)
    ema_200 = Column(Float)
    # EMA-5 +/- ENVELOPE_PCT
    env_upper = Column(Float)
    env_lower = Column(Float)

    # Wilder RSI; the averages are its running state
    rsi_14 = Column(Float)
    rsi_avg_gain = Column(Float)
    rsi_avg_loss = Column(Float)

    # %K(14) / %D(3) from closing prices (the dump has no high/low)
    stoch_k = Column(Float)
    stoch_d = Column(Float)

    # VWAP over the last 20 updates; dev is % from price
    vwap_20 = Column(Float)
    vwap_dev_pct = Column(Float)

    # volume profile of the last 30 updates: point of control, value area high/low
    vp_poc = Column(Float)
    vp_vah = Column(Float)
    vp_val = Column(Float)

    # volume / mean volume of the previous 20 updates
    rel_volume = Column(Float)

    __table_args__ = (
        ForeignKeyConstraint(
            ["id", "jagex_timestamp"],
            ["price_data.id", "price_data.jagex_timestamp"],
            ondelete="CASCADE",
        ),
        # the engine's "latest computed update" lookup
        Index("ix_item_indicators_jagex_timestamp", "jagex_timestamp"),
    )
