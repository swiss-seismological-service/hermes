import typer

from hermes.db import Session
from hermes.repositories.forecastseries import ForecastSeriesRepository
from hermes.schemas import ForecastSeries

app = typer.Typer()


@app.command()
def create():
    forecast_series = ForecastSeries(
        name="test", project_oid="0cc02b40-8255-4aba-ad31-f8ba11b353ec")

    with Session() as session:
        forecast_series_in = ForecastSeriesRepository.create(
            session, forecast_series)
        forecast_series_out = ForecastSeriesRepository.get_one_by_id(
            session, forecast_series_in.oid)

    print(type(forecast_series_out))
