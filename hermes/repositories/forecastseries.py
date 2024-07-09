from sqlalchemy import select
from sqlalchemy.orm import Session

from hermes.datamodel import ForecastSeriesTable, TagTable
from hermes.repositories import repository_factory
from hermes.schemas import ForecastSeries


class ForecastSeriesRepository(repository_factory(
        ForecastSeries, ForecastSeriesTable)):

    @classmethod
    def create(cls, session: Session, data: ForecastSeries) -> ForecastSeries:

        tags = []

        for tag in data.tags:
            q = select(TagTable).where(TagTable.name == tag)
            result = session.execute(q).unique().scalar_one_or_none()
            if result:
                tags.append(result)
            else:
                tags.append(TagTable(name=tag))

        db_model = ForecastSeriesTable(
            _tags=tags, **data.model_dump(exclude=['tags']))
        session.add(db_model)
        session.commit()
        session.refresh(db_model)
        return cls.model.model_validate(db_model)
