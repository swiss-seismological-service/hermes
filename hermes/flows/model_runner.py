from abc import abstractmethod

from hermes_model import ModelInput
from prefect import flow, task

from hermes.repositories.data import (InjectionObservationRepository,
                                      InjectionPlanRepository,
                                      SeismicityObservationRepository)
from hermes.repositories.database import Session
from hermes.schemas.model_schemas import DBModelRunInfo


class ModelRunHandlerInterface:
    """
    General Interface for a model run handler.
    """

    def __init__(self, modelrun_info: DBModelRunInfo, **kwargs) -> None:
        super().__init__(**kwargs)
        self.modelrun_info = modelrun_info
        self.model_config = modelrun_info.modelconfig
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

    def __init__(self, *args, **kwargs) -> None:
        self.session = Session()
        super().__init__(*args, **kwargs)

        self.model_input = self._model_input()

    @task(name='RunModel')
    def run(self) -> None:
        print(self.model_input)

    def _model_input(self) -> ModelInput:
        return ModelInput(
            forecast_start=self.modelrun_info.forecast_start,
            forecast_end=self.modelrun_info.forecast_end,

            injection_observation=self.injection_observation,
            injection_plan=self.injection_plan,
            seismicity_observation=self.seismicity_observation,

            bounding_polygon=self.modelrun_info.bounding_polygon,
            depth_min=self.modelrun_info.depth_min,
            depth_max=self.modelrun_info.depth_max,

            model_parameters=self.model_config.model_parameters
        )

    def __del__(self):
        print('Closing session')
        self.session.close()

    def _fetch_injection_observation(self) -> None:
        if not self.modelrun_info.injection_observation_oid:
            return None
        return InjectionObservationRepository.get_by_id(
            self.session, self.modelrun_info.injection_observation_oid).data

    def _fetch_injection_plan(self) -> None:
        if not self.modelrun_info.injection_plan_oid:
            return None
        return InjectionPlanRepository.get_by_id(
            self.session, self.modelrun_info.injection_plan_oid).data

    def _fetch_seismicity_observation(self) -> None:
        if not self.modelrun_info.seismicity_observation_oid:
            return None
        return SeismicityObservationRepository.get_by_id(
            self.session, self.modelrun_info.seismicity_observation_oid).data


@flow(name='DefaultModelRunner')
def default_model_flow_runner(modelrun_info: DBModelRunInfo) -> None:
    runner = DefaultModelRunHandler(modelrun_info)
    runner.run()
