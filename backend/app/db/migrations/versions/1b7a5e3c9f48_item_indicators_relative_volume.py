"""item_indicators: relative volume

Revision ID: 1b7a5e3c9f48
Revises: 0a6f4d2b8e37
Create Date: 2026-10-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1b7a5e3c9f48"
down_revision: str | Sequence[str] | None = "0a6f4d2b8e37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rows computed before this migration keep NULLs; the engine reseeds from them
    op.add_column("item_indicators", sa.Column("rel_volume", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("item_indicators", "rel_volume")
