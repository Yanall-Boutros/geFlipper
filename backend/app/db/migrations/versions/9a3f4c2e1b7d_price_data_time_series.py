"""price_data: store one row per item per Jagex update

Revision ID: 9a3f4c2e1b7d
Revises: 5c1e2a7b9d40
Create Date: 2026-09-30 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a3f4c2e1b7d'
down_revision: Union[str, Sequence[str], None] = '5c1e2a7b9d40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing rows have no Jagex timestamp to key them on. The collector
    # refills the table from the next dump, so drop them.
    op.execute('DELETE FROM price_data')

    op.add_column('price_data', sa.Column('jagex_timestamp', sa.DateTime(timezone=True), nullable=False))
    op.add_column('price_data', sa.Column('update_detected', sa.DateTime(timezone=True), nullable=False))
    op.drop_constraint('price_data_pkey', 'price_data', type_='primary')
    op.create_primary_key('price_data_pkey', 'price_data', ['id', 'jagex_timestamp'])
    op.create_index('ix_price_data_jagex_timestamp', 'price_data', ['jagex_timestamp'])


def downgrade() -> None:
    """Downgrade schema."""
    # Keep only the latest snapshot of each item so id is unique again
    op.execute('''
        DELETE FROM price_data p
        USING price_data newer
        WHERE newer.id = p.id AND newer.jagex_timestamp > p.jagex_timestamp
    ''')
    op.drop_index('ix_price_data_jagex_timestamp', table_name='price_data')
    op.drop_constraint('price_data_pkey', 'price_data', type_='primary')
    op.create_primary_key('price_data_pkey', 'price_data', ['id'])
    op.drop_column('price_data', 'update_detected')
    op.drop_column('price_data', 'jagex_timestamp')
