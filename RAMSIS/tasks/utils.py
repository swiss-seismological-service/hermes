from prefect import task, get_run_logger
from ramsis.datamodel import EStatus, ModelRun, EInput, Forecast, Status
from RAMSIS.db_utils import set_statuses_db, get_forecast, get_forecastseries
from RAMSIS.db import session_handler

forecast_context_format = "forecast_id: {forecast_id} |"
model_run_context_format = "forecast_id: {forecast_id} " \
    "model_run_id: {model_run_id}|"


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
                status=Status(state=EStatus.PENDING)))
    return model_runs


@task
def new_forecast_from_series(forecastseries_id: int,
                             connection_string: str,
                             start_time) -> int:

    logger = get_run_logger()
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
                raise Exception(
                    "Project requires injection plan but none were "
                    "given on the forecast series. Please modify the "
                    "forecast series before trying to run again.")
            else:
                model_run_list.extend(create_model_runs(model_configs_set))
        else:
            for injection_plan in injection_plans:
                model_run_list.extend(create_model_runs(
                    model_configs_set,
                    injection_plan=injection_plan))
        forecast = Forecast(forecastseries_id=forecastseries_id,
                            starttime=start_time,
                            endtime=forecastseries.endtime,
                            runs=model_run_list,
                            status=Status(state=EStatus.PENDING))

        logger.info("The new forecast will have a starttime of: "
                    f"{forecast.starttime} and an endtime of: "
                    f"{forecast.endtime}")

        session.add(forecast)
        session.commit()
        logger.info(f"The new forecast has an id: {forecast.id}")
        return forecast.id


@task(task_run_name="set_statuses(forecast{forecast_id})")
def set_statuses(forecast_id: int,
                 connection_string: str) -> None:
    logger = get_run_logger()
    with session_handler(connection_string) as session:
        forecast = get_forecast(forecast_id, session)
        model_runs = [r for r in forecast.runs if r.enabled]
        models_finished = all([
            True if model.status.state in
            [EStatus.COMPLETE, EStatus.FINISHED_WITH_ERRORS] else False
            for model in model_runs])
        if not models_finished:
            logger.error("The model runs have mixed statuses and appear to "
                         "be unfinished.")
            forecast.status.state = EStatus.FINISHED_WITH_ERRORS
            session.commit()
            raise Exception("The model runs have mixed statuses and appear to "
                            "be unfinished. ")

        models_complete = all([
            True if model.status.state == EStatus.COMPLETE else False
            for model in model_runs])
        if models_complete:
            forecast.status.state = EStatus.COMPLETE
            session.commit()
        else:
            forecast.status.state = EStatus.FINISHED_WITH_ERRORS
            session.commit()
            raise Exception("Forecast has errors")
