import json
from pathlib import Path

import typer
from rich.console import Console
from typing_extensions import Annotated

from hermes.actions.crud import (create_forecastseries,
                                 read_forecastseries_oid, read_project_oid,
                                 update_forecastseries)
from hermes.cli.utils import row_table
from hermes.repositories.database import Session
from hermes.repositories.project import ForecastSeriesRepository

app = typer.Typer()
console = Console()


@app.command(help="Outputs list of ForecastSeries")
def list():
    with Session() as session:
        fseries = ForecastSeriesRepository.get_all(session)
    if not fseries:
        console.print("No ForecastSeries found")
        return

    table = row_table(fseries, ['oid', 'name', 'status'])

    console.print(table)


@app.command(help="Creates a new ForecastSeries.")
def create(name: Annotated[str,
                           typer.Argument(
                               help="Name of the ForecastSeries.")],
           project: Annotated[str,
                              typer.Argument(
                                  help="Name or UUID of the parent Project.")],
           config: Annotated[Path,
                             typer.Option(
                                 ..., resolve_path=True, readable=True,
                                 help="Path to json Forecastseries "
                                 "configuration file.")]):

    with open(config, "r") as project_file:
        fseries_config = json.load(project_file)

    try:
        project_oid = read_project_oid(project)

        forecast_series_out = create_forecastseries(
            name, fseries_config, project_oid)

        console.print('Successfully created new ForecastSeries '
                      f'{forecast_series_out.name}.')
    except Exception as e:
        console.print(str(e))
        typer.Exit(code=1)


@app.command(help="Updates a ForecastSeries.")
def update(
    forecastseries: Annotated[str,
                              typer.Argument(
                                  help="Name or UUID of the ForecastSeries.")],
    config: Annotated[Path,
                      typer.Option(
                          ..., resolve_path=True, readable=True,
                          help="Path to json Forecastseries "
                          "configuration file.")],
    force: Annotated[bool,
                     typer.Option("--force")] = False):

    with open(config, "r") as project_file:
        fseries_config = json.load(project_file)

    try:
        forecastseries_oid = read_forecastseries_oid(forecastseries)

        forecast_series_out = update_forecastseries(
            fseries_config, forecastseries_oid, force)

        console.print(
            f'Successfully updated ForecastSeries {forecast_series_out.name}.')
    except Exception as e:
        console.print(str(e))
        typer.Exit(code=1)
