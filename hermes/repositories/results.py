from uuid import UUID

import numpy as np
from geoalchemy2.functions import ST_Envelope, ST_Equals, ST_SetSRID
from geoalchemy2.shape import from_shape
from seismostats import Catalog, ForecastCatalog
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hermes.datamodel.result_tables import (GridCellTable, ModelResultTable,
                                            ModelRunTable, SeismicEventTable,
                                            TimeStepTable)
from hermes.io.catalog import serialize_seismostats_catalog
from hermes.repositories.base import repository_factory
from hermes.repositories.database import pandas_read_sql
from hermes.schemas.result_schemas import (GridCell, ModelResult, ModelRun,
                                           SeismicEvent, TimeStep)


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
            ST_Equals(ST_Envelope(GridCellTable.unique_geom),
                      ST_SetSRID(ST_Envelope(gridcell.geom.wkt), 4326)),
            GridCellTable.depth_min == gridcell.depth_min,
            GridCellTable.depth_max == gridcell.depth_max)
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


class SeismicEventRepository(
    repository_factory(SeismicEvent,
                       SeismicEventTable)):

    @classmethod
    def create_from_catalog(cls,
                            session: Session,
                            catalog: Catalog,
                            modelresult_oid: UUID) -> None:
        events = serialize_seismostats_catalog(catalog)

        session.execute(insert(SeismicEventTable)
                        .values(modelresult_oid=modelresult_oid),
                        events)
        session.commit()

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
    pass
