"""item_indicators: stochastic oscillator

Revision ID: e4a7d2b9c815
Revises: d38b6c0e4a12
Create Date: 2026-10-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4a7d2b9c815"
down_revision: str | Sequence[str] | None = "d38b6c0e4a12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rows computed before this migration keep NULLs; the engine reseeds from them
    op.add_column("item_indicators", sa.Column("stoch_k", sa.Float(), nullable=True))
    op.add_column("item_indicators", sa.Column("stoch_d", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("item_indicators", "stoch_d")
    op.drop_column("item_indicators", "stoch_k")
