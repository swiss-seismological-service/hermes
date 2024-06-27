import typer

from hermes.db import Session
from hermes.repositories import ForecastSeriesRepository
from hermes.schemas import ForecastSeries

app = typer.Typer()


@app.command()
def create():
    forecast_series = ForecastSeries(
        name="test", project_oid="03cfee0f-db5e-4b14-9bda-1e5efede78fa")

    with Session() as session:
        forecast_series_in = ForecastSeriesRepository.create(
            session, forecast_series)
        forecast_series_out = ForecastSeriesRepository.get_one_by_id(
            session, forecast_series_in.oid)

    print(type(forecast_series_out))
