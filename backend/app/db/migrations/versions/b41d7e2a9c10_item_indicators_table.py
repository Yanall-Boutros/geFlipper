"""item_indicators: per-item indicator time series keyed like price_data

Revision ID: b41d7e2a9c10
Revises: 9a3f4c2e1b7d
Create Date: 2026-10-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b41d7e2a9c10"
down_revision: str | Sequence[str] | None = "9a3f4c2e1b7d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "item_indicators",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jagex_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("samples", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", "jagex_timestamp"),
        sa.ForeignKeyConstraint(
            ["id", "jagex_timestamp"],
            ["price_data.id", "price_data.jagex_timestamp"],
            ondelete="CASCADE",
        ),
    )
    # Speeds up the engine's "latest computed update" lookup
    op.create_index(
        "ix_item_indicators_jagex_timestamp", "item_indicators", ["jagex_timestamp"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_item_indicators_jagex_timestamp", table_name="item_indicators")
    op.drop_table("item_indicators")
