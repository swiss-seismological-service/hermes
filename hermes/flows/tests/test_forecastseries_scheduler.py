import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from dateutil.rrule import SECONDLY, rrule

from hermes.flows.forecastseries_scheduler import ForecastSeriesScheduler
from hermes.schemas import ForecastSeries


@patch('hermes.repositories.project.ForecastSeriesRepository.get_by_id',
       autocast=True)
class TestForecastSeriesScheduler:

    def test_schedule_assertions(self, mock_fs_get_by_id: MagicMock, prefect):
        """
        Test that the assertions in the ForecastSeriesScheduler
        constructor work.
        """
        forecastseries_wrong = ForecastSeries(
            schedule_starttime=None,
            forecast_endtime=datetime(2021, 1, 2, 12, 0, 0),
            forecast_duration=1800,
            schedule_interval=1800
        )
        mock_fs_get_by_id.return_value = forecastseries_wrong

        with pytest.raises(AssertionError):
            ForecastSeriesScheduler(forecastseries_wrong)

        forecastseries_wrong.schedule_starttime = datetime(2021, 1, 2, 0, 0, 0)
        forecastseries_wrong.schedule_interval = None

        with pytest.raises(AssertionError):
            ForecastSeriesScheduler(forecastseries_wrong)

    def test_past(self, mock_fs_get_by_id: MagicMock, prefect):
        """
        Test the past forecast times generation.
        """
        forecastseries = ForecastSeries(
            schedule_starttime=datetime(2021, 1, 2, 0, 0, 0),
            schedule_endtime=datetime(2021, 1, 2, 12, 0, 0),
            forecast_endtime=datetime(2021, 1, 2, 12, 0, 0),
            forecast_duration=1800,
            schedule_interval=1800
        )
        mock_fs_get_by_id.return_value = forecastseries

        scheduler = ForecastSeriesScheduler(forecastseries)

        assert len(scheduler.past_forecasts) == 25
        assert scheduler.past_forecasts[0] == datetime(2021, 1, 2, 0, 0, 0)
        assert scheduler.past_forecasts[-1] == datetime(2021, 1, 2, 12, 0, 0)
        assert scheduler.rrule is None

    def test_past_future_end(self, mock_fs_get_by_id: MagicMock, prefect):
        # Test the past forecast times generation with a future end time.
        now = datetime.now()
        before = now - timedelta(hours=2)
        after = now + timedelta(hours=2)
        next = now + timedelta(minutes=30)

        forecastseries = ForecastSeries(
            schedule_starttime=before,
            forecast_endtime=after,
            schedule_endtime=after,
            forecast_duration=1800,
            schedule_interval=1800
        )
        mock_fs_get_by_id.return_value = forecastseries

        scheduler = ForecastSeriesScheduler(forecastseries)
        assert len(scheduler.past_forecasts) == 5
        assert abs(scheduler.schedule_starttime - next) < timedelta(seconds=1)

        schedule = rrule(freq=SECONDLY, interval=1800,
                         dtstart=next, until=after)
        assert str(schedule) == str(scheduler.rrule)

        # Test with no end time
        forecastseries.forecast_endtime = None
        scheduler = ForecastSeriesScheduler(forecastseries)
        assert len(scheduler.past_forecasts) == 5
        assert abs(scheduler.schedule_starttime - next) < timedelta(seconds=1)

    def test_no_duration(self, mock_fs_get_by_id: MagicMock, prefect):
        # Test the past forecast times generation with no duration
        forecastseries = ForecastSeries(
            schedule_starttime=datetime(2021, 1, 2, 0, 0, 0),
            forecast_endtime=datetime(2021, 1, 2, 12, 0, 0),
            schedule_endtime=datetime(2021, 1, 2, 12, 0, 0),
            forecast_duration=None,
            schedule_interval=1800
        )
        mock_fs_get_by_id.return_value = forecastseries

        scheduler = ForecastSeriesScheduler(forecastseries)
        assert len(scheduler.past_forecasts) == 24

        assert scheduler.past_forecasts[0] == datetime(2021, 1, 2, 0, 0, 0)
        assert scheduler.past_forecasts[-1] == datetime(2021, 1, 2, 11, 30, 0)

    def test_no_end(self, mock_fs_get_by_id: MagicMock, prefect):
        now = datetime.now()
        before = now - timedelta(hours=2)
        next = now + timedelta(minutes=30)

        forecastseries = ForecastSeries(
            schedule_starttime=before,
            forecast_endtime=None,
            forecast_duration=1800,
            schedule_interval=1800
        )
        mock_fs_get_by_id.return_value = forecastseries

        scheduler = ForecastSeriesScheduler(forecastseries)

        assert len(scheduler.past_forecasts) == 5
        assert abs(scheduler.schedule_starttime - next) < timedelta(seconds=1)

        schedule = rrule(freq=SECONDLY, interval=1800,
                         dtstart=next)

        assert str(schedule) == str(scheduler.rrule)

    def test_schema_instance_attr(self, mock_fs_get_by_id: MagicMock, prefect):
        forecastseries = ForecastSeries(
            oid=uuid.uuid4(),
            schedule_starttime=datetime(2021, 1, 2, 0, 0, 0))

        forecastseries2 = ForecastSeries(
            oid=uuid.uuid4(),
            schedule_starttime=datetime(2021, 1, 3, 0, 0, 0))

        mock_fs_get_by_id.return_value = forecastseries
        scheduler = ForecastSeriesScheduler(forecastseries.oid)

        mock_fs_get_by_id.return_value = forecastseries2
        scheduler2 = ForecastSeriesScheduler(forecastseries2.oid)

        scheduler.schedule_starttime = datetime(2024, 1, 2, 0, 0, 0)

        assert scheduler.forecastseries.schedule_starttime == datetime(
            2024, 1, 2, 0, 0, 0)

        assert scheduler.forecastseries.schedule_starttime != \
            scheduler2.forecastseries.schedule_starttime
