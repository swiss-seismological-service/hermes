from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from hermes.datamodel.base import NameMixin, ORMBase

tag_model_config_association = Table(
    'tag_model_config_association', ORMBase.metadata,
    Column('tag_oid', UUID,
           ForeignKey('tag.oid', ondelete="CASCADE"),
           primary_key=True),
    Column('modelconfig_oid', UUID,
           ForeignKey('modelconfig.oid', ondelete="CASCADE"),
           primary_key=True))

tag_forecast_series_association = Table(
    'tag_forecastseries_association', ORMBase.metadata,
    Column('forecastseries_oid', UUID,
           ForeignKey('forecastseries.oid', ondelete="CASCADE"),
           primary_key=True),
    Column('tag_oid', UUID,
           ForeignKey('tag.oid', ondelete="CASCADE"),
           primary_key=True))


class TagTable(ORMBase, NameMixin):

    modelconfigs = relationship(
        'ModelConfigTable',
        back_populates='_tags',
        secondary=tag_model_config_association)

    forecastseries = relationship(
        'ForecastSeriesTable',
        back_populates='_tags',
        secondary=tag_forecast_series_association)
