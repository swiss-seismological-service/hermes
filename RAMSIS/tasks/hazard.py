from prefect import task, get_run_logger

from RAMSIS.db_utils import get_forecast, get_hazard_model_run
from RAMSIS.db import session_handler
from typing import List
from ramsis_hazard.core.oq_run_utils import OQHazardModelRunExecutor
from ramsis_hazard.core.hazard_run_preparation import HazardRunInfo,\
    ScenarioHazardPreparation, prepare_hazard_for_forecast
from ramsis.datamodel import EStage, EStatus


#@task(task_run_name="hazard_stage_controller(forecast{forecast_id})")
#def hazard_stage_controller(forecast_id: int,
#                            connection_string: str) -> bool:
#
#    with session_handler(connection_string) as session:
#        forecast = session.execute(
#            select(Forecast).filter_by(id=forecast_id)).scalar_one()
#        if run_stage(forecast, EStage.HAZARD):
#            seismicity_stage_statuses = stage_statuses(
#                forecast_id, EStage.SEISMICITY, session)
#            if any(status.state != EStatus.COMPLETE for status in
#                    seismicity_stage_statuses):
#                return True
#        return False
#

@task(task_run_name="run_hazard_flow(forecast{forecast_id})")
def run_hazard_flow(forecast_id: int, connection_string: str) -> bool:
    """
    If any of the scenarios have a hazard stage that is not complete,
    where the forecast or scenario does not have the status of
    ERROR, return True.
    """
    with session_handler(connection_string) as session:
        logger = get_run_logger()
        forecast = get_forecast(forecast_id, session)
        if forecast.status.state == EStatus.ERROR:
            logger.warning(
                "The Hazard stage will not run for this "
                "forecast because the forecast has a status of error")
            return False
        for scenario in forecast.scenarios:
            if not scenario.enabled:
                continue
            if scenario.status.state == EStatus.ERROR:
                logger.warning(
                    "The Hazard stage will not run for this "
                    "forecast because the scenario has a status of error")
                return False
            seismicity_stage = scenario[EStage.SEISMICITY]

            try:
                hazard_stage = scenario[EStage.HAZARD]
            except KeyError:
                continue
            if not hazard_stage.enabled:
                continue
            elif hazard_stage.status.state != EStatus.COMPLETE:
                logger.info("Hazard Stage will be run.")
                if seismicity_stage.status.state != EStatus.COMPLETE:
                    logger.warning(
                        "There are uncompleted seismicity stages")
                    continue
                return True
        logger.info('Hazard stage has been skipped'
                    f' for forecast_id: {forecast_id}'
                    ' as no tasks are required to be done.')
        return False

@task(task_run_name="prepare_forecast_for_hazard(forecast{forecast_id})")
def prepare_hazard(
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

@task
def flatten_hazard_run_info_list(hazard_run_info_lists: List) -> List[HazardRunInfo]:
    ret_list = []
    for info_list in hazard_run_info_lists:
        for item in info_list:
            ret_list.append(item)
    return ret_list


@task(task_run_name="execute_hazard_run(forecast{forecast_id})")
def execute_hazard_run(
        forecast_id,
        hazard_preparation: HazardRunInfo,
        connection_string: str):
    with session_handler(connection_string) as session:
        logger = get_run_logger()
        try:
            executor = OQHazardModelRunExecutor(
                hazard_preparation.hazard_model_run_id,
                session)
            executor.run()
        except Exception as err:
            logger.error(err)
            run_id = hazard_preparation.hazard_model_run_id
            model_run = get_hazard_model_run(run_id, session)
            model_run.status.state = EStatus.ERROR
            session.commit()
            raise
        # TODO set the hazard model run status and leave the forecast to
        # another task. handle errors!

        session.commit()
        logger.info("finished setting the statuses!")
