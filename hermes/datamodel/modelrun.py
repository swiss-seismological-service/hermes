from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from hermes.datamodel.base import ORMBase


class ModelRunTable(ORMBase):

    status = Column(String(25), default='PENDING')

    modelconfig_oid = Column(UUID,
                             ForeignKey('modelconfig.oid',
                                        ondelete="RESTRICT"))
    modelconfig = relationship('ModelConfigTable',
                               back_populates='modelruns')

    forecast_oid = Column(UUID,
                          ForeignKey('forecast.oid',
                                     ondelete="CASCADE"))
    forecast = relationship('ForecastTable',
                            back_populates='modelruns')

    injectionplan_oid = Column(UUID,
                               ForeignKey('injectionplan.oid',
                                          ondelete='SET NULL'))
    injectionplan = relationship('InjectionPlanTable',
                                 back_populates='modelruns')

    modelresults = relationship('ModelResultTable',
                                back_populates='modelrun',
                                cascade='all, delete-orphan',
                                passive_deletes=True)
