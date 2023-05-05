from prefect import flow, unmapped
import time

from RAMSIS.tasks.utils import new_forecast_from_series, \
    set_statuses
from RAMSIS.tasks.forecast import \
    update_fdsn, update_hyd, forecast_serialize_data, \
    model_run_executor, poll_model_run, \
    update_running, run_forecast, model_runs, \
    check_model_run_not_complete, \
    check_model_runs_dispatched, \
    dispatched_model_runs


@flow(name="polling_flow")
def polling_flow(
    forecast_id, polling_ids, connection_string):
    poll_task = poll_model_run.map(unmapped(forecast_id), polling_ids,
                                         unmapped(connection_string))
    #dispatched_ids = check_model_run_not_complete.map(polling_ids, unmapped(connection_string), wait_for=[poll_task])


@flow(name="ramsis_flow")
def ramsis_flow(forecast_id, connection_string, date):
    if run_forecast(forecast_id, connection_string):
        status_task = update_running(forecast_id, connection_string)
        fdsn_task = update_fdsn(forecast_id, date, connection_string,
                                wait_for=[status_task])
        hyd_task = update_hyd(forecast_id, date, connection_string,
                              wait_for=[status_task])

        forecast_data = forecast_serialize_data(
            forecast_id, connection_string,
            wait_for=[fdsn_task, hyd_task])

        model_run_ids = model_runs(forecast_id, connection_string)

        running_ids = model_run_executor.map(unmapped(forecast_id),
                                             unmapped(forecast_data),
                                             model_run_ids,
                                             unmapped(connection_string))
        polling_ids = check_model_run_not_complete.map(running_ids,
                connection_string,
                wait_for=[running_ids])
        disp = check_model_runs_dispatched(forecast_id, connection_string, wait_for=[polling_ids])

        exponential_factor = 1.2
        x = 1
        while check_model_runs_dispatched(forecast_id, connection_string, wait_for=[polling_ids]):
            
            _ = polling_flow(forecast_id, polling_ids, connection_string)
            time.sleep(x**exponential_factor)
            x += 1
        set_statuses(forecast_id,
                     connection_string)



@flow(name="scheduled_ramsis_flow")
def scheduled_ramsis_flow(
        forecastseries_id, connection_string,
        date):
    forecast_id = new_forecast_from_series(
        forecastseries_id,
        connection_string, date)
    _ = ramsis_flow(forecast_id, connection_string, date)
