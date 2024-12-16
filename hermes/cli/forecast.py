import uuid
from datetime import datetime

import typer
from prefect.deployments import run_deployment
from rich.console import Console
from typing_extensions import Annotated

from hermes.actions.crud_models import read_forecastseries_oid
from hermes.cli.utils import console_table
from hermes.flows.forecast_handler import forecast_runner
from hermes.repositories.database import Session
from hermes.repositories.project import ForecastRepository
from hermes.utils.dateutils import local_to_timezone

app = typer.Typer()
console = Console()


@app.command(help="Outputs list of Forecast "
             "belonging to the same ForecastSeries.")
def list(
    forecastseries: Annotated[str,
                              typer.Argument(
                                  help="Name or UUID of "
                                  "the ForecastSeries.")],):
    with Session() as session:
        forecastseries_oid = read_forecastseries_oid(forecastseries)
        forecasts = ForecastRepository.get_by_forecastseries(
            session, forecastseries_oid)
    if not forecasts:
        console.print("No Forecasts found")
        return

    table = console_table(
        forecasts, ['oid', 'starttime', 'endtime', 'status'])

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
    local: Annotated[
        bool,
        typer.Option(
            help="Flag to run the Forecast in local mode.")] = False
):

    try:
        forecastseries_oid = read_forecastseries_oid(forecastseries)
        start = local_to_timezone(start)
        end = local_to_timezone(end)
        mode = 'local' if local else 'deploy'
        if local:
            forecast_runner(forecastseries_oid, start, end, mode)
        else:
            run_deployment(
                name=f'ForecastRunner/{forecastseries_oid}',
                parameters={'forecastseries_oid': forecastseries_oid,
                            'starttime': start,
                            'endtime': end,
                            'mode': mode},
                timeout=0
            )

    except Exception as e:
        console.print(str(e))
        raise typer.Exit(code=1)


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
        raise typer.Exit(code=1)
