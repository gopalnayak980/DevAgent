"""Add title column to conversations table

Revision ID: a1b2c3d4e5f6
Revises: befa9e13a93f
Create Date: 2026-10-06 21:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'befa9e13a93f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'conversations',
        sa.Column('title', sa.String(length=120), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('conversations', 'title')
