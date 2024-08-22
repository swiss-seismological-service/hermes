from datetime import datetime
from uuid import UUID

from prefect import flow, serve
from prefect.deployments import run_deployment

from hermes.flows.forecast_builder import ForecastBuilder
from hermes.flows.modelrun_handler import DefaultModelRunHandler
from hermes.schemas.model_schemas import DBModelRunInfo, ModelConfig


@flow(name='DefaultModelRunner')
def default_model_flow_runner(modelrun_info: DBModelRunInfo,
                              modelconfig: ModelConfig) -> None:
    runner = DefaultModelRunHandler(modelrun_info, modelconfig)
    runner.run()


@flow(name='LocalForecastRunner')
def forecast_flow_runner_local(forecastseries: UUID,
                               starttime: datetime | None = None,
                               endtime: datetime | None = None) -> None:
    builder = ForecastBuilder(forecastseries, starttime, endtime)
    runs = builder.build_runs()
    for run in runs:
        default_model_flow_runner(*run)
    return runs


@flow(name='ForecastRunner')
def forecast_flow_runner(forecastseries: UUID,
                         starttime: datetime | None = None,
                         endtime: datetime | None = None) -> None:
    builder = ForecastBuilder(forecastseries, starttime, endtime)
    runs = builder.build_runs()
    for run in runs:
        run_deployment(
            name='DefaultModelRunner/DefaultModelRunner',
            parameters={'modelrun_info': run[0],
                        'modelconfig': run[1]},
            timeout=0
        )
    return runs


if __name__ == '__main__':
    forecast_deployment = forecast_flow_runner.to_deployment(
        name='ForecastRunner')
    modelrun_deployment = default_model_flow_runner.to_deployment(
        name='DefaultModelRunner')
    serve(forecast_deployment, modelrun_deployment)
