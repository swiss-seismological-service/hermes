import prefect
from prefect import Task
from prefect.tasks.shell import ShellTask
from RAMSIS.db import app_settings
from RAMSIS.core.store import session_handler
from ramsis.datamodel import EStatus, EStage
from RAMSIS.db_utils import get_forecast
from RAMSIS.utils import reset_forecast


dummy_shell_task = ShellTask(
    helper_script=app_settings['env/load_environment_cmd'],
    return_all=True, stream_output=True)


class ForecastTask(Task):
    def run_task(self, forecast, session, **kwargs):
        raise NotImplementedError

    def run(self, forecast_id, connection_string, **kwargs):
        with session_handler(connection_string) as session:
            forecast = get_forecast(forecast_id, session)
            if not forecast:
                raise Exception(f"No forecast found {forecast_id}")
            retval = self.run_task(forecast, session, **kwargs)
        return retval


class CloneForecast(ForecastTask):
    def run_task(self, reference_forecast, session):

        logger = prefect.context.get('logger')
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

        scheduled_start_time = prefect.context.get("scheduled_start_time")
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


class SeismicityStageCheck(ForecastTask):
    def run_task(self, forecast, session):
        if forecast.status.state == EStatus.COMPLETE:
            return False
        for scenario in forecast.scenarios:
            if scenario[EStage.SEISMICITY].status.state == EStatus.COMPLETE:
                return False
        return True


class HazardStageCheck(ForecastTask):
    def run_task(self, forecast, session):
        """Returns True if Hazard Stage should start."""
        logger = prefect.context.get('logger')
        for scenario in forecast.scenarios:
            if scenario[EStage.SEISMICITY].status.state != EStatus.COMPLETE:
                logger.warning("A seismicity stage has the status: "
                               f"{scenario[EStage.SEISMICITY].status.state}")
                return False
            try:
                if scenario[EStage.HAZARD].status.state != EStatus.COMPLETE:
                    return True
            except KeyError:
                return False
        return True


class UpdateForecastStatus(ForecastTask):
    def run_task(self, forecast, session, estatus):
        forecast.status.state = estatus
        session.commit()


class CheckSeismicityStage(ForecastTask):

    def stage_states(self, forecast, session, estage):
        stage_states = []
        for scenario in forecast.scenarios:
            try:
                stage = scenario[estage].status.state
                stage_states.append(stage)
            except KeyError:
                pass
        return stage_states

    def run_task(self, forecast, session):
        seismicity_stage_states = self.stage_states(
            forecast, session, EStage.SEISMICITY)
        return any(state != EStatus.COMPLETE for state in
                   seismicity_stage_states)
