from uuid import UUID

from seismostats import Catalog, ForecastGRRateGrid
from sqlalchemy import func, join, select
from sqlalchemy.orm import Session

from hermes.datamodel.result_tables import (EventForecastTable, GridCellTable,
                                            GRParametersTable,
                                            ModelResultTable, ModelRunTable,
                                            TimeStepTable)
from hermes.io.serialize import (deserialize_seismostats_catalog,
                                 deserialize_seismostats_grrategrid)
from hermes.schemas.result_schemas import (EventForecast, GridCell,
                                           GRParameters, ModelResult, ModelRun)
from web.repositories.base import async_repository_factory
from web.repositories.database import pandas_read_sql_async
from web.schemas import ModelResultJSON


class AsyncModelResultRepository(
    async_repository_factory(ModelResult,
                             ModelResultTable)):

    @classmethod
    async def get_by_modelrun_agg(
            cls,
            session: Session,
            modelrun_oid: UUID) -> list[ModelResult]:
        """
        Get all model results for a given model run, aggregated by grid cell
        and time step.
        """
        q = (
            select(
                GridCellTable.depth_min,
                GridCellTable.depth_max,
                GridCellTable.geom,
                GridCellTable.oid.label("gridcell_oid"),
                TimeStepTable.starttime,
                TimeStepTable.endtime,
                TimeStepTable.oid.label("timestep_oid"),
                func.min(ModelResultTable.result_type).label("result_type"),
            )
            .select_from(
                join(GridCellTable,
                     ModelResultTable,
                     GridCellTable.oid == ModelResultTable.gridcell_oid)
                .join(TimeStepTable,
                      TimeStepTable.oid == ModelResultTable.timestep_oid)
            )
            .where(ModelResultTable.modelrun_oid == modelrun_oid)
            .group_by(GridCellTable.oid, TimeStepTable.oid)
            .order_by(
                func.ST_XMin(GridCellTable.unique_geom),
                func.ST_YMin(GridCellTable.unique_geom),
                GridCellTable.depth_min,
                TimeStepTable.starttime,
            )
        )
        result = await session.execute(q)
        result = result.mappings().all()

        return [ModelResultJSON.model_validate({**r, "result_id": i})
                for i, r in enumerate(result)]

    @classmethod
    async def get_by_modelrun_agg_time(
            cls,
            session: Session,
            modelrun_oid: UUID) -> list[ModelResult]:
        """
        Get all model results for a given model run, aggregated by time step.
        """
        q = (
            select(
                TimeStepTable.starttime,
                TimeStepTable.endtime,
                TimeStepTable.oid.label("timestep_oid"),
                func.min(ModelResultTable.result_type).label("result_type"),
            )
            .select_from(
                join(TimeStepTable,
                     ModelResultTable,
                     TimeStepTable.oid == ModelResultTable.timestep_oid)
            )
            .where(ModelResultTable.modelrun_oid == modelrun_oid)
            .group_by(TimeStepTable.oid)
            .order_by(
                TimeStepTable.starttime,
            )
        )
        result = await session.execute(q)
        result = result.mappings().all()

        return [ModelResultJSON.model_validate({**r, "result_id": i})
                for i, r in enumerate(result)]


class AsyncGridCellRepository(async_repository_factory(GridCell,
                                                       GridCellTable)):
    pass


class AsyncTimeStepRepository(
    async_repository_factory(GridCell,
                             TimeStepTable)):
    pass


class AsyncGRParametersRepository(
    async_repository_factory(GRParameters,
                             GRParametersTable)):

    @classmethod
    async def get_forecast_grrategrid(
            cls,
            session: Session,
            modelrun_oid: UUID,
            gridcell_oid: UUID | None = None,
            timestep_oid: UUID | None = None
    ) -> ForecastGRRateGrid:

        filter = [ModelResultTable.modelrun_oid == modelrun_oid]
        if gridcell_oid:
            filter.append(ModelResultTable.gridcell_oid == gridcell_oid)
        if timestep_oid:
            filter.append(ModelResultTable.timestep_oid == timestep_oid)

        q = select(ModelResultTable.realization_id,
                   *GRParametersTable.__table__.c,
                   GridCellTable.depth_min,
                   GridCellTable.depth_max,
                   GridCellTable.geom,
                   TimeStepTable.starttime,
                   TimeStepTable.endtime,) \
            .where(*filter) \
            .join(GRParametersTable) \
            .join(GridCellTable) \
            .join(TimeStepTable)

        result = await pandas_read_sql_async(q, session)

        rategrid = deserialize_seismostats_grrategrid(
            result,
            timestep=timestep_oid is not None)

        return rategrid


class AsyncEventForecastRepository(
    async_repository_factory(EventForecast,
                             EventForecastTable)):

    @classmethod
    async def get_forecast_catalog(
            cls,
            session: Session,
            modelrun_oid: UUID,
            gridcell_oid: UUID | None = None,
            timestep_oid: UUID | None = None
    ) -> Catalog:

        filter = [ModelResultTable.modelrun_oid == modelrun_oid]
        if gridcell_oid:
            filter.append(ModelResultTable.gridcell_oid == gridcell_oid)
        if timestep_oid:
            filter.append(ModelResultTable.timestep_oid == timestep_oid)

        q = select(ModelResultTable.realization_id,
                   *EventForecastTable.__table__.c,
                   GridCellTable.depth_min,
                   GridCellTable.depth_max,
                   GridCellTable.geom,
                   TimeStepTable.starttime,
                   TimeStepTable.endtime)\
            .where(*filter) \
            .join(EventForecastTable) \
            .join(GridCellTable) \
            .join(TimeStepTable)

        result = await pandas_read_sql_async(q, session)

        catalog = deserialize_seismostats_catalog(
            result,
            gridcell=gridcell_oid is not None,
            timestep=timestep_oid is not None)

        return catalog


class AsyncModelRunRepository(async_repository_factory(
        ModelRun, ModelRunTable)):

    @classmethod
    async def get_by_forecast(
            cls,
            session: Session,
            forecast_oid: UUID) -> list[ModelRun]:
        q = select(ModelRunTable).where(
            ModelRunTable.forecast_oid == forecast_oid)
        result = await session.execute(q)
        result = result.unique().scalars().all()
        return [cls.model.model_validate(r) for r in result]
