from ramsis.datamodel import Forecast, \
    ForecastSeries, ModelRun
from prefect import get_run_logger
from sqlalchemy import select


def get_forecastseries(forecastseries_id, session):
    forecast = session.query(ForecastSeries).filter(
        ForecastSeries.id == forecastseries_id).first()
    return forecast


def get_forecast(forecast_id, session):
    forecast = session.query(Forecast).filter(
        Forecast.id == forecast_id).first()
    return forecast


def get_model_run(model_run_id, session):
    model_run = session.query(ModelRun).filter(
        ModelRun.id == model_run_id).first()
    return model_run


def update_forecast_status(forecast_id, estatus, session):
    forecast = get_forecast(forecast_id, session)
    forecast.status.state = estatus


def set_statuses_db(forecast_id, estatus, session):
    logger = get_run_logger()
    forecast = session.execute(
        select(Forecast).filter_by(id=forecast_id)).scalar_one()
    logger.info(f"forecast state: {forecast.status.state}")
