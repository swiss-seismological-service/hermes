from datetime import datetime, timedelta
from uuid import UUID

from prefect import flow, get_run_logger, runtime, task

from hermes.flows.get_catalog import get_catalog
from hermes.flows.model_runner import model_flow_runner
from hermes.repositories.data import SeismicityObservationRepository
from hermes.repositories.database import Session
from hermes.repositories.project import (ForecastRepository,
                                         ForecastSeriesRepository,
                                         ProjectRepository)
from hermes.schemas import (EInput, Forecast, ModelRunInfo,
                            SeismicityObservation)
from hermes.schemas.base import EStatus
from hermes.schemas.data_schemas import InjectionPlan
from hermes.schemas.project_schemas import ModelConfig
from hermes.utils.prefect import futures_wait


@flow(name='ForecastRunner')
def forecast_flow_runner(forecastseries: UUID,
                         starttime: datetime | None = None,
                         endtime: datetime | None = None) -> None:
    builder = ForecastBuilder(forecastseries, starttime, endtime)
    runs = builder.build_runs()
    for run in runs:
        model_flow_runner(run)


class ForecastBuilder:
    @task(name="ForecastBuilder")
    def __init__(self,
                 forecastseries_oid: UUID,
                 starttime: datetime | None = None,
                 endtime: datetime | None = None):

        self.logger = get_run_logger()
        self.session = Session()

        self.forecastseries = ForecastSeriesRepository.get_by_id(
            self.session, forecastseries_oid)
        self.project = ProjectRepository.get_by_id(
            self.session, self.forecastseries.project_oid)
        self.modelconfigs = ForecastSeriesRepository.get_model_configs(
            self.session, forecastseries_oid)

        self.forecast = None
        self._create_forecast(starttime, endtime)

        try:
            # Retreive input data from various services
            task_so = self._create_seismicityobservation.submit()
            task_io = self._create_injectionobservation.submit()
            task_ip = self._read_injectionplans.submit()
            futures_wait([task_so, task_io, task_ip])
        except BaseException as e:
            self.update_status(EStatus.FAILED)
            raise e

    def __del__(self):
        print('Closing session')
        self.session.close()

    def update_status(self, status: EStatus):
        if self.forecast.oid:
            self.forecast = ForecastRepository.update_status(
                self.session, self.forecast.oid, status)

    @task
    def _create_forecast(self,
                         starttime: datetime | None,
                         endtime: datetime | None) -> None:

        starttime = starttime or runtime.flow_run.scheduled_start_time
        endtime = endtime or starttime + timedelta(
            seconds=self.forecastseries.forecast_duration)

        forecast = Forecast(
            name=f'forecast_{starttime.strftime("%Y-%m-%dT%H:%M:%S")}',
            forecastseries_oid=self.forecastseries.oid,
            status='PENDING',
            starttime=starttime,
            endtime=endtime,
        )
        self.forecast = ForecastRepository.create(self.session, forecast)

    @task
    def _create_seismicityobservation(self) -> None:
        """
        Gets the seismicity observation data and stores it to the database.
        """

        if self.project.seismicityobservation_required == EInput.NOT_ALLOWED:
            self.forecast.seismicity_observation = None
            return None

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
    def _create_injectionobservation(self) -> None:
        """
        Gets the injection observation data and stores it to the database.
        """
        if self.project.injectionobservation_required == EInput.NOT_ALLOWED:
            self.forecast.injection_observation = None
        else:
            raise NotImplementedError

    @task
    def _read_injectionplans(self) -> None:
        """
        Reads the injection plans of the respective ForecastSeries
        from the database.
        """
        if self.project.injectionplan_required == EInput.NOT_ALLOWED:
            self.forecastseries.injection_plans = None
        else:
            raise NotImplementedError

    def _modelrun_info(self,
                       modelconfig: ModelConfig,
                       injectionplan: InjectionPlan) -> ModelRunInfo:
        """
        Assembles the information required to run the model from the
        various sources.

        The purpose is, that only raw input data still needs to be retreived
        by the model runner, while contextual data is provided directly.

        Args:
            modelconfig: The model configuration.
            injectionplan: The injection plan.

        Returns:
            ModelRunInfo: The information required to run the model.
        """
        return ModelRunInfo(
            forecast_oid=self.forecast.oid,
            forecast_start=self.forecast.starttime,
            forecast_end=self.forecast.endtime,

            injection_observation_oid=getattr(
                self.forecast.injection_observation, 'oid', None),
            seismicity_observation_oid=getattr(
                self.forecast.seismicity_observation, 'oid', None),

            bounding_polygon=self.forecastseries.bounding_polygon,
            depth_min=self.forecastseries.depth_min,
            depth_max=self.forecastseries.depth_max,

            injection_plan_oid=getattr(injectionplan, 'oid', None),
            config=modelconfig
        )

    @task(name='Build Model Runs')
    def build_runs(self) -> list[ModelRunInfo]:
        runs = []
        for modelconfig in self.modelconfigs:
            if self.forecastseries.injection_plans:
                for injection_plan in self.forecastseries.injection_plans:
                    runs.append(self._modelrun_info(
                        modelconfig, injection_plan))
            else:
                runs.append(self._modelrun_info(modelconfig, None))

        return runs

    @task
    def build_deployments(self) -> dict:
        """
        TODO: The idea is to build the input arguments for a
        `prefect.deployment.run_deployment`call.
        """


if __name__ == '__main__':
    forecast_flow_runner.serve()
