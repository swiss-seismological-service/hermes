from datetime import datetime, timedelta

from prefect import flow, runtime, task

from hermes.flows.get_catalog import get_catalog
from hermes.repositories.data import SeismicityObservationRepository
from hermes.repositories.project import (ForecastRepository,
                                         ForecastSeriesRepository,
                                         ProjectRepository)
from hermes.repositories.types import SessionType
from hermes.schemas import (EInput, Forecast, ForecastSeries, ModelConfig,
                            ModelInput, ModelRunInfo, SeismicityObservation)


class ForecastExecutor:
    @flow(name='ForecastExecutor')
    def __init__(self,
                 session: SessionType,
                 forecastseries: ForecastSeries,
                 starttime: datetime | None = None,
                 endtime: datetime | None = None,
                 modelconfigs: ModelConfig | None = None):

        self.session = session
        self.project = ProjectRepository.get_by_id(session,
                                                   forecastseries.project_oid)
        self.forecastseries = forecastseries
        self.forecast = None
        self.model_run_infos = []

        self._create_forecast(starttime, endtime)
        self._create_seismicityobservation()
        self._prepare_model_run_infos(modelconfigs)

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

    @flow
    def run(self):
        raise NotImplementedError


if __name__ == '__main__':

    from hermes.repositories.database import Session

    with Session() as session:
        forecastseries = ForecastSeriesRepository.get_by_name(
            session, 'test_forecastseries')

        fex = ForecastExecutor(session, forecastseries,
                               datetime(2021, 1, 1, 13),
                               datetime(2021, 1, 1, 14))

        print(type(fex.model_run_infos[0]))
        print(len(fex.model_run_infos))
