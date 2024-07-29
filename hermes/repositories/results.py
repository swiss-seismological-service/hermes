from uuid import UUID

from geoalchemy2.shape import from_shape
from seismostats import Catalog
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from hermes.datamodel.result_tables import (GridCellTable, ModelResultTable,
                                            ModelRunTable, SeismicEventTable,
                                            TimeStepTable)
from hermes.io.catalog import serialize_seismostats_catalog
from hermes.repositories.base import repository_factory
from hermes.repositories.database import pandas_read_sql
from hermes.schemas.result_schemas import (GridCell, ModelResult, ModelRun,
                                           SeismicEvent)


class ModelResultRepository(
    repository_factory(ModelResult,
                       ModelResultTable)):
    pass


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


class TimeStepRepository(
    repository_factory(GridCell,
                       TimeStepTable)):
    pass


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
    def get_catalog(cls, session: Session, modelresult_oid: UUID) -> Catalog:
        q = select(SeismicEventTable).where(
            SeismicEventTable.modelresult_oid == modelresult_oid)

        df = pandas_read_sql(q, session)

        return Catalog(df)


class ModelRunRepository(repository_factory(
        ModelRun, ModelRunTable)):
    pass
