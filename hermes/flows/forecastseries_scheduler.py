import asyncio
import logging
from datetime import datetime, timedelta
from uuid import UUID

from dateutil.rrule import SECONDLY, rrule
from prefect import get_run_logger
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


DEPLOYMENT_NAME = 'ForecastRunner/{}'


class ForecastSeriesScheduler:

    schedule_starttime = ForecastSeriesAttr()
    schedule_interval = ForecastSeriesAttr()
    schedule_endtime = ForecastSeriesAttr()
    schedule_id = ForecastSeriesAttr()
    schedule_active = ForecastSeriesAttr()

    forecast_starttime = ForecastSeriesAttr()
    forecast_endtime = ForecastSeriesAttr()
    forecast_duration = ForecastSeriesAttr()

    def __init__(self, forecastseries_oid: UUID) -> None:
        try:
            self.logger = get_run_logger()
        except BaseException:
            self.logger = logging.getLogger('prefect.hermes')
        self.session = Session()
        self.forecastseries: ForecastSeries = \
            ForecastSeriesRepository.get_by_id(
                self.session, forecastseries_oid)

        self.deployment_name = DEPLOYMENT_NAME.format(self.forecastseries.name)

        self.now = datetime.now()

        if self.schedule_active is None:
            self.schedule_active = True

    def __del__(self) -> None:
        try:
            self.session.close()
        except BaseException:
            pass

    def schedule(self, schedule_config: dict) -> None:
        '''
        Creates or updates a schedule based on the given configuration.

        args:
            schedule_config: dict
                A dictionary with the configuration to create or update a
                schedule.
        '''
        self._check_schedule_validity(schedule_config)

        schedule_exists = self.schedule_id is not None and \
            asyncio.run(get_deployment_schedule_by_id(
                self.deployment_name, self.schedule_id)) is not None

        if self._is_schedule_in_past(schedule_config):
            # No prefect schedule should be created
            if schedule_exists:
                self._delete_prefect_schedule()
            self._unset_schedule(False)
            self._update(schedule_config)
            self.logger.info('No future schedule was created, '
                             'all forecasts are in the past.')
        elif schedule_exists:
            self._update_prefect_schedule(schedule_config)
            self.logger.info('Schedule successfully updated.')
        else:
            self._create_prefect_schedule(schedule_config)
            self.logger.info('Schedule successfully created.')

    def _update(self, config: dict | None = None, update_db: bool = True) \
            -> None:
        '''
        Updates the ForecastSeries object with the given configuration.

        args:
            config: dict
                A dictionary with the configuration to update.
            update_db: bool
                If True, the changes will be saved to the database.
        '''
        if config is not None:
            schedule = ForecastSeriesSchedule(**config)
            for key, value in schedule.model_dump(exclude_unset=True).items():
                setattr(self, key, value)

        if update_db:
            self.forecastseries = ForecastSeriesRepository.update(
                self.session, self.forecastseries)

    def _check_schedule_validity(self, schedule_config: dict) -> None:
        schedule = ForecastSeriesSchedule(**schedule_config)

        if schedule.schedule_starttime is None \
                or schedule.schedule_interval is None:
            raise ValueError(
                'Creating a schedule always requires a '
                'schedule_starttime, schedule_interval')

        if schedule.forecast_endtime is None \
                and schedule.forecast_duration is None:
            raise ValueError(
                'Creating a schedule always requires a '
                'forecast_endtime or/and a forecast_duration')

        if schedule.schedule_endtime is not None and \
            schedule.forecast_endtime is not None and \
                schedule.schedule_endtime >= schedule.forecast_endtime:
            raise ValueError(
                'Cannot create a schedule with a schedule endtime which is '
                'after the forecast endtime.')

        if schedule.forecast_starttime is not None and \
                schedule.schedule_endtime is not None and \
                schedule.forecast_starttime < schedule.schedule_endtime:
            raise ValueError(
                'Cannot create a schedule with a schedule endtime which is '
                'after the forecast starttime.')

        # if no schedule endtime is specified, check whether it is constrained
        # by the forecast starttime or forecast endtime and set explicitly
        if schedule.schedule_endtime is None and \
                schedule.forecast_starttime is not None:
            # no schedules should be created after the forecast starttime
            schedule.schedule_endtime = schedule.forecast_starttime
        elif schedule.schedule_endtime is None and \
                schedule.forecast_endtime is not None:
            # no schedules should be created after the forecast endtime
            schedule.schedule_endtime = schedule.forecast_endtime - \
                timedelta(seconds=schedule.schedule_interval - 1)

    def _is_schedule_in_past(self, schedule_config: dict) -> bool:
        """
        Check if the schedule is already fully in the past.

        I.e. returns False if forecasts will be created in the future.
        """
        schedule = ForecastSeriesSchedule(**schedule_config)

        if schedule.schedule_endtime is not None and \
                schedule.schedule_endtime < self.now:
            return True

        if schedule.schedule_endtime is None and \
                schedule.forecast_endtime is not None and \
                schedule.forecast_endtime < self.now:
            return True

        return False

    def _build_rrule(self, future=False) -> rrule:
        '''
        Builds a rrule object based on the ForecastSeries attributes.

        args:
            future: bool
                If True, the next regular occurrence of the schedule will be
                returned. If False, the schedule will start at the
                schedule_starttime.
        '''
        # create a schedule which starts at schedule_starttime
        rule = rrule(
            freq=SECONDLY,
            interval=self.schedule_interval,
            dtstart=self.schedule_starttime,
            until=self.schedule_endtime)

        if future:
            if self.schedule_endtime and \
                    self.schedule_endtime < self.now:
                raise ValueError('No future schedule can be created, '
                                 'the schedule endtime is in the past.')

            rule = rrule(
                freq=SECONDLY,
                interval=self.schedule_interval,
                dtstart=rule.after(self.now, inc=False),
                until=self.schedule_endtime)

        return rule

    def _unset_schedule(self, update_db: bool = True) -> None:
        '''
        Clears all schedule attributes except for `schedule_active`.

        args:
            update_db: bool
                If True, the changes will be saved to the database.
        '''
        clear = {k: None for k in ForecastSeriesSchedule.__annotations__}
        del clear['schedule_active']
        self._update(clear, update_db)

    def _create_prefect_schedule(self, schedule_config: dict) -> None:
        # create new prefect schedule
        self._unset_schedule(False)
        self._update(schedule_config, update_db=False)
        rule = self._build_rrule(True)

        # add the new schedule and save the schedule id
        prefect_schedule = asyncio.run(add_deployment_schedule(
            self.deployment_name, rule, self.schedule_active))

        self.schedule_id = prefect_schedule.id

        # update data locally and on the database
        self._update()

    def _update_prefect_schedule(self, schedule_config: dict) -> None:
        # update existing prefect schedule
        schedule_config['schedule_id'] = self.schedule_id
        self._unset_schedule(False)
        self._update(schedule_config, update_db=False)
        rule = self._build_rrule(True)

        # update the schedule status if necessary
        if 'schedule_active' in schedule_config:
            asyncio.run(
                update_deployment_schedule_status(self.deployment_name,
                                                  self.schedule_id,
                                                  self.schedule_active))

        # update the schedule in prefect
        asyncio.run(
            update_deployment_schedule(self.deployment_name,
                                       self.schedule_id,
                                       rule))

        # update data locally and on the database
        self._update()

    def _delete_prefect_schedule(self) -> None:

        # check if a schedule id exists and if the schedule still exists
        if self.schedule_id is not None and \
            asyncio.run(get_deployment_schedule_by_id(
                self.deployment_name, self.schedule_id)) is not None:
            asyncio.run(delete_deployment_schedule(self.deployment_name,
                                                   self.schedule_id))

        self._unset_schedule()

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
        schedule: rrule,
        active: bool = True) -> DeploymentSchedule:

    async with get_client() as client:
        schedule = RRuleSchedule(rrule=str(schedule))
        deployment = await client.read_deployment_by_name(deployment_name)

        # Add the new schedule to the deployment
        [schedule] = await client.create_deployment_schedules(
            deployment_id=deployment.id,
            schedules=[(schedule, active)]
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


async def update_deployment_schedule_status(
        deployment_name: str,
        schedule_id: UUID,
        active: bool) -> None:

    async with get_client() as client:
        deployment = await client.read_deployment_by_name(deployment_name)

        await client.update_deployment_schedule(
            deployment_id=deployment.id,
            schedule_id=schedule_id,
            active=active
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
