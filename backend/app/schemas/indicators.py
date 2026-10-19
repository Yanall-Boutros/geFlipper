# Pydantic schema for item_indicators rows

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Indicators are NULL until the item has enough priced updates for them; EMA
# values exist from the first update but an EMA-n is only reliable once
# samples >= n. RSI's running averages are internal state and not exposed.
class IndicatorSchema(BaseModel):
    jagex_timestamp: datetime
    samples: int
    ema_5: float | None = None
    ema_20: float | None = None
    ema_200: float | None = None
    env_upper: float | None = None
    env_lower: float | None = None
    rsi_14: float | None = None
    stoch_k: float | None = None
    stoch_d: float | None = None
    vwap_20: float | None = None
    vwap_dev_pct: float | None = None
    vp_poc: float | None = None
    vp_vah: float | None = None
    vp_val: float | None = None
    rel_volume: float | None = None

    model_config = ConfigDict(from_attributes=True)
