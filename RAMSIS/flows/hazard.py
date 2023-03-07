#from RAMSIS.tasks.hazard import hazard_stage_controller, \
#    PrepareHazardForForecast, \
#    MapScenarioRuns, ExecuteHazardRun, update_status_running
#from prefect import Flow, Parameter, case, unmapped, flatten
#
#
#def hazard_flow_factory(flow_name):
#    with Flow(flow_name
#              ) as hazard_flow:
#        forecast_id = Parameter('forecast_id')
#        data_dir = Parameter('data_dir')
#        connection_string = Parameter('connection_string')
#        with case(hazard_stage_controller(forecast_id, connection_string),
#                  True):
#            update_status_running(forecast_id, connection_string)
#            prepare_hazard = PrepareHazardForForecast(log_stdout=True)
#            hazard_preparation_list = prepare_hazard(
#                forecast_id, unmapped(data_dir),
#                unmapped(connection_string))
#            map_scenario_runs = MapScenarioRuns(log_stdout=True)
#            hazard_run_info_list = map_scenario_runs.map(
#                hazard_preparation_list)
#            execute_hazard_run = ExecuteHazardRun(log_stdout=True)
#            _ = execute_hazard_run.map(
#                flatten(hazard_run_info_list),
#                unmapped(connection_string))
#    return hazard_flow
#
#
#hazard_flow_name = "HazardForecast"
#hazard_flow = hazard_flow_factory(hazard_flow_name)
