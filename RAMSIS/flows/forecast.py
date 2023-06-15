from prefect import flow, unmapped, get_run_logger
import time
from ramsis.datamodel import EStatus

from RAMSIS.tasks.utils import new_forecast_from_series, \
    set_statuses
from RAMSIS.tasks.forecast import \
    update_fdsn, update_hyd, forecast_serialize_data, \
    model_run_executor, poll_model_run, \
    update_running, model_runs, \
    check_model_run_not_complete, \
    check_model_runs_dispatched, \
    forecast_status


@flow(name="polling_flow")
def polling_flow(
        forecast_id, polling_ids, connection_string):
    logger = get_run_logger()
    logger.info(f"Polling ids: {polling_ids}")
    _ = poll_model_run.map(unmapped(forecast_id), polling_ids,
                           unmapped(connection_string))
    logger.debug("After poll_task.")


@flow(name="ramsis_flow")
def ramsis_flow(forecast_id, connection_string, date):
    logger = get_run_logger()
    forecast_state = forecast_status(forecast_id, connection_string)
    if forecast_state == EStatus.COMPLETE:
        logger.info(f'Forecast {forecast_id} will not be run '
                    ' as it is complete')
    elif forecast_state == EStatus.RUNNING:
        logger.info(f'Forecast {forecast_id} is in RUNNING state, '
                    ' check if model runs can be polled.')

        polling_ids = model_runs(forecast_id, connection_string)

        exponential_factor = 1.2
        x = 1
        while check_model_runs_dispatched(forecast_id, connection_string,
                                          wait_for=[polling_ids]):

            _ = polling_flow(forecast_id, polling_ids, connection_string)
            time.sleep(x**exponential_factor)
            print(f"Polling for forecast {forecast_id}, {x}")
            x += 1

    else:
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
        polling_ids = check_model_run_not_complete.map(
            running_ids,
            connection_string,
            wait_for=[running_ids])
        _ = check_model_runs_dispatched(forecast_id, connection_string,
                                        wait_for=[polling_ids])

        exponential_factor = 1.2
        x = 1
        while check_model_runs_dispatched(forecast_id, connection_string,
                                          wait_for=[polling_ids]):

            _ = polling_flow(forecast_id, polling_ids, connection_string)
            t = x**exponential_factor
            logger.info(f"sleeping for {t} seconds...")
            time.sleep(x**exponential_factor)
            logger.info(f"Polling for forecast {forecast_id}, {x}")
            x += 1
    set_statuses(forecast_id,
                 connection_string)


@flow(name="scheduled_ramsis_flow")
def scheduled_ramsis_flow(
        forecastseries_id, connection_string,
        date=None):
    forecast_id, date = new_forecast_from_series(
        forecastseries_id,
        connection_string, date)
    _ = ramsis_flow(forecast_id, connection_string, date)
