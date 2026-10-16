"""item_indicators: volume profile

Revision ID: 0a6f4d2b8e37
Revises: f59e3c1a7d26
Create Date: 2026-10-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0a6f4d2b8e37"
down_revision: str | Sequence[str] | None = "f59e3c1a7d26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rows computed before this migration keep NULLs; the engine reseeds from them
    op.add_column("item_indicators", sa.Column("vp_poc", sa.Float(), nullable=True))
    op.add_column("item_indicators", sa.Column("vp_vah", sa.Float(), nullable=True))
    op.add_column("item_indicators", sa.Column("vp_val", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("item_indicators", "vp_val")
    op.drop_column("item_indicators", "vp_vah")
    op.drop_column("item_indicators", "vp_poc")
