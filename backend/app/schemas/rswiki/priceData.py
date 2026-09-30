# Pydantic schema for priceData

from typing import Optional

from pydantic import BaseModel, ConfigDict

# Untraded or untradeable items leave out price/last/volume, alch values and limit
class PriceDataSchemaBase(BaseModel):
    id: int
    name: str
    examine: str
    price: Optional[int] = None
    last: Optional[int] = None
    volume: Optional[int] = None
    members: bool
    lowalch: Optional[int] = None
    highalch: Optional[int] = None
    limit: Optional[int] = None
    value: Optional[int] = None
    icon: str

    model_config = ConfigDict(from_attributes=True)

class PriceDataSchemaCreate(PriceDataSchemaBase):
    pass

class PriceDataSchemaUpdate(PriceDataSchemaBase):
    pass

class PriceDataSchema(PriceDataSchemaBase):
    pass

    