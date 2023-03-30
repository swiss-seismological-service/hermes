from prefect import flow, unmapped

from RAMSIS.tasks.utils import new_forecast_from_series, \
    set_statuses
from RAMSIS.tasks.forecast import \
    update_fdsn, update_hyd, forecast_serialize_data, \
    model_run_executor, poll_model_run, \
    update_running, run_forecast, model_runs


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

        poll_task = poll_model_run.map(unmapped(forecast_id), running_ids,
                                       unmapped(connection_string),
                                       wait_for=[running_ids])
        set_statuses(forecast_id,
                     connection_string, wait_for=[poll_task])


@flow(name="scheduled_ramsis_flow")
def scheduled_ramsis_flow(
        forecastseries_id, connection_string,
        date):
    forecast_id = new_forecast_from_series(
        forecastseries_id,
        connection_string, date)
    _ = ramsis_flow(forecast_id, connection_string, date)
