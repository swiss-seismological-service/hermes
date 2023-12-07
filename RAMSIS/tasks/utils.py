from prefect import task, get_run_logger, runtime
import json
from sqlalchemy.orm.session import Session
from datetime import timedelta, datetime
from ramsis.datamodel import EStatus, ModelRun, EInput, Forecast, \
    ForecastSeries
from typing import Union
from RAMSIS.db_utils import set_statuses_db, get_forecast, get_forecastseries
from RAMSIS.db import session_handler

forecast_context_format = "forecast_id: {forecast_id} |"
model_run_context_format = "forecast_id: {forecast_id} " \
    "model_run_id: {model_run_id}|"


def fork_log(obj: Union[ModelRun, Forecast, ForecastSeries],
             estatus: EStatus,
             msg: str, session: Session, logger, propagate=True):
    """
    Some important logs are stored in the database,
    these messages are logged traditionally and appended
    to a list of logs on the object (datetime added in db).
    """
    # Choose log level
    if estatus == EStatus.FAILED:
        logger.error(msg)
    else:
        logger.info(msg)
    obj.add_log(msg)
    obj.status = estatus
    # Add model run logs to the forecast also,
    # so we can see how many have completed and failed.
    # Option to propagate the log to forecast level also.
    if isinstance(obj, ModelRun) and propagate is True:
        forecast_msg = f"Model run {obj.id}: {msg}"
        obj.forecast.add_log(forecast_msg)
    print(f"new status of {obj}: {estatus}")
    session.commit()


@task
def update_status(forecast_id, connection_string, estatus):
    with session_handler(connection_string) as session:
        set_statuses_db(forecast_id, estatus, session)
        session.commit()


def create_model_runs(model_configs, injection_plan=None):
    model_runs = list()
    for config in model_configs:
        model_runs.append(
            ModelRun(
                modelconfig=config,
                injectionplan=injection_plan,
                status=EStatus.PENDING))
    return model_runs


@task
def new_forecast_from_series(forecastseries_id: int,
                             connection_string: str,
                             start_time: str) -> int:

    logger = get_run_logger()
    if not start_time:
        start_time = runtime.flow_run.scheduled_start_time
    elif type(start_time) == str: # noqa
        start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')
    with session_handler(connection_string) as session:
        forecastseries = get_forecastseries(
            forecastseries_id, session)

        # Get unique model configs to create model runs for.
        model_configs = list()
        for tag in forecastseries.tags:
            model_configs.extend(tag.modelconfigs)
        model_configs_set = set(model_configs)
        injection_plans = forecastseries.injectionplans

        model_run_list = list()
        if not injection_plans:
            if forecastseries.project.injectionplan_required == \
                    EInput.REQUIRED:
                msg = (
                    "Project requires injection plan but none were "
                    "given on the forecast series. Please modify the "
                    "forecast series before trying to run again.")
                fork_log(forecastseries, EStatus.FAILED, msg, session, logger)
                return
            else:
                model_run_list.extend(create_model_runs(model_configs_set))
        else:
            injection_plans = json.loads(injection_plans.decode('utf-8'))
            for injection_plan in injection_plans:
                model_run_list.extend(create_model_runs(
                    model_configs_set,
                    injection_plan=json.dumps(
                        injection_plan, ensure_ascii=False).encode('utf-8')))
        # Set forecast endtime
        if forecastseries.forecastduration:
            endtime = start_time + timedelta(
                seconds=forecastseries.forecastduration)
        elif forecastseries.endtime:
            endtime = forecastseries.endtime
        else:
            msg = (
                "forecast series endtime or forecastduration "
                "not set. Please update the forecastseries configuration.")
            fork_log(forecastseries, EStatus.FAILED, msg, session, logger)
            return
        forecast = Forecast(forecastseries_id=forecastseries_id,
                            starttime=start_time,
                            endtime=endtime,
                            runs=model_run_list,
                            status=EStatus.PENDING)

        session.add(forecast)
        session.commit()

        msg = (f"The new forecast {forecast.id} will have a starttime of: "
               f"{forecast.starttime} and an endtime of: "
               f"{forecast.endtime} and {len(model_run_list)} model runs.")
        fork_log(forecast, EStatus.PENDING, msg, session, logger)

        for run in forecast.runs:
            run.add_log(f"Model run {run.id} created.")
        session.commit()

        return forecast.id, start_time


@task(task_run_name="set_statuses(forecast{forecast_id})")
def set_statuses(forecast_id: int,
                 connection_string: str) -> None:
    logger = get_run_logger()
    with session_handler(connection_string) as session:
        forecast = get_forecast(forecast_id, session)
        forecastseries = forecast.forecastseries
        model_statuses = [model.status for model in forecast.runs]
        model_status_names = [status.name for status in model_statuses]
        models_finished = all([
            True if status in
            [EStatus.COMPLETED, EStatus.FAILED] else False
            for status in model_statuses])
        if not models_finished:
            msg = ("The model runs have mixed statuses and appear to "
                   f"be unfinished. {model_status_names}")
            fork_log(forecast, EStatus.FAILED, msg, session, logger)

        models_complete = all([
            True if model.status == EStatus.COMPLETED else False
            for model in forecast.runs])
        if models_complete:
            msg = "The model runs are all completed "
            fork_log(forecast, EStatus.COMPLETED, msg, session, logger)
            if forecastseries.endtime:
                if forecast.starttime >= forecastseries.endtime:
                    forecastseries.active = False
                    fork_log(forecast.forecastseries, EStatus.COMPLETED,
                             "All forecasts are complete", session, logger)
        else:
            msg = f"Some model runs have failed. {model_status_names}"
            fork_log(forecast, EStatus.FAILED, msg, session, logger)

        # Set status for forecastseries.
        if forecastseries.forecastinterval:
            # If there is no endtime then the forecast series will never
            # become inactive unless the user inactivates it manually.
            if forecastseries.endtime:
                # Earliest possible starttime for the last forecast.
                last_dttime = (
                    forecastseries.endtime - timedelta(
                        seconds=forecastseries.forecastinterval))
                if forecast.starttime > last_dttime:
                    forecastseries.active = False
                    fork_log(forecast.forecastseries, EStatus.COMPLETED,
                             "No more forecasts are scheduled", session,
                             logger)
        else:
            # If there is no forecastinterval set, only a single forecast
            # is run
            forecastseries.active = False
            fork_log(forecast.forecastseries, EStatus.COMPLETED,
                     "No more forecasts are scheduled", session, logger)
