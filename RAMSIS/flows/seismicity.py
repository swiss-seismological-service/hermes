from prefect import flow, unmapped
from ramsis.datamodel import EStage
from RAMSIS.tasks.seismicity_forecast import \
    update_fdsn, update_hyd, forecast_scenarios, forecast_serialize_data, \
    scenario_serialize_data, model_runs, model_run_executor, poll_model_run, \
    run_seismicity_flow, update_running, set_statuses, flatten_model_run_list

seismicity_flow_name = 'SeismiciyFlow'




@flow(name="seismicity_stage")
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

    model_runs_data = scenario_serialize_data.map(
        scenario_ids, unmapped(connection_string),
        wait_for=[status_task, fdsn_task, hyd_task])
    model_run_data = flatten_model_run_list(model_runs_data)
    model_run_ids = model_run_executor.map(unmapped(forecast_id), unmapped(forecast_data),
                                        model_run_data,
                                        unmapped(connection_string))

    poll_task = poll_model_run.map(unmapped(forecast_id), model_run_ids,
                                   unmapped(connection_string),
                               wait_for=[model_run_ids])


# creates a flow run called 'marvin-on-Thursday'
# seismicity_stage_flow(name="marvin", date=datetime.datetime.utcnow())
