from geoalchemy2 import Geometry
from geoalchemy2.shape import from_shape, to_shape
from sqlalchemy import (Column, Float, ForeignKey, Index, String,
                        UniqueConstraint, event)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from hermes.datamodel.base import (CreationInfoMixin, ORMBase,
                                   RealQuantityMixin, TimeQuantityMixin)


class TimeStepTable(ORMBase):
    starttime = Column(TIMESTAMP(precision=0), nullable=False)
    endtime = Column(TIMESTAMP(precision=0), nullable=False)

    forecastseries_oid = Column(UUID, ForeignKey(
        'forecastseries.oid', ondelete='CASCADE'))

    modelresults = relationship(
        'ModelResultTable',
        back_populates='timestep')

    __table_args__ = (
        UniqueConstraint('starttime', 'endtime', 'forecastseries_oid'),
    )


class GridCellTable(ORMBase):
    geom = Column(Geometry('POLYGON'), nullable=False)
    unique_geom = Column(Geometry('POLYGON'), nullable=False)
    depth_min = Column(Float)
    depth_max = Column(Float)
    forecastseries_oid = Column(UUID, ForeignKey(
        'forecastseries.oid', ondelete='CASCADE'))

    modelresults = relationship(
        'ModelResultTable',
        back_populates='gridcell')

    __table_args__ = (
        UniqueConstraint('unique_geom', 'forecastseries_oid',
                         'depth_min', 'depth_max'),
        Index('ix_grid_cells_unique_geom', 'unique_geom',
              postgresql_using='gist'))


# TODO: This part should eventually become a database trigger!
def set_unique_geom(mapper, connection, target):
    if target.geom is not None:
        polygon = to_shape(target.geom)
        target.unique_geom = from_shape(polygon.envelope, srid=4326)


# Attach event listeners to ensure unique_geom is populated
event.listen(GridCellTable, 'before_insert', set_unique_geom)
event.listen(GridCellTable, 'before_update', set_unique_geom)


class ModelResultTable(CreationInfoMixin, ORMBase):

    modelrun_oid = Column(UUID,
                          ForeignKey('modelrun.oid', ondelete='CASCADE'))
    modelrun = relationship('ModelRunTable',
                            back_populates='modelresults')

    result_type = Column(String(25), nullable=False)

    timestep_oid = Column(UUID,
                          ForeignKey('timestep.oid', ondelete='SET NULL'))
    timestep = relationship('TimeStepTable',
                            back_populates='modelresults')

    gridcell_oid = Column(UUID,
                          ForeignKey('gridcell.oid', ondelete='SET NULL'))
    gridcell = relationship('GridCellTable',
                            back_populates='modelresults')

    seismicevents = relationship('SeismicEventTable',
                                 back_populates='modelresult',
                                 cascade='all, delete-orphan',
                                 passive_deletes=True)

    grparameters = relationship('GRParametersTable',
                                back_populates='modelresult',
                                cascade='all, delete-orphan',
                                passive_deletes=True)


class SeismicEventTable(TimeQuantityMixin('time'),
                        RealQuantityMixin('latitude'),
                        RealQuantityMixin('longitude'),
                        RealQuantityMixin('depth'),
                        RealQuantityMixin('magnitude'),
                        ORMBase):
    magnitude_type = Column(String)

    modelresult_oid = Column(UUID, ForeignKey(
        'modelresult.oid', ondelete='CASCADE'))
    modelresult = relationship(
        'ModelResultTable',
        back_populates='seismicevents')


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


class GRParametersTable(RealQuantityMixin('number_events'),
                        RealQuantityMixin('a'),
                        RealQuantityMixin('b'),
                        RealQuantityMixin('mc'),
                        RealQuantityMixin('alpha'),
                        ORMBase):
    modelresult_oid = Column(UUID, ForeignKey(
        'modelresult.oid', ondelete='CASCADE'))
    modelresult = relationship(
        'ModelResultTable',
        back_populates='grparameters')
