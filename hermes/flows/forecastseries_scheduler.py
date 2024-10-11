import asyncio
from datetime import datetime, timedelta

from dateutil.rrule import SECONDLY, rrule
from prefect.client.orchestration import get_client
from prefect.client.schemas.schedules import RRuleSchedule

from hermes.schemas import ForecastSeries


class ForecastSeriesScheduler:
    def __init__(self, forecastseries: ForecastSeries):
        assert forecastseries.forecast_starttime is not None
        assert forecastseries.forecast_interval is not None
        assert forecastseries.forecast_endtime or \
            forecastseries.forecast_duration

        self.forecastseries = forecastseries
        self.start = forecastseries.forecast_starttime
        self.end = forecastseries.forecast_endtime
        self.interval = forecastseries.forecast_interval
        self.duration = forecastseries.forecast_duration
        self.now = datetime.now()

        self.past_forecasts = []
        self._set_past_forecasts()

        self.schedule = None
        self._create_schedule()

    def _set_past_forecasts(self):
        """
        If the forecast has a start time in the past, calculate the past
        forecast start and endtimes.
        """
        # If the start time is in the future, we don't have any past forecasts
        if self.start > self.now:
            return None

        # if the endtime lies in the past, we only want to calculate
        # past forecasts up to the endtime
        if self.end is not None and self.end < self.now:
            past_end = self.end
        # otherwise we calculate past forecasts up to the current time
        else:
            past_end = self.now

        # if no duration is specified, we want to avoid creating a forecast
        # which starts at the same time as the endtime
        if self.duration is None:
            past_end -= timedelta(seconds=1)

        rrule_past = rrule(freq=SECONDLY, interval=self.interval,
                           dtstart=self.start, until=past_end)

        self.past_forecasts = list(rrule_past)

    def _create_schedule(self):

        if self.end is not None and self.end < self.now:
            return None

        if self.start < self.now:
            rrule_full = rrule(freq=SECONDLY, interval=self.interval,
                               dtstart=self.start, until=self.end)
            self.start = rrule_full.after(self.now, inc=False)

        self.schedule = rrule(freq=SECONDLY, interval=self.interval,
                              dtstart=self.start, until=self.end)

    def run(self):
        # asyncio.run(add_schedule_to_deployment())
        return None


async def add_schedule_to_deployment(deployment_name: str, schedule: rrule):
    async with get_client() as client:
        schedule = RRuleSchedule(rrule=str(schedule))
        deployment = await client.read_deployment(deployment_name)

        # Add the new schedule to the deployment
        await client.create_deployment_schedules(
            deployment_id=deployment.id,
            schedule=schedule
        )
