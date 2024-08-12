from abc import abstractmethod

from prefect import flow, task

from hermes.repositories.database import Session
from hermes.schemas.model_schemas import ModelRunInfo


class ModelRunHandlerInterface:
    def __init__(self, modelrun_info: ModelRunInfo) -> None:
        self.modelrun_info = modelrun_info
        self.model_config = modelrun_info.config
        self.injection_plan = self._fetch_injection_plan()
        self.injection_observation = self._fetch_injection_observation()
        self.seismicity_observation = self._fetch_seismicity_observation()

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def _fetch_injection_observation(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def _fetch_injection_plan(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def _fetch_seismicity_observation(self) -> None:
        raise NotImplementedError


class DefaultModelRunHandler(ModelRunHandlerInterface):

    def __init__(self, modelrun_info: ModelRunInfo) -> None:
        super().__init__(modelrun_info)
        self.session = Session()

    def __del__(self):
        print('Closing session')
        self.session.close()

    def _fetch_injection_observation(self) -> None:
        pass

    def _fetch_injection_plan(self) -> None:
        pass

    def _fetch_seismicity_observation(self) -> None:
        pass

    @task(name='RunModel')
    def run(self) -> None:
        print(self.modelrun_info)


@flow(name='DefaultModelRunner')
def model_flow_runner(modelrun_info: ModelRunInfo) -> None:
    runner = DefaultModelRunHandler(modelrun_info)
    runner.run()
