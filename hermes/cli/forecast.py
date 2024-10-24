import uuid
from datetime import datetime

import typer
from rich.console import Console
from typing_extensions import Annotated

from hermes.flows.forecast_handler import forecast_runner
from hermes.repositories.database import Session
from hermes.repositories.project import ForecastSeriesRepository
from hermes.utils.dateutils import local_to_utc

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
    end: Annotated[datetime,
                   typer.Option(
                       ...,
                       help="Endtime of the Forecast.")],
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

    start = local_to_utc(start)
    end = local_to_utc(end)

    forecast_runner(forecastseries_db.oid, start, end, mode='local')
