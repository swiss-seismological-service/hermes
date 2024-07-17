from hermes.datamodel import ForecastTable
from hermes.repositories import repository_factory
from hermes.schemas import Forecast


class ForecastRepository(repository_factory(Forecast, ForecastTable)):
    pass
