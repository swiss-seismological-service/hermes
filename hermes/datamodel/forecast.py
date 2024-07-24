from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from hermes.datamodel.base import CreationInfoMixin, FiniteEpochMixin, ORMBase


class ForecastTable(CreationInfoMixin,
                    FiniteEpochMixin,
                    ORMBase):

    status = Column(String(25), default='PENDING')
    name = Column(String)

    forecastseries_oid = Column(UUID,
                                ForeignKey('forecastseries.oid',
                                           ondelete="CASCADE"))
    forecastseries = relationship('ForecastSeriesTable',
                                  back_populates='forecasts')

    modelruns = relationship('ModelRunTable',
                             back_populates='forecast',
                             cascade='all, delete-orphan',
                             passive_deletes=True)

    injectionobservation = relationship('InjectionObservationTable',
                                        back_populates='forecast',
                                        cascade='all, delete-orphan',
                                        passive_deletes=True)

    seismicityobservation = relationship('SeismicityObservationTable',
                                         back_populates='forecast',
                                         cascade='all, delete-orphan',
                                         passive_deletes=True)
