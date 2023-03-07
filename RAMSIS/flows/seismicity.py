from prefect import flow
from ramsis.datamodel import EStage
from RAMSIS.tasks.seismicity_forecast import \
    update_fdsn, update_hyd, forecast_scenarios, forecast_serialize_data, \
    scenario_serialize_data, model_runs, model_run_executor, poll_model_run, \
    run_seismicity_flow, update_running, set_statuses

seismicity_flow_name = 'SeismiciyFlow'




@flow(name="seismicity_stage_{forecast_id}-on-{date}")
def seismicity_stage_flow(forecast_id, connection_string, date):

    status_task = update_running(forecast_id, connection_string)
    # Data should be got/refreshed only if there are no model
    # runs with a EStatus.COMPLETE state. In this case, existing
    # data will be used and only model runs that are not complete
    # will be recalculated.
    fdsn_task = update_fdsn(forecast_id, date, connection_string)
    hyd_task = update_hyd(forecast_id, date, connection_string)

    scenario_ids = forecast_scenarios(
        forecast_id, connection_string,
        wait_for=[status_task, fdsn_task, hyd_task])
    forecast_data = forecast_serialize_data(
        forecast_id, connection_string,
        wait_for=[status_task, fdsn_task, hyd_task])
    for scenario_id in scenario_ids:
        scenario_data = scenario_serialize_data(
            forecast_id, connection_string,
            wait_for=[status_task, fdsn_task, hyd_task])
        model_run_ids = model_runs(scenario_id, connection_string)
        for model_run_id in model_run_ids:
            model_post = model_run_executor(forecast_id, forecast_data,
                                            scenario_data, model_run_id,
                                            connection_string)

            poll_task = poll_model_run(forecast_id, model_run_id,
                                       connection_string,
                                       wait_for=[model_post])

            set_statuses(forecast_id, EStage.SEISMICITY,
                         connection_string, wait_for=[poll_task])
    set_statuses(forecast_id, EStage.SEISMICITY,
                 connection_string)

# creates a flow run called 'marvin-on-Thursday'
# seismicity_stage_flow(name="marvin", date=datetime.datetime.utcnow())
