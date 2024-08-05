import uuid
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from hermes.flows.create_forecast import ForecastExecutor
from hermes.repositories.database import Session
from hermes.repositories.project import ForecastSeriesRepository

app = typer.Typer()
console = Console()


@app.command(help="Run a Forecast.")
def run(
    forecastseries: Annotated[str,
                              typer.Argument(
                                  help="Name or UUID of "
                                  "the ForecastSeries.")],
    start: Annotated[datetime,
                     typer.Option(
                         ...,
                         help="Starttime of the Forecast.")],
    end: Annotated[Optional[datetime],
                   typer.Option(
                       help="Endtime of the Forecast.")] = None,
):
    # Get the forecastseries
    try:
        forecastseries_oid = uuid.UUID(forecastseries, version=4)
        with Session() as session:
            forecastseries_db = ForecastSeriesRepository.get_by_id(
                session, forecastseries_oid)
    except ValueError:
        with Session() as session:
            forecastseries_db = ForecastSeriesRepository.get_by_name(
                session, forecastseries)

        if not forecastseries_db:
            console.print(f'ForecastSeries "{forecastseries}" not found.')
            raise typer.Exit()

    # Run the forecast
    with Session() as session:
        forecast = ForecastExecutor(
            session, forecastseries_db, start, end)
        forecast.run()

    console.print(f'Forecast "{forecast.forecast.name}" dispatched.')
