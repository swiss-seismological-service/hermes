from prefect import Task
import prefect
from sqlalchemy import select
from typing import List
from ramsis_hazard.core.oq_run_utils import OQHazardModelRunExecutor
from ramsis_hazard.core.hazard_run_preparation import HazardRunInfo,\
    ScenarioHazardPreparation, prepare_hazard_for_forecast
from ramsis.datamodel import Forecast, EStage, EStatus

from RAMSIS.db import session_handler


def set_statuses(forecast_id: int, status: EStatus, connection_string: str):
    with session_handler(connection_string) as session:
        forecast = session.execute(
            select(Forecast).filter_by(id=forecast_id)).scalar_one()
        forecast.status.state = status
        for scenario in forecast.scenarios:
            stage = scenario[EStage.HAZARD]
            stage.status.state = status
            scenario.status.state = status
        session.commit()


class PrepareHazardForForecast(Task):
    def run(self, forecast_id: int, data_dir: str, connection_string: str) -> \
            List[ScenarioHazardPreparation]:
        with session_handler(connection_string) as session:
            # Prepare hazard files and return nested information
            # about scenarios and hazard runs within that forecast
            hazard_preparation_list = prepare_hazard_for_forecast(
                forecast_id, data_dir, session)
            return hazard_preparation_list


class MapScenarioRuns(Task):
    def run(self, hazard_preparation: ScenarioHazardPreparation,
            connection_string: str) -> List[HazardRunInfo]:
        # Scenario_level
        # context_str = scenario_context_format.format(
        #     forecast_id=scenario.forecast.id,
        #     scenario_id=scenario.id)
        # with prefect.context(forecast_context=context_str):
        return hazard_preparation.hazard_run_info_list


class ExecuteHazardRun(Task):
    def run(self, hazard_preparation: HazardRunInfo, connection_string: str):
        with session_handler(connection_string) as session:
            logger = prefect.context.get('logger')
            executor = OQHazardModelRunExecutor(
                hazard_preparation.hazard_model_run_id,
                session)
            executor.run()
            forecast_id = prefect.context.get('forecast_id')
            # TODO set the hazard model run status and leave the forecast
            # to another task. handle errors!
            set_statuses(forecast_id, EStatus.COMPLETE)
            logger.info("finished setting the statuses!")
