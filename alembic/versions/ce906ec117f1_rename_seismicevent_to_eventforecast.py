"""Rename SeismicEvent to EventForecast

Revision ID: ce906ec117f1
Revises: eecc136ab320
Create Date: 2025-05-20 16:42:36.974798

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ce906ec117f1'
down_revision: Union[str, None] = 'eecc136ab320'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.rename_table('seismicevent', 'eventforecast')


def downgrade():
    op.rename_table('eventforecast', 'seismicevent')
