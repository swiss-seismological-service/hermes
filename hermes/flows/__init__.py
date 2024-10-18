from datetime import datetime
from typing import Literal
from uuid import UUID

from prefect import flow

from hermes.flows.forecast_handler import ForecastHandler
from hermes.flows.modelrun_handler import DefaultModelRunHandler
from hermes.schemas.model_schemas import DBModelRunInfo, ModelConfig


@flow(name='DefaultModelRunner')
def default_model_runner(modelrun_info: DBModelRunInfo,
                         modelconfig: ModelConfig) -> None:
    runner = DefaultModelRunHandler(modelrun_info, modelconfig)
    runner.run()


@flow(name='ForecastRunner')
def forecast_runner(forecastseries_oid: UUID,
                    starttime: datetime | None = None,
                    endtime: datetime | None = None,
                    mode: Literal['local', 'deploy'] = 'local') -> None:
    forecasthandler = ForecastHandler(forecastseries_oid, starttime, endtime)
    forecasthandler.run(mode)
