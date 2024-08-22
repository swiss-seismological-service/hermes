
from geoalchemy2 import Geometry
from sqlalchemy import Column, ForeignKey, Integer, LargeBinary, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from hermes.datamodel.base import ORMBase, RealQuantityMixin, TimeQuantityMixin


class InjectionPlanTable(ORMBase):
    data = Column(LargeBinary, nullable=False)

    forecastseries_oid = Column(UUID, ForeignKey('forecastseries.oid',
                                                 ondelete="CASCADE"))
    forecastseries = relationship('ForecastSeriesTable',
                                  back_populates='injectionplans')

    modelruns = relationship('ModelRunTable',
                             back_populates='injectionplan')


class InjectionObservationTable(ORMBase):
    data = Column(LargeBinary, nullable=False)

    forecast_oid = Column(UUID, ForeignKey('forecast.oid',
                                           ondelete="CASCADE"))
    forecast = relationship('ForecastTable',
                            back_populates='injectionobservation')


class SeismicityObservationTable(ORMBase):
    data = Column(LargeBinary, nullable=False)

    forecast_oid = Column(UUID, ForeignKey('forecast.oid',
                                           ondelete="CASCADE"))
    forecast = relationship('ForecastTable',
                            back_populates='seismicityobservation')
    events = relationship('EventObservationTable',
                          back_populates='seismicityobservation')


class EventObservationTable(TimeQuantityMixin('time'),
                            RealQuantityMixin('latitude'),
                            RealQuantityMixin('longitude'),
                            RealQuantityMixin('depth'),
                            RealQuantityMixin('magnitude'),
                            ORMBase):

    magnitude_type = Column(String)

    seismicityobservation_oid = Column(UUID, ForeignKey(
        'seismicityobservation.oid', ondelete="CASCADE"))
    seismicityobservation = relationship('SeismicityObservationTable',
                                         back_populates='events')
    associated_phasecount = Column(Integer)
    coordinates = Column(Geometry('POINT', srid=4326))


tag_forecast_series_association = Table(
    'tag_forecastseries_association', ORMBase.metadata,
    Column('forecastseries_oid', UUID,
           ForeignKey('forecastseries.oid', ondelete="CASCADE"),
           primary_key=True),
    Column('tag_oid', UUID,
           ForeignKey('tag.oid', ondelete="CASCADE"),
           primary_key=True))
tag_model_config_association = Table(
    'tag_model_config_association', ORMBase.metadata,
    Column('tag_oid', UUID,
           ForeignKey('tag.oid', ondelete="CASCADE"),
           primary_key=True),
    Column('modelconfig_oid', UUID,
           ForeignKey('modelconfig.oid', ondelete="CASCADE"),
           primary_key=True))
