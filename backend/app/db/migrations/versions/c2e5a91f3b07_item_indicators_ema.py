"""item_indicators: EMA 5/20/200 and envelopes

Revision ID: c2e5a91f3b07
Revises: b41d7e2a9c10
Create Date: 2026-10-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2e5a91f3b07"
down_revision: str | Sequence[str] | None = "b41d7e2a9c10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rows computed before this migration keep NULLs; the engine reseeds from them
    op.add_column("item_indicators", sa.Column("ema_5", sa.Float(), nullable=True))
    op.add_column("item_indicators", sa.Column("ema_20", sa.Float(), nullable=True))
    op.add_column("item_indicators", sa.Column("ema_200", sa.Float(), nullable=True))
    op.add_column("item_indicators", sa.Column("env_upper", sa.Float(), nullable=True))
    op.add_column("item_indicators", sa.Column("env_lower", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("item_indicators", "env_lower")
    op.drop_column("item_indicators", "env_upper")
    op.drop_column("item_indicators", "ema_200")
    op.drop_column("item_indicators", "ema_20")
    op.drop_column("item_indicators", "ema_5")
