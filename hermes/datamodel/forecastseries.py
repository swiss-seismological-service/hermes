from geoalchemy2 import Geometry
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from hermes.datamodel.base import (CreationInfoMixin, EpochMixin, NameMixin,
                                   ORMBase)
from hermes.datamodel.tag import tag_forecast_series_association

ForecastEpochMixin = EpochMixin(name='forecast',
                                column_prefix='forecast',
                                epoch_type='default')
ObservationEpochMixin = EpochMixin(name='observation',
                                   column_prefix='observation',
                                   epoch_type='open')


class ForecastSeriesTable(CreationInfoMixin,
                          ForecastEpochMixin,
                          ObservationEpochMixin,
                          NameMixin,
                          ORMBase):

    status = Column(String(25))
    description = Column(String)
    project_oid = Column(UUID,
                         ForeignKey('project.oid', ondelete="CASCADE"))
    project = relationship('ProjectTable',
                           back_populates='forecastseries')

    # Interval in seconds to place forecasts apart in time.
    forecast_interval = Column(Integer)
    forecast_duration = Column(Integer)

    # Spatial dimensions of the area considered.
    bounding_polygon = Column(Geometry('POLYGON', srid=4326))
    depth_min = Column(Float)
    depth_max = Column(Float)

    forecasts = relationship('ForecastTable',
                             back_populates='forecastseries',
                             cascade='all, delete-orphan',
                             passive_deletes=True)
    _tags = relationship('TagTable',
                         back_populates='forecastseries',
                         secondary=tag_forecast_series_association)

    @hybrid_property
    def tags(self):
        t = [tag.name for tag in self._tags]
        return t

    injectionplans = relationship('InjectionPlanTable',
                                  back_populates='forecastseries',
                                  cascade='all, delete-orphan',
                                  passive_deletes=True)
