from sqlalchemy import Column, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from hermes.datamodel.base import ORMBase


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
