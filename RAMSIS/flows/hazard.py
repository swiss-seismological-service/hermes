from RAMSIS.tasks.hazard import hazard_stage_controller, \
    PrepareHazardForForecast, \
    MapScenarioRuns, ExecuteHazardRun
from RAMSIS.tasks.utils import update_status_running
from prefect import Flow, Parameter, case, unmapped, flatten

@flow(name="hazard_stage")
def hazard_flow_factory(forecast_id, connection_string, data_dir):
    if hazard_stage_controller(forecast_id, connection_string):
        update_status_running(forecast_id, connection_string)
        prepare_hazard = prepare_hazard_for_forecast(
            forecast_id, unmapped(data_dir),
            unmapped(connection_string))
        map_scenario_runs = MapScenarioRuns(log_stdout=True)
        hazard_run_info_list = map_scenario_runs.map(
            hazard_preparation_list)
        execute_hazard_run = ExecuteHazardRun(log_stdout=True)
        _ = execute_hazard_run.map(
            flatten(hazard_run_info_list),
            unmapped(connection_string))
    return hazard_flow


hazard_flow_name = "HazardForecast"
hazard_flow = hazard_flow_factory(hazard_flow_name)
