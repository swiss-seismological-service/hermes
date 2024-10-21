from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from prefect import flow, get_run_logger, runtime, task
from prefect.deployments import run_deployment

from hermes.flows.catalog_readers import get_catalog
from hermes.flows.modelrun_builder import ModelRunBuilder
from hermes.flows.modelrun_handler import default_model_runner
from hermes.repositories.data import SeismicityObservationRepository
from hermes.repositories.database import Session
from hermes.repositories.project import (ForecastRepository,
                                         ForecastSeriesRepository)
from hermes.schemas import Forecast
from hermes.schemas.base import EInput, EStatus
from hermes.schemas.data_schemas import SeismicityObservation
from hermes.utils.prefect import futures_wait


class ForecastHandler:
    def __init__(self,
                 forecastseries_oid: UUID,
                 starttime: datetime | None = None,
                 endtime: datetime | None = None):

        self.logger = get_run_logger()
        self.session = Session()

        self.forecastseries = ForecastSeriesRepository.get_by_id(
            self.session, forecastseries_oid)
        self.modelconfigs = ForecastSeriesRepository.get_model_configs(
            self.session, forecastseries_oid)

        self.starttime = starttime or \
            self.forecastseries.forecast_starttime or \
            runtime.flow_run.scheduled_start_time
        self.endtime = endtime or \
            self.starttime + timedelta(
                seconds=self.forecastseries.forecast_duration) or \
            self.forecastseries.forecast_endtime

        self.starttime = self.starttime.astimezone(
            timezone.utc).replace(tzinfo=None)
        self.endtime = self.endtime.astimezone(
            timezone.utc).replace(tzinfo=None)

        self.forecast = None
        self._create_forecast()

        try:
            # Retreive input data from various services
            task_so = self._create_seismicityobservation.submit()
            task_io = self._create_injectionobservation.submit()
            task_ip = self._read_injectionplans.submit()
            futures_wait([task_so, task_io, task_ip])
        except BaseException as e:
            ForecastRepository.update_status(self.session, self.forecast.oid,
                                             EStatus.FAILED)
            raise e

        self.builder = ModelRunBuilder(self.forecast,
                                       self.forecastseries,
                                       self.modelconfigs)

    def __del__(self):
        self.logger.info('Closing session')
        self.session.close()

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

        new_forecast = self.forecast or Forecast(
            forecastseries_oid=self.forecastseries.oid,
            status='PENDING',
            starttime=self.starttime,
            endtime=self.endtime,
        )
        self.forecast = ForecastRepository.create(self.session, new_forecast)

    @task
    def _create_seismicityobservation(self) -> None:
        """
        Gets the seismicity observation data and stores it to the database.
        """

        if self.forecastseries.seismicityobservation_required == \
                EInput.NOT_ALLOWED:
            self.forecast.seismicity_observation = None
            return None

        seismicity = SeismicityObservation(
            forecast_oid=self.forecast.oid,
            data=get_catalog(
                self.forecastseries.fdsnws_url,
                self.forecastseries.observation_starttime,
                self.starttime).to_quakeml()
        )

        self.forecast.seismicity_observation = \
            SeismicityObservationRepository.create(
                self.session,
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
        else:
            raise NotImplementedError

    @task
    def _read_injectionplans(self) -> None:
        """
        Reads the injection plans of the respective ForecastSeries
        from the database.
        """
        if self.forecastseries.injectionplan_required == EInput.NOT_ALLOWED:
            self.forecastseries.injection_plans = None
        else:
            raise NotImplementedError


@flow(name='ForecastRunner')
def forecast_runner(forecastseries_oid: UUID,
                    starttime: datetime | None = None,
                    endtime: datetime | None = None,
                    mode: Literal['local', 'deploy'] = 'local') -> None:
    forecasthandler = ForecastHandler(forecastseries_oid, starttime, endtime)
    forecasthandler.run(mode)
    return forecasthandler
