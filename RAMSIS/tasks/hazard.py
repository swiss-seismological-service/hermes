
from RAMSIS.db_utils import stage_statuses, run_stage, set_statuses
from prefect import task, Task
import prefect
from RAMSIS.core.store import session_handler
from sqlalchemy import select
from typing import List
from ramsis_hazard.core.oq_run_utils import OQHazardModelRunExecutor
from ramsis_hazard.core.hazard_run_preparation import HazardRunInfo,\
    ScenarioHazardPreparation, prepare_hazard_for_forecast
from ramsis.datamodel import Forecast, EStage, EStatus


@task
def update_status_running(forecast_id, connection_string, checkpoint=False):
    with session_handler(connection_string) as session:
        set_statuses(forecast_id, EStatus.RUNNING, session)
        session.commit()


@task
def hazard_stage_controller(forecast_id: int,
                            connection_string: str):

    # logger = prefect.context.get('logger')
    with session_handler(connection_string) as session:
        forecast = session.execute(
            select(Forecast).filter_by(id=forecast_id)).scalar_one()
        if run_stage(forecast, EStage.HAZARD):
            seismicity_stage_statuses = stage_statuses(
                forecast_id, EStage.SEISMICITY, session)
            if any(status.state != EStatus.COMPLETE for status in
                    seismicity_stage_statuses):
                return True
        return False


class PrepareHazardForForecast(Task):
    def run(self, forecast_id: int, data_dir: str,
            connection_string: str) -> List[ScenarioHazardPreparation]:
        with session_handler(connection_string) as session:
            # Prepare hazard files and return nested information
            # about scenarios and hazard runs within that forecast
            hazard_preparation_list = prepare_hazard_for_forecast(
                forecast_id, data_dir, session)
            return hazard_preparation_list


class MapScenarioRuns(Task):
    def run(self, hazard_preparation: ScenarioHazardPreparation
            ) -> List[HazardRunInfo]:
        # Scenario_level
        # context_str = scenario_context_format.format(
        #     forecast_id=scenario.forecast.id,
        #     scenario_id=scenario.id)
        # with prefect.context(forecast_context=context_str):
        return hazard_preparation.hazard_run_info_list


class ExecuteHazardRun(Task):
    def run(self, hazard_preparation: HazardRunInfo,
            connection_string: str):
        with session_handler(connection_string) as session:
            logger = prefect.context.get('logger')
            executor = OQHazardModelRunExecutor(
                hazard_preparation.hazard_model_run_id,
                session)
            executor.run()
            forecast_id = prefect.context.get('forecast_id')
            # TODO set the hazard model run status and leave the forecast to
            # another task. handle errors!
            set_statuses(forecast_id, EStatus.COMPLETE, session)
            session.commit()
            logger.info("finished setting the statuses!")
