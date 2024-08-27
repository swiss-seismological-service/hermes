from datetime import datetime, timedelta
from uuid import UUID

from prefect import get_run_logger, runtime, task

from hermes.flows.catalog_readers import get_catalog
from hermes.repositories.data import SeismicityObservationRepository
from hermes.repositories.database import Session
from hermes.repositories.project import (ForecastRepository,
                                         ForecastSeriesRepository,
                                         ProjectRepository)
from hermes.schemas import (DBModelRunInfo, EInput, EStatus, Forecast,
                            InjectionPlan, ModelConfig, SeismicityObservation)
from hermes.utils.prefect import futures_wait


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

        if self.forecastseries.seismicityobservation_required == \
                EInput.NOT_ALLOWED:
            self.forecast.seismicity_observation = None
            return None

        seismicity = SeismicityObservation(
            forecast_oid=self.forecast.oid,
            data=get_catalog(self.forecastseries.fdsnws_url,
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

    def _modelrun_info(self,
                       injectionplan: InjectionPlan | None = None) \
            -> DBModelRunInfo:
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
        return DBModelRunInfo(
            forecastseries_oid=self.forecastseries.oid,
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

            injection_plan_oid=getattr(injectionplan, 'oid', None)
        )

    @task(name='Build Model Runs')
    def build_runs(self) -> list[tuple[DBModelRunInfo, ModelConfig]]:
        runs = []
        for modelconfig in self.modelconfigs:
            if self.forecastseries.injection_plans:
                for injection_plan in self.forecastseries.injection_plans:
                    runs.append(
                        (self._modelrun_info(injection_plan), modelconfig))
            else:
                runs.append((self._modelrun_info(), modelconfig))

        return runs

    @task
    def build_deployments(self) -> dict:
        """
        TODO: The idea is to build the input arguments for a
        `prefect.deployment.run_deployment`call.
        """
