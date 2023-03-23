from prefect import task, get_run_logger
from ramsis.datamodel import EStage, EStatus
from RAMSIS.db_utils import set_statuses_db, get_forecast
from RAMSIS.utils import reset_forecast
from RAMSIS.db import session_handler

forecast_context_format = "forecast_id: {forecast_id} |"
scenario_context_format = "forecast_id: {forecast_id} scenario_id: " \
    "{scenario_id}|"
model_run_context_format = "forecast_id: {forecast_id} scenario_id: " \
    "{scenario_id} model_run_id: {model_run_id}|"


@task
def update_status(forecast_id, connection_string, estatus):
    with session_handler(connection_string) as session:
        set_statuses_db(forecast_id, estatus, session)
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


@task(task_run_name="set_statuses(forecast{forecast_id})")
def set_statuses(forecast_id: int, estage: EStage,
                 connection_string: str) -> None:
    # Set statuses at end of the stage
    logger = get_run_logger()
    with session_handler(connection_string) as session:
        forecast = get_forecast(forecast_id, session)
        for scenario in forecast.scenarios:
            if not scenario.enabled:
                pass
            try:
                stage = scenario[estage]
            except KeyError:
                continue
            if not stage.enabled:
                pass
            model_success = all([
                True if model.status.state == EStatus.COMPLETE else False
                for model in [r for r in stage.runs if r.enabled]])
            if model_success:
                stage.status.state = EStatus.COMPLETE
            else:
                stage.status.state = EStatus.ERROR
            # All stages are considered here.
            stage_states = [stage.status.state for stage in
                            [s for s in scenario.stages if s.enabled]]
            if all([state == EStatus.COMPLETE
                    for state in stage_states]):
                scenario.status.state = EStatus.COMPLETE
            elif any([state == EStatus.ERROR
                      for state in stage_states]):
                scenario.status.state = EStatus.ERROR
            elif any([state == EStatus.PENDING
                     for state in stage_states]):
                scenario.status.state = EStatus.RUNNING
                logger.info(f"The scenario {scenario.id} has uncompleted "
                            "stages")
            else:
                scenario.status.state = EStatus.ERROR
                logger.error(f"Scenario {scenario.id} has stages which "
                             "do not appear to be complete.")

        scenario_states = [scenario.status.state for scenario in
                           [s for s in forecast.scenarios if s.enabled]]

        if all([state == EStatus.ERROR
                for state in scenario_states]):
            forecast.status.state = EStatus.ERROR
            session.commit()
            raise Exception("Forecast has errors")
        elif any([state == EStatus.ERROR
                  for state in scenario_states]):
            forecast.status.state = EStatus.COMPLETE
            logger.warning("Some scenarios have failed")

        else:
            forecast.status.state = EStatus.COMPLETE
        session.commit()
