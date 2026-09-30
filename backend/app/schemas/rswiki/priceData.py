# Pydantic schema for priceData

from pydantic import BaseModel, ConfigDict

class PriceDataSchemaBase(BaseModel):
    id: int
    name: str
    examine: str
    price: int
    last: int
    volume: int
    members: bool
    lowalch: int
    highalch: int
    limit: int
    value: int
    icon: str

    model_config = ConfigDict(from_attributes=True)

class PriceDataSchemaCreate(PriceDataSchemaBase):
    pass

class PriceDataSchemaUpdate(PriceDataSchemaBase):
    pass

class PriceDataSchema(PriceDataSchemaBase):
    pass

    