import importlib
from abc import abstractmethod
from typing import Any

from hermes_model import ModelInput
from prefect import flow, task
from seismostats import ForecastCatalog, ForecastGRRateGrid

from hermes.io.model_results import save_forecast_catalog_to_repositories
from hermes.repositories.data import (InjectionObservationRepository,
                                      InjectionPlanRepository,
                                      SeismicityObservationRepository)
from hermes.repositories.database import Session
from hermes.schemas.base import EResultType
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
        self.save_results = {EResultType.CATALOG: self._save_catalog,
                             EResultType.BINS: self._save_bins,
                             EResultType.GRID: self._save_grid, }

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

    @abstractmethod
    def _save_catalog(self, results: list[ForecastCatalog]) -> None:
        raise NotImplementedError

    @abstractmethod
    def _save_bins(self, results: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def _save_grid(self, results: list[ForecastGRRateGrid]) -> None:
        raise NotImplementedError


class DefaultModelRunHandler(ModelRunHandlerInterface):

    def __init__(self, *args, **kwargs) -> None:
        self.session = Session()
        super().__init__(*args, **kwargs)

        self.model_input = self._model_input()
        self.model_config = self.modelrun_info.modelconfig

    @task(name='RunModel')
    def run(self) -> None:
        model_module = importlib.import_module(self.model_config.sfm_module)
        model_function = getattr(model_module, self.model_config.sfm_function)

        results = model_function(self.model_input.model_dump())
        self.save_results[self.model_config.result_type](results)

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

    def _save_catalog(self, results: list[ForecastCatalog]) -> None:
        for catalog in results:
            save_forecast_catalog_to_repositories(self.session, catalog)

    def _save_bins(self, results: Any) -> None:
        raise NotImplementedError

    def _save_grid(self, results: list[ForecastGRRateGrid]) -> None:
        raise NotImplementedError


@flow(name='DefaultModelRunner')
def default_model_flow_runner(modelrun_info: DBModelRunInfo) -> None:
    runner = DefaultModelRunHandler(modelrun_info)
    runner.run()
