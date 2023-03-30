
from prefect import flow
from RAMSIS.flows.seismicity import seismicity_stage_flow
from RAMSIS.flows.hazard import hazard_stage_flow
from RAMSIS.tasks.seismicity_forecast import \
    run_seismicity_flow
from RAMSIS.tasks.hazard import \
    run_hazard_flow
from RAMSIS.tasks.utils import clone_forecast, set_statuses, \
    update_status
from ramsis.datamodel import EStage, EStatus
from prefect import flow, unmapped
from RAMSIS.tasks.seismicity_forecast import \
    update_fdsn, update_hyd, forecast_scenarios, forecast_serialize_data, \
    scenario_serialize_data, model_run_executor, poll_model_run, \
    update_running, flatten_model_run_list

seismicity_flow_name = 'SeismiciyFlow'


@flow(name="ramsis_flow")
def ramsis_flow(forecast_id, connection_string, date):
    if run_forecast(forecast_id, connection_string):
        status_task = update_running(forecast_id, connection_string)
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
        model_run_ids = model_run_executor.map(unmapped(forecast_id),
                                               unmapped(forecast_data),
                                               model_run_data,
                                               unmapped(connection_string))

        _ = poll_model_run.map(unmapped(forecast_id), model_run_ids,
                                        unmapped(connection_string),
                                        wait_for=[model_run_ids])
        set_statuses(forecast_id,
                     connection_string, wait_for=[seismicity_stage])


@flow(name="scheduled_ramsis_flow")
def scheduled_ramsis_flow(
        forecastseries_id, connection_string,
        date):
    forecast_id = clone_forecast(forecastseries_id,
                                 connection_string, date)
    run_forecast = ramsis_flow
