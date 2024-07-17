from geoalchemy2.shape import from_shape
from sqlalchemy.orm import Session

from hermes.datamodel import GridCellTable, ModelResultTable, TimeStepTable
from hermes.repositories import repository_factory
from hermes.schemas import ModelResult
from hermes.schemas.results import GridCell


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
