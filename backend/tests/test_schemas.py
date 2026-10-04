import pytest
from pydantic import ValidationError

from app.models import PriceDataModel
from app.schemas.pagination import Page
from app.schemas.rswiki.priceData import PriceDataSchema, PriceDataSchemaCreate
from tests.conftest import price_row


def test_price_data_from_model():
    schema = PriceDataSchema.model_validate(PriceDataModel(**price_row(7)))
    assert schema.id == 7
    assert schema.price == 100


def test_untraded_item_fields_are_optional():
    row = price_row(1)
    for key in ("price", "last", "volume", "lowalch", "highalch", "limit", "value"):
        del row[key]
    schema = PriceDataSchemaCreate.model_validate(row)
    assert schema.price is None and schema.limit is None


@pytest.mark.parametrize("missing", ["name", "examine", "members", "icon", "jagex_timestamp", "update_detected"])
def test_required_fields(missing):
    row = price_row(1)
    del row[missing]
    with pytest.raises(ValidationError):
        PriceDataSchemaCreate.model_validate(row)


def test_page():
    page = Page[PriceDataSchema](items=[price_row(1)], total=10, offset=0, limit=1)
    assert isinstance(page.items[0], PriceDataSchema)
    assert page.model_dump()["total"] == 10
