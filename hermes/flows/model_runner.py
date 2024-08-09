from prefect import flow

from hermes.repositories.types import SessionType
from hermes.schemas.model_schemas import ModelRunInfo
from hermes.schemas.project_schemas import Forecast


class ModelRunner:
    def __init__(self,
                 session: SessionType,
                 modelrun_info: ModelRunInfo,
                 forecast: Forecast) -> None:
        self.session = session
        self.model_input = modelrun_info.input
        self.model_config = modelrun_info.config
        self.forecast = forecast

    @flow(name='RunModel')
    def run(self) -> None:
        # print(self.model_input)
        print(self.model_config)
