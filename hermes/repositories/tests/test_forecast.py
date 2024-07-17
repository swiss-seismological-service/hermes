from datetime import datetime

from sqlalchemy import text

from hermes.repositories.forecast import ForecastRepository
from hermes.schemas.base import EStatus
from hermes.schemas.forecast import Forecast


class TestForecast:
    def test_create(self, connection, session):
        forecast = Forecast(starttime=datetime(2021, 1, 1, 0, 0, 0),
                            endtime=datetime(2021, 1, 2, 0, 0, 0),
                            name='forecast',
                            status=EStatus.PENDING
                            )
        forecast = ForecastRepository.create(session, forecast)
        assert forecast.oid is not None
        forecast = connection.execute(
            text('SELECT * FROM forecast'))
        assert len(forecast.all()) == 1
