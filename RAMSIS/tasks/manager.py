from prefect import Task
import prefect
from RAMSIS.db import store
from ramsis.datamodel import Forecast, EStatus, EStage

class ForecastTask(Task):
    def run_task(self, forecast, session, **kwargs):
        raise NotImplementedError

    def run(self, forecast_id, **kwargs):
        session = store.session
        forecast = session.query(Forecast).filter(
            Forecast.id==forecast_id).one_or_none()
        retval = self.run_task(forecast, session, **kwargs)
        session.remove()
        return retval

class StartForecastCheck(ForecastTask):
    def run_task(self, forecast, session):
        self.logger.info(f"prefect.context {type(prefect.context)}")
        print(f"prefect.context {type(prefect.context)}")
        if forecast.status.state != EStatus.COMPLETE:
            return True
        return False

class UpdateForecastStatus(ForecastTask):
    def run_task(self, forecast, session, estatus=None):
        if not estatus:
            raise IOError('estatus is None')
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
        seismicity_stage_states = self.stage_states(forecast, session, EStage.SEISMICITY)
        return any(state != EStatus.COMPLETE for state in
                   seismicity_stage_states)

#def get_forecast_starttime(session, forecast_id):
#    forecast = session.query(Forecast).filter(
#        Forecast.id == forecast_id).first()
#    return forecast.starttime
