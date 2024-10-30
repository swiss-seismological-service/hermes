from uuid import UUID

import numpy as np
from geoalchemy2.functions import (ST_Envelope, ST_Equals, ST_GeomFromText,
                                   ST_SetSRID)
from geoalchemy2.shape import from_shape
from seismostats import Catalog, ForecastCatalog, ForecastGRRateGrid
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hermes.datamodel.result_tables import (GridCellTable, GRParametersTable,
                                            ModelResultTable, ModelRunTable,
                                            SeismicEventTable, TimeStepTable)
from hermes.io.catalog import (serialize_seismostats_catalog,
                               serialize_seismostats_grrategrid)
from hermes.repositories.base import repository_factory
from hermes.repositories.database import pandas_read_sql
from hermes.schemas.result_schemas import (GridCell, GRParameters, ModelResult,
                                           ModelRun, SeismicEvent, TimeStep)


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
                 'result_type': result_type} for _ in range(number)]

        q = insert(ModelResultTable).returning(ModelResultTable.oid)

        result = session.execute(q, data).fetchall()
        session.commit()
        return [row[0] for row in result]


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
        rategrid.grid_id = np.array(modelresult_oids)[rategrid.grid_id]
        rategrid = rategrid.rename(columns={'grid_id': 'modelresult_oid'})
        grparameters = serialize_seismostats_grrategrid(rategrid)

        session.execute(insert(GRParametersTable), grparameters)
        session.commit()

    @classmethod
    def get_forecast_grrategrid(
            cls,
            session: Session,
            modelresult_oid: UUID) -> ForecastGRRateGrid:
        pass


class SeismicEventRepository(
    repository_factory(SeismicEvent,
                       SeismicEventTable)):

    @classmethod
    def create_from_forecast_catalog(cls,
                                     session: Session,
                                     catalog: ForecastCatalog,
                                     modelresult_oids: list[UUID]) -> None:

        # replace the catalog_id column with the modelresult_oids
        catalog.catalog_id = np.array(modelresult_oids)[catalog.catalog_id]
        catalog = catalog.rename(columns={'catalog_id': 'modelresult_oid'})
        events = serialize_seismostats_catalog(catalog)

        session.execute(insert(SeismicEventTable), events)
        session.commit()

    @classmethod
    def get_catalog(cls, session: Session, modelresult_oid: UUID) -> Catalog:
        q = select(SeismicEventTable).where(
            SeismicEventTable.modelresult_oid == modelresult_oid)

        df = pandas_read_sql(q, session)

        return Catalog(df)


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
