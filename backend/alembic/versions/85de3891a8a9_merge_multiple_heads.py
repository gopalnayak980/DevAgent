"""merge multiple heads

Revision ID: 85de3891a8a9
Revises: a1b2c3d4e5f6, dc0e52173676
Create Date: 2026-10-15 21:54:25.320955

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85de3891a8a9'
down_revision: Union[str, None] = ('a1b2c3d4e5f6', 'dc0e52173676')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
