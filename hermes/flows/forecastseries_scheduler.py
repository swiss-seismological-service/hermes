# import asyncio
from datetime import datetime, timedelta
from uuid import UUID

from dateutil.rrule import SECONDLY, rrule
from prefect import get_run_logger
from prefect.client.orchestration import get_client
from prefect.client.schemas.schedules import RRuleSchedule

from hermes.flows.forecast_handler import forecast_runner
from hermes.repositories.database import Session
from hermes.repositories.project import ForecastSeriesRepository
from hermes.schemas.project_schemas import ForecastSeries


class ForecastSeriesScheduler:
    def __init__(self, forecastseries_oid: UUID):

        self.logger = get_run_logger()
        self.session = Session()
        self.forecastseries: ForecastSeries = \
            ForecastSeriesRepository.get_by_id(
                self.session, forecastseries_oid)

        assert self.forecastseries.schedule_starttime is not None
        assert self.forecastseries.schedule_interval is not None
        assert self.forecastseries.forecast_endtime or \
            self.forecastseries.forecast_duration

        self.start = self.forecastseries.schedule_starttime
        self.end = self.forecastseries.schedule_endtime
        self.interval = self.forecastseries.schedule_interval
        self.now = datetime.now()

        self.name = f"schedule_{self.forecastseries.oid}"

        self.past_forecasts = []
        self._set_past_forecasts()

        self.schedule = None
        self._create_schedule()

    def __del__(self):
        self.logger.info('Closing session')
        self.session.close()

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
        if self.forecastseries.forecast_duration is None:
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
        # asyncio.run(add_schedule_to_deployment('name/name', self.schedule))

        for starttime in self.past_forecasts:
            forecast_runner(self.forecastseries.oid, starttime)

        return None


async def add_schedule_to_deployment(deployment_name: str, schedule: rrule):
    async with get_client() as client:
        schedule = RRuleSchedule(rrule=str(schedule))
        deployment = await client.read_deployment_by_name(deployment_name)

        # Add the new schedule to the deployment
        await client.create_deployment_schedules(
            deployment_id=deployment.id,
            schedules=[(schedule, True)]
        )


async def update_schedule(name: str, schedule_id: UUID, new_schedule: rrule):

    async with get_client() as client:
        deployment = await client.read_deployment_by_name(name)

        await client.update_deployment_schedule(
            deployment_id=deployment.id,
            schedule_id=schedule_id,
            schedule=RRuleSchedule(rrule=str(new_schedule))
        )
