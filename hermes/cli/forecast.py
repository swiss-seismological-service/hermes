import uuid
from datetime import datetime

import typer
from rich.console import Console
from typing_extensions import Annotated

from hermes.actions.crud_models import read_forecastseries_oid
from hermes.cli.utils import row_table
from hermes.flows.forecast_handler import forecast_runner
from hermes.repositories.database import Session
from hermes.repositories.project import ForecastRepository
from hermes.utils.dateutils import local_to_utc

app = typer.Typer()
console = Console()


@app.command(help="Outputs list of Forecast "
             "belonging to the same ForecastSeries.")
def list():
    with Session() as session:
        forecasts = ForecastRepository.get_all(session)
    if not forecasts:
        console.print("No Forecasts found")
        return

    table = row_table(forecasts, ['oid', 'starttime', 'endtime', 'status'])

    console.print(table)


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

    try:
        forecastseries_oid = read_forecastseries_oid(forecastseries)
        start = local_to_utc(start)
        end = local_to_utc(end)

        forecast_runner(forecastseries_oid, start, end, mode='local')

    except Exception as e:
        console.print(str(e))
        typer.Exit(code=1)


@app.command(help="Deletes a Forecast.")
def delete(
    forecast_oid: Annotated[uuid.UUID,
                            typer.Argument(
                                help="UUID of "
                                "the ForecastSeries.")]):
    try:
        with Session() as session:
            ForecastRepository.delete(session, forecast_oid)
        console.print(f"ForecastSeries {forecast_oid} deleted.")
    except Exception as e:
        console.print(str(e))
        typer.Exit(code=1)
