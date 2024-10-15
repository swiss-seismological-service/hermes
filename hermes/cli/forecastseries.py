import json
import uuid
from pathlib import Path

import typer
from rich.console import Console
from typing_extensions import Annotated

from hermes.cli.utils import row_table
from hermes.flows.forecastseries_scheduler import ForecastSeriesScheduler
from hermes.repositories.database import Session
from hermes.repositories.project import (ForecastSeriesRepository,
                                         ProjectRepository)
from hermes.schemas import EStatus, ForecastSeries

app = typer.Typer()
console = Console()


@app.command(help="Outputs list of ForecastSeries")
def list():
    with Session() as session:
        fseries = ForecastSeriesRepository.get_all(session)
    if not fseries:
        console.print("No ForecastSeries found")
        return

    table = row_table(fseries, ['oid', 'name', 'forecast_starttime', 'status'])

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
            project_db = ProjectRepository.get_by_name(session, project)

        if not project_db:
            console.print(f'Project "{project}" not found.')
            raise typer.Exit()

        project_oid = project_db.oid

    forecast_series = ForecastSeries(name=name,
                                     status=EStatus.PENDING,
                                     project_oid=project_oid,
                                     **fseries_config_dict)

    with Session() as session:
        forecast_series_out = ForecastSeriesRepository.create(
            session, forecast_series)
    console.print(
        f'Successfully created new ForecastSeries {forecast_series_out.name}.')


@app.command(help="Executes past Forecasts and schedules future Forecasts.")
def schedule(forecastseries: Annotated[str,
                                       typer.Argument(
                                           help="Name or UUID of "
                                           "the ForecastSeries.")]):
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

    scheduler = ForecastSeriesScheduler(forecastseries_db)
    # scheduler.run()
