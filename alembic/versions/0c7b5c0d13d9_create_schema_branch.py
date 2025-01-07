"""create schema branch

Revision ID: 0c7b5c0d13d9
Revises:
Create Date: 2025-01-07 15:31:50.195212

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '0c7b5c0d13d9'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ('schema',)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
