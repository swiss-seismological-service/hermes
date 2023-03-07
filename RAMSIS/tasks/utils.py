from prefect import task, get_run_logger
from RAMSIS.db_utils import set_statuses, get_forecast
from RAMSIS.utils import reset_forecast
from RAMSIS.db import session_handler

forecast_context_format = "forecast_id: {forecast_id} |"
scenario_context_format = "forecast_id: {forecast_id} scenario_id: " \
    "{scenario_id}|"
model_run_context_format = "forecast_id: {forecast_id} scenario_id: " \
    "{scenario_id} model_run_id: {model_run_id}|"


@task
def update_status(forecast_id, connection_string, estatus, checkpoint=False):
    with session_handler(connection_string) as session:
        set_statuses(forecast_id, estatus, session)
        session.commit()


@task
def clone_forecast(reference_forecast_id: int,
                   connection_string: str,
                   scheduled_start_time) -> int:

    logger = get_run_logger()
    with session_handler(connection_string) as session:
        reference_forecast = get_forecast(
            reference_forecast_id, session)
        project_settings = reference_forecast.project.settings.config
        # If some input data is attached to the forecast rather
        # than being received from a webservice, this must also
        # be cloned. with_results=True only copies input data over.
        if not project_settings['hydws_url'] or \
                not project_settings['fdsnws_url']:
            with_results = True
        else:
            with_results = False
        forecast = reference_forecast.clone(with_results=with_results)
        reference_forecast_duration = reference_forecast.endtime - \
            reference_forecast.starttime
        logger.info("The duration of the reference forecast is: "
                    f"{reference_forecast_duration}")

        logger.info("The new forecast will have a starttime of: "
                    f"{scheduled_start_time}")
        forecast.starttime = scheduled_start_time
        forecast.endtime = scheduled_start_time + \
            reference_forecast_duration
        logger.info("The new forecast will have an endtime of: "
                    f"{forecast.endtime}")

        forecast.project_id = reference_forecast.project_id
        # Reset statuses
        forecast = reset_forecast(forecast)
        session.add(forecast)
        session.commit()
        logger.info(f"The new forecast has an id: {forecast.id}")
        return forecast.id
