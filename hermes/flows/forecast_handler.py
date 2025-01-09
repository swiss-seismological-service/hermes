import json
from datetime import datetime, timedelta
from logging import Logger
from typing import Literal
from uuid import UUID

from prefect import flow, get_run_logger, runtime, task
from prefect.deployments import run_deployment

from hermes.flows.modelrun_builder import ModelRunBuilder
from hermes.flows.modelrun_handler import default_model_runner
from hermes.io.hydraulics import HydraulicsDataSource
from hermes.io.seismicity import SeismicityDataSource
from hermes.repositories.data import (InjectionObservationRepository,
                                      InjectionPlanRepository,
                                      SeismicityObservationRepository)
from hermes.repositories.database import Session
from hermes.repositories.project import (ForecastRepository,
                                         ForecastSeriesRepository)
from hermes.schemas import Forecast
from hermes.schemas.base import EInput, EStatus
from hermes.schemas.data_schemas import InjectionObservation, InjectionPlan
from hermes.schemas.model_schemas import ModelConfig
from hermes.schemas.project_schemas import ForecastSeries
from hermes.utils.prefect import futures_wait


class ForecastHandler:
    def __init__(self,
                 forecastseries_oid: UUID,
                 starttime: datetime | None = None,
                 endtime: datetime | None = None,
                 observation_starttime: datetime | None = None,
                 observation_endtime: datetime | None = None,
                 observation_window: int | None = None) -> None:

        self.logger: Logger = get_run_logger()
        self.starttime: datetime
        self.endtime: datetime
        self.observation_starttime: datetime
        self.observation_endtime: datetime
        self.observation_window: int
        self.forecast: Forecast = None
        self.catalog_data_source: SeismicityDataSource = None
        self.hydraulic_data_source: HydraulicsDataSource = None

        with Session() as session:
            self.forecastseries: ForecastSeries = \
                ForecastSeriesRepository.get_by_id(
                    session, forecastseries_oid)
            self.modelconfigs: list[ModelConfig] = \
                ForecastSeriesRepository.get_model_configs(
                session, forecastseries_oid)

        if not self.modelconfigs:
            self.logger.warning('No ModelConfigs associated with the '
                                'ForecastSeries. Exiting.')
            return None

        self._set_forecast_timebounds(starttime,
                                      endtime,
                                      observation_starttime,
                                      observation_endtime,
                                      observation_window)

        self._create_forecast()

        try:
            # Retreive input data from various services
            task_so = self._create_seismicityobservation.submit()
            task_io = self._create_injectionobservation.submit()
            task_ip = self._create_injectionplan.submit()
            futures_wait([task_so, task_io, task_ip])

            # necessary to raise exceptions from the tasks if any failed
            [task_so.result(), task_io.result(), task_ip.result()]

            self.builder = ModelRunBuilder(self.forecast,
                                           self.forecastseries,
                                           self.modelconfigs)
        except BaseException as e:
            with Session() as session:
                ForecastRepository.update_status(session, self.forecast.oid,
                                                 EStatus.FAILED)
            raise e

    def __del__(self):
        self.logger.info('Closing session')

    @task(name='SubmitModelRuns', cache_policy=None)
    def run(self, mode: Literal['local', 'deploy'] = 'local') -> None:
        if not self.builder.runs:
            self.logger.warning('No modelruns to run.')
            with Session() as session:
                ForecastRepository.update_status(session, self.forecast.oid,
                                                 EStatus.CANCELLED)
            return None

        try:
            if mode == 'local':
                for run in self.builder.runs:
                    default_model_runner(*run)
            else:
                for run in self.builder.runs:
                    run_deployment(
                        name=f'DefaultModelRunner/{self.forecastseries.name}',
                        parameters={'modelrun_info': run[0],
                                    'modelconfig': run[1]},
                        timeout=0
                    )
        except BaseException as e:
            with Session() as session:
                ForecastRepository.update_status(session, self.forecast.oid,
                                                 EStatus.FAILED)
            raise e
        with Session() as session:
            ForecastRepository.update_status(session, self.forecast.oid,
                                             EStatus.COMPLETED)

    def _set_forecast_timebounds(self,
                                 starttime: datetime,
                                 endtime: datetime,
                                 observation_starttime: datetime,
                                 observation_endtime: datetime,
                                 observation_window: int) -> None:
        """
        Sets the forecast start and end times.

        starttime:  When running forecasts manually or catching up on a
                    schedule, the starttime should be passed as an argument.
                    Else, a fixed starttime can be set on the ForecastSeries.
                    If the forecasts are run on a schedule, the starttime
                    will be the scheduled start time of the flow run.
        endtime:    When running forecasts manually or catching up on a
                    schedule, the endtime should be passed as an argument.
                    Else, it is given by the two following fields on
                    the ForecastSeries:
                    forecast_duration, forecast_endtime.
        observation:Times should only be passed in either for manual runs
                    when required or when catching up on a schedule.
                    Otherwise, the observation starttime of the ForecastSeries
                    should be used, and the endtime usually equals the
                    starttime of the forecast.
        """
        # set start and endtime
        self.starttime = self.forecastseries.forecast_starttime or \
            starttime or \
            runtime.flow_run.scheduled_start_time

        if self.starttime.tzinfo is not None:
            self.starttime = self.starttime.replace(tzinfo=None)

        if self.forecastseries.forecast_starttime is not None and \
                self.starttime > self.forecastseries.forecast_starttime:
            raise ValueError(
                "Starttime can't be later than forecast_starttime.")

        # set endtime, forecast_duration takes precedence over forecast_endtime
        self.endtime = endtime or \
            (self.starttime
             + timedelta(seconds=self.forecastseries.forecast_duration)
             if self.forecastseries.forecast_duration else None) or \
            self.forecastseries.forecast_endtime
        # endtime can't be later than forecast_endtime
        if self.forecastseries.forecast_endtime is not None and \
                self.forecastseries.forecast_endtime < self.endtime:
            self.endtime = self.forecastseries.forecast_endtime

        if self.endtime.tzinfo is not None:
            self.endtime = self.endtime.replace(tzinfo=None)

        # set observation times
        self.observation_starttime = observation_starttime or \
            self.forecastseries.observation_starttime
        self.observation_endtime = observation_endtime or \
            self.forecastseries.observation_endtime or \
            self.starttime
        self.observation_window = observation_window or \
            self.forecastseries.observation_window
        if self.observation_starttime.tzinfo is not None:
            self.observation_starttime = self.observation_starttime.replace(
                tzinfo=None)
        if self.observation_endtime.tzinfo is not None:
            self.observation_endtime = self.observation_endtime.replace(
                tzinfo=None)

        # user can't pass both observation times and observation window
        if (self.observation_starttime is not None
            or self.observation_endtime != self.starttime) and \
                self.observation_window is not None:
            raise ValueError("You can't have an observation start/end time "
                             "and an observation_window.")

        # if observation window is passed, calculate observation start time
        if self.observation_window is not None:
            self.observation_starttime = self.starttime - \
                timedelta(seconds=self.observation_window)

        # Sanity Checks
        if self.observation_starttime == self.observation_endtime:
            raise ValueError("Observation start and end time can't be equal.")
        if self.observation_starttime > self.observation_endtime:
            raise ValueError("Observation start time can't be later than "
                             "observation end time.")

        if self.starttime == self.endtime:
            raise ValueError("Forecast start and end time can't be equal.")
        print(self.starttime)
        print(self.endtime)
        if self.starttime > self.endtime:
            raise ValueError("Forecast start time can't be later than "
                             "forecast end time.")

    @task(name='CreateForecast', cache_policy=None)
    def _create_forecast(self) -> None:
        """
        Creates the forecast in the database.
        """
        new_forecast = self.forecast or Forecast(
            forecastseries_oid=self.forecastseries.oid,
            status='PENDING',
            starttime=self.starttime,
            endtime=self.endtime,
        )
        with Session() as session:
            self.forecast: Forecast = ForecastRepository.create(
                session, new_forecast)

    @task(name='CreateSeismicityObservation', cache_policy=None)
    def _create_seismicityobservation(self) -> None:
        """
        Gets the seismicity observation data and stores it to the database.
        """

        if self.forecastseries.seismicityobservation_required == \
                EInput.NOT_ALLOWED:
            self.forecast.seismicity_observation = None
            return None

        self.catalog_data_source = SeismicityDataSource.from_uri(
            self.forecastseries.fdsnws_url,
            self.observation_starttime,
            self.observation_endtime
        )

        with Session() as session:
            self.forecast.seismicity_observation = \
                SeismicityObservationRepository.create_from_quakeml(
                    session,
                    self.catalog_data_source.get_quakeml(),
                    self.forecast.oid
                )

    @task(name='CreateInjectionObservation', cache_policy=None)
    def _create_injectionobservation(self) -> None:
        """
        Gets the injection observation data and stores it to the database.
        """
        if self.forecastseries.injectionobservation_required == \
                EInput.NOT_ALLOWED:
            self.forecast.injection_observation = None
            return None

        self.hydraulic_data_source = HydraulicsDataSource.from_uri(
            self.forecastseries.hydws_url,
            self.observation_starttime,
            self.observation_endtime
        )

        hydraulics = InjectionObservation(
            forecast_oid=self.forecast.oid,
            data=self.hydraulic_data_source.get_json()
        )
        with Session() as session:
            self.forecast.injection_observation = \
                InjectionObservationRepository.create(
                    session,
                    hydraulics
                )

    @task(name='CreateInjectionPlan', cache_policy=None)
    def _create_injectionplan(self) -> None:
        """
        Gets the injection plan data and stores it to the database.
        """
        if self.forecastseries.injectionplan_required == \
                EInput.NOT_ALLOWED:
            self.forecastseries.injection_plans = None
            return None

        with Session() as session:
            injection_plans = \
                InjectionPlanRepository.get_by_forecastseries(
                    session,
                    self.forecastseries.oid
                )

            if not injection_plans:
                if self.forecastseries.injectionplan_required == \
                        EInput.OPTIONAL:
                    self.forecastseries.injection_plans = None
                    return None
                else:
                    raise ValueError('No injection plans found for the '
                                     'ForecastSeries.')

            for idx, ip in enumerate(injection_plans):
                data = HydraulicsDataSource.from_data(json.loads(ip.data),
                                                      self.starttime,
                                                      self.endtime)

                new_ip = InjectionPlan(
                    name=ip.name,
                    data=data.get_json()
                )

                injection_plans[idx] = InjectionPlanRepository.create(
                    session, new_ip)

        self.forecastseries.injection_plans = injection_plans


def generate_flow_run_name():
    """
    Try to use starttime to generate a name for the flow run.
    """

    parameters = runtime.flow_run.parameters
    start = parameters["starttime"] or \
        runtime.flow_run.scheduled_start_time or None

    if start:
        end = parameters["endtime"] or None
        if end:
            return f"Forecast-{start}-{end}"
        else:
            return f"Forecast-{start}"

    return f"Forecast-{parameters['forecastseries_oid']}"


@flow(name='ForecastRunner', flow_run_name=generate_flow_run_name)
def forecast_runner(forecastseries_oid: UUID,
                    starttime: datetime | None = None,
                    endtime: datetime | None = None,
                    mode: Literal['local', 'deploy'] = 'local') \
        -> ForecastHandler:
    forecasthandler = ForecastHandler(forecastseries_oid, starttime, endtime)
    forecasthandler.run(mode)
    return forecasthandler
