from datetime import datetime, timedelta
from uuid import UUID

from prefect import flow, get_run_logger, runtime, task

from hermes.flows.get_catalog import get_catalog
from hermes.flows.model_runner import ModelRunner
from hermes.repositories.data import SeismicityObservationRepository
from hermes.repositories.database import Session
from hermes.repositories.project import (ForecastRepository,
                                         ForecastSeriesRepository,
                                         ProjectRepository)
from hermes.schemas import (EInput, Forecast, ModelConfig, ModelInput,
                            ModelRunInfo, SeismicityObservation)
from hermes.schemas.base import EStatus


@flow(name='ForecastRunner')
def factory(
    forecastseries: UUID,
    starttime: datetime | None = None,
    endtime: datetime | None = None,
    modelconfigs: ModelConfig | None = None
) -> None:
    return ForecastRunner(forecastseries, starttime, endtime, modelconfigs)


class ForecastRunner:
    @task(name="ForecastRunner")
    def __init__(self,
                 forecastseries_oid: UUID,
                 starttime: datetime | None = None,
                 endtime: datetime | None = None,
                 modelconfigs: ModelConfig | None = None):

        self.logger = get_run_logger()
        self.session = Session()
        self.forecastseries = ForecastSeriesRepository.get_by_id(
            self.session, forecastseries_oid)
        self.project = \
            ProjectRepository.get_by_id(self.session,
                                        self.forecastseries.project_oid)
        self.forecast = None
        self.model_run_infos = []

        try:
            self._create_forecast(starttime, endtime)
            self._create_seismicityobservation()
            self._prepare_model_run_infos(modelconfigs)
            self.run()
        except BaseException as e:
            self.update_status(EStatus.FAILED)
            raise e

    def __del__(self):
        self.logger.info('Closing session')
        self.session.close()

    def update_status(self, status: EStatus):
        self.forecast = ForecastRepository.update_status(
            self.session, self.forecast.oid, status)

    @task
    def _create_forecast(self, starttime, endtime):
        if not starttime:
            starttime = runtime.flow_run.scheduled_start_time

        if not endtime:
            endtime = starttime + timedelta(
                seconds=self.forecastseries.forecast_duration)

        # create Forecast and store to database
        forecast = Forecast(
            name=f'forecast_{starttime.strftime("%Y-%m-%dT%H:%M:%S")}',
            forecastseries_oid=self.forecastseries.oid,
            status='PENDING',
            starttime=starttime,
            endtime=endtime,
        )
        self.forecast = ForecastRepository.create(self.session, forecast)

    @task
    def _create_seismicityobservation(self):
        if self.project.seismicityobservation_required == EInput.NOT_ALLOWED:
            self.forecast.seismicity_observation = None

        seismicity = SeismicityObservation(
            forecast_oid=self.forecast.oid,
            data=get_catalog(self.project.fdsnws_url,
                             self.forecastseries.observation_starttime,
                             self.forecast.starttime).to_quakeml()
        )

        self.forecast.seismicity_observation = \
            SeismicityObservationRepository.create(
                self.session,
                seismicity
            )

    @task
    def _prepare_model_run_infos(self, modelconfigs=None):
        if not modelconfigs:
            modelconfigs = ForecastSeriesRepository.get_model_configs(
                self.session, self.forecast.forecastseries_oid)

        for config in modelconfigs:
            model = ModelInput(
                forecast_start=self.forecast.starttime,
                forecast_end=self.forecast.endtime,
                bounding_polygon=self.forecastseries.bounding_polygon,
                depth_min=self.forecastseries.depth_min,
                depth_max=self.forecastseries.depth_max,
                config=config.config,
                seismicity_observation=(
                    self.forecast.seismicity_observation.data
                )
            )

            self.model_run_infos.append(
                ModelRunInfo(
                    config=config,
                    input=model
                )
            )

    @task(name='RunForecast')
    def run(self):
        for run_info in self.model_run_infos:
            model_runner = ModelRunner(
                self.session, run_info, self.forecast)
            model_runner.run()


if __name__ == '__main__':
    factory.serve()
