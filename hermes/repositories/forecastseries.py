from hermes.datamodel import ForecastSeriesTable
from hermes.repositories import repository_factory
from hermes.schemas import ForecastSeries


class ForecastSeriesRepository(repository_factory(
        ForecastSeries, ForecastSeriesTable)):
    pass
