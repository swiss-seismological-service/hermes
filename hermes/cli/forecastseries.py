import json
import uuid
from pathlib import Path

import typer
from rich.console import Console
from typing_extensions import Annotated

from hermes.cli.utils import row_table
from hermes.db import Session
from hermes.repositories.forecastseries import ForecastSeriesRepository
from hermes.repositories.project import ProjectRepository
from hermes.schemas import ForecastSeries

app = typer.Typer()
console = Console()


@app.command(help="Outputs list of ForecastSeries")
def list(help="List all ForecastSeries."):
    with Session() as session:
        fseries = ForecastSeriesRepository.get_all(session)
    if not fseries:
        console.print("No ForecastSeries found")
        return

    table = row_table(fseries, ['oid', 'name', 'forecast_starttime'])

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
        fseries_config_dict = json.load(project_file)

    try:
        project_oid = uuid.UUID(project, version=4)
    except ValueError:
        with Session() as session:
            project_oid = ProjectRepository.get_by_name(session, project).oid

    if not project_oid:
        console.print(f'Project {project} not found.')
        raise typer.Exit()

    forecast_series = ForecastSeries(name=name,
                                     project_oid=project_oid,
                                     **fseries_config_dict)

    with Session() as session:
        forecast_series_out = ForecastSeriesRepository.create(
            session, forecast_series)

    print(forecast_series_out)
