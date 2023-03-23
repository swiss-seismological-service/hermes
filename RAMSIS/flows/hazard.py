from prefect import flow
from ramsis.datamodel import EStatus
from RAMSIS.tasks.hazard import prepare_hazard,  map_scenario_runs, \
    flatten_hazard_run_info_list, \
    execute_hazard_run
from RAMSIS.tasks.utils import update_status
from prefect import unmapped


@flow(name="hazard_stage")
def hazard_stage_flow(forecast_id, connection_string, data_dir):
    update_status(forecast_id, connection_string, EStatus.RUNNING)
    hazard_preparation_list = prepare_hazard(
        forecast_id, data_dir, connection_string)
    hazard_run_info_lists = map_scenario_runs.map(
        hazard_preparation_list)
    hazard_run_info_list = flatten_hazard_run_info_list.map(
        hazard_run_info_lists)
    _ = execute_hazard_run.map(
        unmapped(forecast_id),
        hazard_run_info_list,
        unmapped(connection_string))
