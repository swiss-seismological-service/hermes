from datetime import datetime
from uuid import UUID

from prefect import flow

from hermes.flows.forecast_builder import ForecastBuilder
from hermes.flows.modelrun_handler import DefaultModelRunHandler
from hermes.schemas.model_schemas import DBModelRunInfo, ModelConfig


@flow(name='DefaultModelRunner')
def default_model_flow_runner(modelrun_info: DBModelRunInfo,
                              modelconfig: ModelConfig) -> None:
    runner = DefaultModelRunHandler(modelrun_info, modelconfig)
    runner.run()


@flow(name='ForecastRunner')
def forecast_flow_runner(forecastseries: UUID,
                         starttime: datetime | None = None,
                         endtime: datetime | None = None) -> None:
    builder = ForecastBuilder(forecastseries, starttime, endtime)
    runs = builder.build_runs()
    for run in runs:
        default_model_flow_runner(*run)
    return runs


if __name__ == '__main__':
    forecast_flow_runner.serve()
