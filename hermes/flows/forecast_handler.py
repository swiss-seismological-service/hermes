from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from prefect import flow, get_run_logger, runtime, task
from prefect.deployments import run_deployment

from hermes.config import get_settings
from hermes.flows.modelrun_builder import ModelRunBuilder
from hermes.flows.modelrun_handler import default_model_runner
from hermes.io.hydraulics import HydraulicsDataSource
from hermes.io.seismicity import SeismicityDataSource
from hermes.repositories.data import (InjectionObservationRepository,
                                      SeismicityObservationRepository)
from hermes.repositories.database import Session
from hermes.repositories.project import (ForecastRepository,
                                         ForecastSeriesRepository)
from hermes.schemas import Forecast
from hermes.schemas.base import EInput, EStatus
from hermes.schemas.data_schemas import (InjectionObservation,
                                         SeismicityObservation)
from hermes.schemas.model_schemas import ModelConfig
from hermes.schemas.project_schemas import ForecastSeries
from hermes.utils.prefect import futures_wait


class ForecastHandler:
    def __init__(self,
                 forecastseries_oid: UUID,
                 starttime: datetime | None = None,
                 endtime: datetime | None = None,
                 observation_starttime: datetime | None = None,
                 observation_endtime: datetime | None = None) -> None:

        self.logger = get_run_logger()
        # self.session = Session()

        tz = get_settings().TIMEZONE
        self.timezone = ZoneInfo(tz) if tz else None

        with Session() as session:
            self.forecastseries: ForecastSeries = \
                ForecastSeriesRepository.get_by_id(
                    session, forecastseries_oid)
            self.modelconfigs: list[ModelConfig] = \
                ForecastSeriesRepository.get_model_configs(
                session, forecastseries_oid)

        self.starttime: datetime
        self.endtime: datetime
        self.observation_starttime: datetime
        self.observation_endtime: datetime
        self.set_forecast_timebounds(starttime,
                                     endtime,
                                     observation_starttime,
                                     observation_endtime)

        self.forecast: Forecast = None
        self._create_forecast()

        self.catalog_data_source: SeismicityDataSource = None
        self.hydraulic_data_source: HydraulicsDataSource = None

        try:
            # Retreive input data from various services
            task_so = self._create_seismicityobservation.submit()
            task_io = self._create_injectionobservation.submit()
            futures_wait([task_so, task_io])
        except BaseException as e:
            with Session() as session:
                ForecastRepository.update_status(session, self.forecast.oid,
                                                 EStatus.FAILED)
            raise e

        self.builder = ModelRunBuilder(self.forecast,
                                       self.forecastseries,
                                       self.modelconfigs)

    def __del__(self):
        self.logger.info('Closing session')
        # self.session.close()

    def set_forecast_timebounds(self,
                                starttime: datetime,
                                endtime: datetime,
                                observation_starttime: datetime,
                                observation_endtime: datetime) -> None:
        """
        Sets the forecast start and end times.

        Starttime:  When running forecasts manually or catching up on a
                    schedule, the starttime should be passed as an argument.
                    Else, a fixed starttime can be set on the ForecastSeries,
                    which I'm not sure if is needed.
                    If the forecasts are run on a schedule, the starttime
                    will be the scheduled start time of the flow run.
        Endtime:    When running forecasts manually or catching up on a
                    schedule, the endtime should be passed as an argument.
                    Else, it is given by one of the two following fields on
                    the ForecastSeries:
                    forecast_duration (priority), forecast_endtime.
        Observation:Times should only be passed in either for manual runs
                    when required or when catching up on a schedule.
                    Otherwise, the observation starttime of the ForecastSeries
                    should be used, and the endtime usually equals the
                    starttime of the forecast.
        """
        self.starttime = starttime or \
            self.forecastseries.forecast_starttime or \
            runtime.flow_run.scheduled_start_time

        self.endtime = endtime or \
            (self.starttime
             + timedelta(seconds=self.forecastseries.forecast_duration)
             if self.forecastseries.forecast_duration else None) or \
            self.forecastseries.forecast_endtime

        # TODO: Think hard and carefully about timezones
        # and where they should be set/unset.
        if self.starttime.tzinfo is not None:
            self.starttime = self.starttime.replace(tzinfo=None)
        if self.endtime.tzinfo is not None:
            self.endtime = self.endtime.replace(tzinfo=None)

        self.observation_starttime = observation_starttime or \
            self.forecastseries.observation_starttime
        self.observation_endtime = observation_endtime or \
            self.forecastseries.observation_endtime or \
            self.starttime

        if self.observation_starttime.tzinfo is not None:
            self.observation_starttime = self.observation_starttime.replace(
                tzinfo=None)
        if self.observation_endtime.tzinfo is not None:
            self.observation_endtime = self.observation_endtime.replace(
                tzinfo=None)

    @task
    def run(self, mode: Literal['local', 'deploy'] = 'local') -> None:
        if mode == 'local':
            for run in self.builder.runs:
                default_model_runner(*run)
        else:
            for run in self.builder.runs:
                run_deployment(
                    name='DefaultModelRunner/DefaultModelRunner',
                    parameters={'modelrun_info': run[0],
                                'modelconfig': run[1]},
                    timeout=0
                )

    @task
    def _create_forecast(self) -> None:
        """
        Creates or updates the forecast in the database.
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

    @task
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

        seismicity = SeismicityObservation(
            forecast_oid=self.forecast.oid,
            data=self.catalog_data_source.get_quakeml()
        )
        with Session() as session:
            self.forecast.seismicity_observation = \
                SeismicityObservationRepository.create(
                    session,
                    seismicity
                )

    @task
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


@flow(name='ForecastRunner')
def forecast_runner(forecastseries_oid: UUID,
                    starttime: datetime | None = None,
                    endtime: datetime | None = None,
                    mode: Literal['local', 'deploy'] = 'local') \
        -> ForecastHandler:
    forecasthandler = ForecastHandler(forecastseries_oid, starttime, endtime)
    forecasthandler.run(mode)
    return forecasthandler
