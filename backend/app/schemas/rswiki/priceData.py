# Pydantic schema for priceData

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Untraded or untradeable items leave out price/last/volume, alch values and limit
class PriceDataSchemaBase(BaseModel):
    id: int
    jagex_timestamp: datetime
    update_detected: datetime
    name: str
    examine: str
    price: int | None = None
    last: int | None = None
    volume: int | None = None
    members: bool
    lowalch: int | None = None
    highalch: int | None = None
    limit: int | None = None
    value: int | None = None
    icon: str

    model_config = ConfigDict(from_attributes=True)


class PriceDataSchemaCreate(PriceDataSchemaBase):
    pass


class PriceDataSchemaUpdate(PriceDataSchemaBase):
    pass


class PriceDataSchema(PriceDataSchemaBase):
    pass
