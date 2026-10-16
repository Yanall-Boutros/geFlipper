"""item_indicators: rolling VWAP

Revision ID: f59e3c1a7d26
Revises: e4a7d2b9c815
Create Date: 2026-10-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f59e3c1a7d26"
down_revision: str | Sequence[str] | None = "e4a7d2b9c815"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rows computed before this migration keep NULLs; the engine reseeds from them
    op.add_column("item_indicators", sa.Column("vwap_20", sa.Float(), nullable=True))
    op.add_column(
        "item_indicators", sa.Column("vwap_dev_pct", sa.Float(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("item_indicators", "vwap_dev_pct")
    op.drop_column("item_indicators", "vwap_20")
