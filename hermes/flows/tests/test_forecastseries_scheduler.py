from datetime import datetime, timedelta

import pytest

from hermes.flows.forecastseries_scheduler import ForecastSeriesScheduler
from hermes.schemas import ForecastSeries


class TestForecastSeriesScheduler:

    def test_schedule_assertions(self):
        """
        Test that the assertions in the ForecastSeriesScheduler
        constructor work.
        """
        forecastseries_wrong = ForecastSeries(
            forecast_starttime=None,
            forecast_endtime=datetime(2021, 1, 2, 12, 0, 0),
            forecast_duration=1800,
            forecast_interval=1800
        )

        with pytest.raises(AssertionError):
            ForecastSeriesScheduler(forecastseries_wrong)

        forecastseries_wrong.forecast_starttime = datetime(2021, 1, 2, 0, 0, 0)
        forecastseries_wrong.forecast_interval = None

        with pytest.raises(AssertionError):
            ForecastSeriesScheduler(forecastseries_wrong)

    def test_past(self):
        """
        Test the past forecast times generation.
        """
        forecastseries = ForecastSeries(
            forecast_starttime=datetime(2021, 1, 2, 0, 0, 0),
            forecast_endtime=datetime(2021, 1, 2, 12, 0, 0),
            forecast_duration=1800,
            forecast_interval=1800
        )

        scheduler = ForecastSeriesScheduler(forecastseries)
        assert len(scheduler.past_forecasts) == 25
        assert scheduler.past_forecasts[0] == datetime(2021, 1, 2, 0, 0, 0)

        assert scheduler.past_forecasts[-1] == datetime(2021, 1, 2, 12, 0, 0)

    def test_past_future_end(self):

        # Test the past forecast times generation with a future end time.
        now = datetime.now()
        before = now - timedelta(hours=2)
        after = now + timedelta(hours=2)
        next = now + timedelta(minutes=30)

        forecastseries = ForecastSeries(
            forecast_starttime=before,
            forecast_endtime=after,
            forecast_duration=1800,
            forecast_interval=1800
        )

        scheduler = ForecastSeriesScheduler(forecastseries)
        assert len(scheduler.past_forecasts) == 5
        assert abs(scheduler.start - next) < timedelta(seconds=1)

        # Test with no end time
        forecastseries.forecast_endtime = None
        scheduler = ForecastSeriesScheduler(forecastseries)
        assert len(scheduler.past_forecasts) == 5
        assert abs(scheduler.start - next) < timedelta(seconds=1)

    def test_no_duration(self):
        # Test the past forecast times generation with no duration
        forecastseries = ForecastSeries(
            forecast_starttime=datetime(2021, 1, 2, 0, 0, 0),
            forecast_endtime=datetime(2021, 1, 2, 12, 0, 0),
            forecast_duration=None,
            forecast_interval=1800
        )

        scheduler = ForecastSeriesScheduler(forecastseries)
        assert len(scheduler.past_forecasts) == 24

        assert scheduler.past_forecasts[0] == datetime(2021, 1, 2, 0, 0, 0)
        assert scheduler.past_forecasts[-1] == datetime(2021, 1, 2, 11, 30, 0)
