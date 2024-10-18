from prefect import flow

from hermes.flows.modelrun_handler import DefaultModelRunHandler
from hermes.schemas import (DBModelRunInfo, Forecast, ForecastSeries,
                            InjectionPlan, ModelConfig)


class ModelRunBuilder:
    def __init__(self,
                 forecast: Forecast,
                 forecastseries: ForecastSeries,
                 modelconfigs: list[ModelConfig]):

        self.forecast = forecast
        self.forecastseries = forecastseries
        self.modelconfigs = modelconfigs

        self.runs = self.build_runs()

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


@flow(name='DefaultModelRunner')
def default_model_runner(modelrun_info: DBModelRunInfo,
                         modelconfig: ModelConfig) -> None:
    runner = DefaultModelRunHandler(modelrun_info, modelconfig)
    runner.run()
