
from ramsis.datamodel import Forecast
import prefect
from sqlalchemy import select


def get_forecast(forecast_id, session):
    forecast = session.query(Forecast).filter(
        Forecast.id == forecast_id).first()
    return forecast


def update_forecast_status(forecast_id, estatus, session):
    forecast = get_forecast(forecast_id, session)
    forecast.status.state = estatus


def stage_statuses(forecast_id, estage, session):
    forecast = get_forecast(forecast_id, session)
    stage_states_list = []
    for scenario in forecast.scenarios:
        try:
            stage = scenario[estage].status
            stage_states_list.append(stage)
        except KeyError:
            pass
    return stage_states_list


def run_stage(forecast, estage):
    try:
        scenarios = forecast.scenarios
        for scenario in scenarios:
            if scenario[estage].enabled:
                return True
    except KeyError:
        pass
    return False


def set_statuses(forecast_id, estatus, session):
    logger = prefect.context.get('logger')
    forecast = session.execute(
        select(Forecast).filter_by(id=forecast_id)).scalar_one()
    forecast.status.state = estatus
    for scenario in forecast.scenarios:
        scenario.status.state = estatus
    logger.info(f"forecast state: {forecast.status.state}")
