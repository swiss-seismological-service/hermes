from geoalchemy2.shape import from_shape
from sqlalchemy.orm import Session

from hermes.datamodel import ForecastSeriesTable
from hermes.repositories import repository_factory
from hermes.repositories.tag import TagRepository
from hermes.schemas import ForecastSeries


class ForecastSeriesRepository(repository_factory(
        ForecastSeries, ForecastSeriesTable)):

    @classmethod
    def create(cls, session: Session, data: ForecastSeries) -> ForecastSeries:

        # Check if tags exist in the database, if not create them.
        tags = []
        for tag in data.tags:
            tags.append(TagRepository._get_or_create(session, tag))

        # Convert the bounding polygon to a geoalchemy2 shape.
        bounding_polygon = None
        if data.bounding_polygon:
            bounding_polygon = from_shape(data.bounding_polygon)

        # Create the database model and commit it to the database.
        db_model = ForecastSeriesTable(
            _tags=tags,
            bounding_polygon=bounding_polygon,
            **data.model_dump(exclude_unset=True,
                              exclude=['tags', 'bounding_polygon']))

        session.add(db_model)
        session.commit()
        session.refresh(db_model)

        return cls.model.model_validate(db_model)
