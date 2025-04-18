"""add indexes for deletion cascades

Revision ID: eecc136ab320
Revises: c164eff8a1f3
Create Date: 2025-04-15 12:17:12.450065

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'eecc136ab320'
down_revision: Union[str, None] = 'c164eff8a1f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_eventobservation_seismicityobservation_oid'),
                    'eventobservation', ['seismicityobservation_oid'],
                    unique=False)
    op.create_index(op.f('ix_forecastseries_project_oid'),
                    'forecastseries', ['project_oid'], unique=False)
    op.create_index(op.f('ix_gridcell_forecastseries_oid'),
                    'gridcell', ['forecastseries_oid'], unique=False)
    op.create_index(op.f('ix_grparameters_modelresult_oid'),
                    'grparameters', ['modelresult_oid'], unique=False)
    op.create_index(op.f('ix_injectionobservation_forecast_oid'),
                    'injectionobservation', ['forecast_oid'], unique=False)
    op.create_index(op.f('ix_injectionplan_forecastseries_oid'),
                    'injectionplan', ['forecastseries_oid'], unique=False)
    op.create_index(op.f('ix_seismicityobservation_forecast_oid'),
                    'seismicityobservation', ['forecast_oid'], unique=False)
    op.create_index(op.f('ix_timestep_forecastseries_oid'),
                    'timestep', ['forecastseries_oid'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_timestep_forecastseries_oid'),
                  table_name='timestep')
    op.drop_index(op.f('ix_seismicityobservation_forecast_oid'),
                  table_name='seismicityobservation')
    op.drop_index(op.f('ix_injectionplan_forecastseries_oid'),
                  table_name='injectionplan')
    op.drop_index(op.f('ix_injectionobservation_forecast_oid'),
                  table_name='injectionobservation')
    op.drop_index(op.f('ix_grparameters_modelresult_oid'),
                  table_name='grparameters')
    op.drop_index(op.f('ix_gridcell_forecastseries_oid'),
                  table_name='gridcell')
    op.drop_index(op.f('ix_forecastseries_project_oid'),
                  table_name='forecastseries')
    op.drop_index(op.f('ix_eventobservation_seismicityobservation_oid'),
                  table_name='eventobservation')
    # ### end Alembic commands ###
