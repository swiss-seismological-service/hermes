from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from hermes.datamodel.base import (CreationInfoMixin, DefaultEpochMixin,
                                   NameMixin, ORMBase)


class ProjectTable(CreationInfoMixin,
                   NameMixin,
                   DefaultEpochMixin,
                   ORMBase):

    description = Column(String)

    forecastseries = relationship(
        'ForecastSeriesTable',
        back_populates='project',
        cascade='all, delete-orphan',
        passive_deletes=True)

    fdsnws_url = Column(String)
    hydws_url = Column(String)

    seismicityobservation_required = Column(String(15), default='REQUIRED')
    injectionobservation_required = Column(String(15), default='REQUIRED')
    injectionplan_required = Column(String(15), default='REQUIRED')
