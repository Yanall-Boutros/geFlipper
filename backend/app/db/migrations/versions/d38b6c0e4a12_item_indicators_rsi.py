"""item_indicators: RSI(14)

Revision ID: d38b6c0e4a12
Revises: c2e5a91f3b07
Create Date: 2026-10-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d38b6c0e4a12"
down_revision: str | Sequence[str] | None = "c2e5a91f3b07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rows computed before this migration keep NULLs; the engine reseeds from them
    op.add_column("item_indicators", sa.Column("rsi_14", sa.Float(), nullable=True))
    op.add_column(
        "item_indicators", sa.Column("rsi_avg_gain", sa.Float(), nullable=True)
    )
    op.add_column(
        "item_indicators", sa.Column("rsi_avg_loss", sa.Float(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("item_indicators", "rsi_avg_loss")
    op.drop_column("item_indicators", "rsi_avg_gain")
    op.drop_column("item_indicators", "rsi_14")
