from uuid import UUID

import numpy as np
from geoalchemy2.functions import (ST_Envelope, ST_Equals, ST_GeomFromText,
                                   ST_SetSRID)
from geoalchemy2.shape import from_shape
from seismostats import Catalog, ForecastCatalog, ForecastGRRateGrid
from sqlalchemy import func, insert, join, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hermes.datamodel.result_tables import (GridCellTable, GRParametersTable,
                                            ModelResultTable, ModelRunTable,
                                            SeismicEventTable, TimeStepTable)
from hermes.io.serialize import (deserialize_seismostats_catalog,
                                 deserialize_seismostats_grrategrid,
                                 serialize_seismostats_catalog,
                                 serialize_seismostats_grrategrid)
from hermes.repositories.base import repository_factory
from hermes.repositories.database import pandas_read_sql_async
from hermes.schemas.result_schemas import (GridCell, GRParameters, ModelResult,
                                           ModelRun, SeismicEvent, TimeStep)
from web.schemas import ModelResultJSON


class ModelResultRepository(
    repository_factory(ModelResult,
                       ModelResultTable)):
    @classmethod
    def batch_create(cls,
                     session: Session,
                     number: int,
                     result_type: str,
                     timestep_oid: UUID | None = None,
                     gridcell_oid: UUID | None = None,
                     modelrun_oid: UUID | None = None) -> list[UUID]:
        data = [{'timestep_oid': timestep_oid,
                 'gridcell_oid': gridcell_oid,
                 'modelrun_oid': modelrun_oid,
                 'result_type': result_type,
                 'realization_id': i} for i in range(number)]

        q = insert(ModelResultTable).returning(
            ModelResultTable.oid,
            ModelResultTable.realization_id)

        result = session.execute(q, data).fetchall()
        session.commit()

        # make sure that the list id is the same as the realization_id
        # since the database does not guarantee the order of the results
        batch = sorted(result, key=lambda x: x[1])
        return [x[0] for x in batch]

    @classmethod
    async def get_by_modelrun_agg_async(
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
    async def get_by_modelrun_agg_time_async(
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


class GridCellRepository(
    repository_factory(GridCell,
                       GridCellTable)):
    @classmethod
    def create(cls,
               session: Session,
               data: GridCell) -> GridCell:

        geom = None
        if data.geom:
            geom = from_shape(data.geom)

        db_model = GridCellTable(
            geom=geom,
            **data.model_dump(exclude_unset=True,
                              exclude=['geom']))

        session.add(db_model)
        session.commit()
        session.refresh(db_model)

        return cls.model.model_validate(db_model)

    @classmethod
    def get_or_create(cls,
                      session: Session,
                      gridcell: GridCell) -> GridCell:
        q = select(GridCellTable).where(
            GridCellTable.forecastseries_oid == gridcell.forecastseries_oid,
            # TODO: Improve SRID handling
            ST_Equals(
                ST_Envelope(GridCellTable.unique_geom),
                ST_Envelope(
                    ST_SetSRID(
                        ST_GeomFromText(gridcell.geom.wkt),
                        4326
                    )
                )
            )
        )
        result = session.execute(q).unique().scalar_one_or_none()

        if not result:
            try:
                result = cls.create(session, gridcell)
            except IntegrityError as e:
                session.rollback()
                result = session.execute(q).unique().scalar_one_or_none()
                if not result:
                    raise e
        return result


class TimeStepRepository(
    repository_factory(GridCell,
                       TimeStepTable)):
    @classmethod
    def get_or_create(cls,
                      session: Session,
                      timestep: TimeStep) -> TimeStep:
        q = select(TimeStepTable).where(
            TimeStepTable.starttime == timestep.starttime,
            TimeStepTable.endtime == timestep.endtime,
            TimeStepTable.forecastseries_oid == timestep.forecastseries_oid)
        result = session.execute(q).unique().scalar_one_or_none()
        if not result:
            try:
                result = cls.create(session, timestep)
            except IntegrityError as e:
                session.rollback()
                result = session.execute(q).unique().scalar_one_or_none()
                if not result:
                    raise e
        return result


class GRParametersRepository(
    repository_factory(GRParameters,
                       GRParametersTable)):
    @classmethod
    def create_from_forecast_grrategrid(
            cls,
            session: Session,
            rategrid: ForecastGRRateGrid,
            modelresult_oids: list[UUID]) -> None:

        # make sure that the grid_id is 0 indexed
        if max(rategrid.grid_id) >= len(modelresult_oids):
            raise ValueError('The number of modelresult_oids is less than the '
                             'maximum grid_id in the rategrid.')

        # Modelresult_oid is guaranteed to be in the same order as the
        # 0 indexed grid_id. Replace the grid_id with the modelresult_oid.
        rategrid.grid_id = np.array(modelresult_oids)[rategrid.grid_id]
        rategrid = rategrid.rename(columns={'grid_id': 'modelresult_oid'})
        grparameters = serialize_seismostats_grrategrid(rategrid)

        session.execute(insert(GRParametersTable), grparameters)
        session.commit()

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


class SeismicEventRepository(
    repository_factory(SeismicEvent,
                       SeismicEventTable)):

    @classmethod
    def create_from_forecast_catalog(cls,
                                     session: Session,
                                     catalog: ForecastCatalog,
                                     modelresult_oids: list[UUID]) -> None:
        if catalog.empty:
            return
        # make sure that the catalog_id is 0 indexed
        if max(catalog.catalog_id) >= len(modelresult_oids):
            raise ValueError('The number of modelresult_oids is less than the '
                             'maximum catalog_id in the catalog.')

        # Modelresult_oid is guaranteed to be in the same order as the 0
        # indexed grid_id. Replace the catalog_id column with the
        # modelresult_oids.
        catalog.catalog_id = np.array(modelresult_oids)[catalog.catalog_id]
        catalog = catalog.rename(columns={'catalog_id': 'modelresult_oid'})
        events = serialize_seismostats_catalog(catalog)

        session.execute(insert(SeismicEventTable), events)
        session.commit()

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
                   *SeismicEventTable.__table__.c,
                   GridCellTable.depth_min,
                   GridCellTable.depth_max,
                   GridCellTable.geom,
                   TimeStepTable.starttime,
                   TimeStepTable.endtime)\
            .where(*filter) \
            .join(SeismicEventTable) \
            .join(GridCellTable) \
            .join(TimeStepTable)

        result = await pandas_read_sql_async(q, session)

        catalog = deserialize_seismostats_catalog(
            result,
            gridcell=gridcell_oid is not None,
            timestep=timestep_oid is not None)

        return catalog


class ModelRunRepository(repository_factory(
        ModelRun, ModelRunTable)):
    @classmethod
    def update_status(cls,
                      session: Session,
                      modelrun_oid: UUID,
                      status: str) -> ModelRun:
        q = select(ModelRunTable).where(ModelRunTable.oid == modelrun_oid)
        result = session.execute(q).unique().scalar_one_or_none()

        if result:
            result.status = status
            session.commit()
            session.refresh(result)
            return cls.model.model_validate(result)
        return None

    @classmethod
    def get_by_modelconfig(cls,
                           session: Session,
                           modelconfig_oid: UUID) -> ModelRun:
        q = select(ModelRunTable).where(
            ModelRunTable.modelconfig_oid == modelconfig_oid)
        result = session.execute(q).unique().all()
        return [cls.model.model_validate(r) for r in result]

    @classmethod
    def get_by_injectionplan(cls,
                             session: Session,
                             injectionplan_oid: UUID) -> ModelRun:
        q = select(ModelRunTable).where(
            ModelRunTable.injectionplan_oid == injectionplan_oid)
        result = session.execute(q).unique().all()
        return [cls.model.model_validate(r) for r in result]

    @classmethod
    async def get_by_forecast_async(
            cls,
            session: Session,
            forecast_oid: UUID) -> list[ModelRun]:
        q = select(ModelRunTable).where(
            ModelRunTable.forecast_oid == forecast_oid)
        result = await session.execute(q)
        result = result.unique().scalars().all()
        return [cls.model.model_validate(r) for r in result]
