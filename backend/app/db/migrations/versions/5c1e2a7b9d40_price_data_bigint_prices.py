"""price_data: widen price, last and volume to BigInteger

Revision ID: 5c1e2a7b9d40
Revises: 0fb98dffcf83
Create Date: 2026-09-30 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5c1e2a7b9d40"
down_revision: str | Sequence[str] | None = "0fb98dffcf83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = ("price", "last", "volume")


def upgrade() -> None:
    """Upgrade schema."""
    for column in COLUMNS:
        op.alter_column(
            "price_data",
            column,
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Fails if any row holds a value above the 32-bit limit
    for column in COLUMNS:
        op.alter_column(
            "price_data",
            column,
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=True,
        )
