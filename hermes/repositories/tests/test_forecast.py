from datetime import datetime

from hermes.repositories.forecast import ForecastRepository
from hermes.repositories.project import ProjectRepository
from hermes.schemas.base import EStatus
from hermes.schemas.forecast import Forecast


class TestForecast:
    def test_create(self, session, forecastseries):
        forecast = Forecast(starttime=datetime(2021, 1, 1, 0, 0, 0),
                            endtime=datetime(2021, 1, 2, 0, 0, 0),
                            name='forecast',
                            status=EStatus.PENDING,
                            forecastseries_oid=forecastseries.oid)

        forecast = ForecastRepository.create(session, forecast)
        assert forecast.oid is not None

        ProjectRepository.delete(session, forecastseries.project_oid)

        assert ForecastRepository.get_by_id(session, forecast.oid) is None
