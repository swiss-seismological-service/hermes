
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




@task(task_run_name="hazard_stage_controller(forecast{forecast_id})")
def hazard_stage_controller(forecast_id: int,
                            connection_string: str) -> bool:

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

@task(task_run_name="prepare_forecast_for_hazard(forecast{forecast_id})")
def prepare_hazard_for_forecast(
        forecast_id: int, data_dir: str,
        connection_string: str) -> List[ScenarioHazardPreparation]:
    with session_handler(connection_string) as session:
        # Prepare hazard files and return nested information
        # about scenarios and hazard runs within that forecast
        hazard_preparation_list = prepare_hazard_for_forecast(
            forecast_id, data_dir, session)
        return hazard_preparation_list


@task
def map_scenario_runs(hazard_preparation: ScenarioHazardPreparation
            ) -> List[HazardRunInfo]:
        return hazard_preparation.hazard_run_info_list


@task(task_run_name="execute_hazard_run(forecast{forecast_id})")
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
