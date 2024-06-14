import time

from prefect import flow, get_run_logger, unmapped
from ramsis.datamodel import EStatus

from hermes.tasks.forecast import (check_model_run_not_complete,
                                   check_model_runs_running, forecast_status,
                                   model_run_executor, model_runs,
                                   poll_model_run, update_fdsn, update_hyd,
                                   update_running, waiting_task)
from hermes.tasks.utils import new_forecast_from_series, set_statuses


@flow(name="polling_flow")
def polling_flow(
        forecast_id, polling_ids, connection_string):
    logger = get_run_logger()
    logger.info(f"Polling ids: {polling_ids}")
    _ = poll_model_run.map(unmapped(forecast_id), polling_ids,
                           unmapped(connection_string))


@flow(name="ramsis_flow")
def ramsis_flow(forecast_id, connection_string, date):
    logger = get_run_logger()
    forecast_state = forecast_status(forecast_id, connection_string)
    if forecast_state == EStatus.COMPLETED:
        logger.info(f'Forecast {forecast_id} will not be run '
                    ' as it is complete')
    elif forecast_state == EStatus.RUNNING:
        logger.info(f'Forecast {forecast_id} is in RUNNING state, '
                    ' check if model runs can be polled.')

        polling_ids = model_runs(forecast_id, connection_string)

        exponential_factor = 1.2
        x = 1
        logger.info(f"just before check model runs sent off, {polling_ids}")
        while check_model_runs_running(forecast_id, connection_string,
                                       wait_for=[polling_ids]):
            logger.info("just after check model runs set to run, "
                        f"{connection_string}")

            _ = polling_flow(forecast_id, polling_ids, connection_string)
            time.sleep(x**exponential_factor)
            logger.info(f"Polling for forecast {forecast_id}, {x}")
            x += 1

    else:
        status_task = update_running(forecast_id, connection_string)
        fdsn_task = update_fdsn(forecast_id, date, connection_string,
                                wait_for=[status_task])
        hyd_task = update_hyd(forecast_id, date, connection_string,
                              wait_for=[status_task])

        model_run_ids = model_runs(forecast_id, connection_string,
                                   wait_for=[fdsn_task, hyd_task])

        running_ids = model_run_executor.map(unmapped(forecast_id),
                                             model_run_ids,
                                             unmapped(connection_string))
        polling_ids = check_model_run_not_complete.map(
            running_ids,
            connection_string,
            wait_for=[running_ids])

        exponential_factor = 1.2
        x = 1
        while check_model_runs_running(forecast_id, connection_string,
                                       wait_for=[polling_ids]):

            poll_flow = polling_flow(forecast_id, polling_ids,
                                     connection_string)
            t = x**exponential_factor
            waiting_task(forecast_id, t, connection_string, wait_for=poll_flow)
            x += 1
    set_statuses(forecast_id,
                 connection_string)


@flow(name="scheduled_ramsis_flow")
def scheduled_ramsis_flow(
        forecastseries_id, connection_string,
        date=None):
    try:
        forecast_id, date = new_forecast_from_series(
            forecastseries_id,
            connection_string, date)
        _ = ramsis_flow(forecast_id, connection_string, date)
    except TypeError:
        # If None is returned from new_forecast_from_series,
        # exit the flow. The information is already logged.
        pass
