import asyncio
import logging
from datetime import datetime
from uuid import UUID

from dateutil.rrule import SECONDLY, rrule
from prefect.client.orchestration import get_client
from prefect.client.schemas.objects import DeploymentSchedule
from prefect.client.schemas.schedules import RRuleSchedule

from hermes.repositories.database import Session
from hermes.repositories.project import ForecastSeriesRepository
from hermes.schemas.project_schemas import (ForecastSeries,
                                            ForecastSeriesSchedule)


class ForecastSeriesAttr:
    """
    Given an object, acts as a proxy to the attributes of the object.
    """

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, instance, type=None) -> object:
        return getattr(instance.forecastseries, self._name)

    def __set__(self, instance, value):
        setattr(instance.forecastseries, self._name, value)


DEPLOYMENT_NAME = 'ForecastRunner/ForecastRunner'


class ForecastSeriesScheduler:

    schedule_starttime = ForecastSeriesAttr()
    schedule_interval = ForecastSeriesAttr()
    schedule_endtime = ForecastSeriesAttr()
    schedule_id = ForecastSeriesAttr()

    forecast_starttime = ForecastSeriesAttr()
    forecast_endtime = ForecastSeriesAttr()
    forecast_duration = ForecastSeriesAttr()

    def __init__(self, forecastseries_oid: UUID) -> None:

        self.logger = logging.getLogger(__name__)
        self.session = Session()
        self.forecastseries: ForecastSeries = \
            ForecastSeriesRepository.get_by_id(
                self.session, forecastseries_oid)

        self.deployment_name = DEPLOYMENT_NAME

        self.now = datetime.now()

        self.rrule = None

    def update(self, config: dict | None = None) -> None:

        if config is not None:
            schedule = ForecastSeriesSchedule(**config)
            for key, value in schedule.model_dump(exclude_unset=True).items():
                setattr(self, key, value)

        self.forecastseries = \
            ForecastSeriesRepository.update(self.session, self.forecastseries)

    def __del__(self) -> None:
        self.session.close()

    def _build_rrule(self) -> None:

        assert self.schedule_starttime is not None \
            and self.schedule_interval is not None \
            and (self.forecast_endtime or self.forecast_duration), \
            'Creating a schedule requires a schedule_starttime, '\
            'schedule_interval, and either forecast_endtime or ' \
            'forecast_duration.'

        # If the endtime is in the past, we don't need to create a schedule
        if self.schedule_endtime is not None and \
                self.schedule_endtime < self.now:
            return None

        # create a schedule which starts at schedule_starttime
        self.rrule = rrule(
            freq=SECONDLY,
            interval=self.schedule_interval,
            dtstart=self.schedule_starttime,
            until=self.schedule_endtime)

        # if schedule_starttime lies in the past, we need to use the next
        # regular occurrence of the schedule.
        if self.schedule_starttime < self.now:
            self.rrule = rrule(
                freq=SECONDLY,
                interval=self.schedule_interval,
                dtstart=self.rrule.after(self.now, inc=False),
                until=self.schedule_endtime)

    def create_prefect_schedule(self, schedule_config: dict) -> None:

        # check whether a schedule id exists, and if so, whether the schedule
        # still exists in prefect
        if self.schedule_id is not None:
            if asyncio.run(get_deployment_schedule_by_id(
                    self.deployment_name,
                    self.schedule_id)) is not None:
                raise ValueError(
                    'A schedule for this ForecastSeries already exists.')

        # update the ForecastSeries with the new schedule configuration
        self.update(schedule_config)

        self._build_rrule()

        if self.rrule is None:
            raise ValueError('Scheduled times are all in the past, '
                             'no schedule will be created.')

        # add the new schedule and save the schedule id to the ForecastSeries
        prefect_schedule = asyncio.run(add_deployment_schedule(
            self.deployment_name, self.rrule))
        self.schedule_id = prefect_schedule.id
        self.update()

    def update_prefect_schedule(self, schedule_config: dict) -> None:

        # check if a schedule id exists and if the schedule still exists
        if self.schedule_id is None or \
            asyncio.run(get_deployment_schedule_by_id(
                self.deployment_name, self.schedule_id)) is None:
            raise ValueError('No schedule for this ForecastSeries exists.')

        # update the Scheduler and ForecastSeries with the new schedule
        self.update(schedule_config)
        self._build_rrule()
        asyncio.run(update_deployment_schedule(self.deployment_name,
                                               self.schedule_id,
                                               self.rrule))

    def delete_prefect_schedule(self) -> None:

        # check if a schedule id exists and if the schedule still exists
        if self.schedule_id is not None and \
            asyncio.run(get_deployment_schedule_by_id(
                self.deployment_name, self.schedule_id)) is not None:
            asyncio.run(delete_deployment_schedule(self.deployment_name,
                                                   self.schedule_id))

        clear = {k: None for k in ForecastSeriesSchedule.__annotations__}

        self.update(clear)

    # def _set_past_forecasts(self):
    #     """
    #     If the forecast has a start time in the past, calculate the past
    #     forecast start and endtimes.
    #     """
    #     # If the start time is in the future,
    #     # we don't have any past forecasts
    #     if self.schedule_starttime > self.now:
    #         return None

    #     # if the endtime lies in the past, we only want to calculate
    #     # past forecasts up to the endtime
    #     if self.schedule_endtime is not None and \
    #             self.schedule_endtime < self.now:
    #         past_end = self.schedule_endtime
    #     # otherwise we calculate past forecasts up to the current time
    #     else:
    #         past_end = self.now

    #     # if no duration is specified, we want to avoid creating a forecast
    #     # which starts at the same time as the endtime
    #     if self.forecastseries.forecast_duration is None:
    #         past_end -= timedelta(seconds=1)

    #     rrule_past = rrule(freq=SECONDLY, interval=self.schedule_interval,
    #                        dtstart=self.schedule_starttime, until=past_end)

    #     self.past_forecasts = list(rrule_past)


async def add_deployment_schedule(
        deployment_name: str,
        schedule: rrule) -> DeploymentSchedule:

    async with get_client() as client:
        schedule = RRuleSchedule(rrule=str(schedule))
        deployment = await client.read_deployment_by_name(deployment_name)

        # Add the new schedule to the deployment
        [schedule] = await client.create_deployment_schedules(
            deployment_id=deployment.id,
            schedules=[(schedule, True)]
        )
        return schedule


async def get_deployment_schedule_by_id(
        deployment_name: str,
        schedule_id: UUID) -> DeploymentSchedule:

    async with get_client() as client:
        deployment = await client.read_deployment_by_name(deployment_name)
        schedules = await client.read_deployment_schedules(deployment.id)

    return next((s for s in schedules if s.id == schedule_id), None)


async def update_deployment_schedule(
        deployment_name: str,
        schedule_id: UUID,
        new_schedule: rrule) -> None:

    async with get_client() as client:
        deployment = await client.read_deployment_by_name(deployment_name)

        await client.update_deployment_schedule(
            deployment_id=deployment.id,
            schedule_id=schedule_id,
            schedule=RRuleSchedule(rrule=str(new_schedule))
        )


async def delete_deployment_schedule(
        deployment_name: str,
        schedule_id: UUID) -> None:

    async with get_client() as client:
        deployment = await client.read_deployment_by_name(deployment_name)
        await client.delete_deployment_schedule(
            deployment_id=deployment.id,
            schedule_id=schedule_id
        )
