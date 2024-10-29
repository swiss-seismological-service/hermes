import json
from pathlib import Path

import typer
from rich.console import Console
from typing_extensions import Annotated

from hermes.actions.crud import (create_schedule, read_forecastseries_oid,
                                 update_schedule)
from hermes.cli.utils import row_table
from hermes.flows.forecastseries_scheduler import ForecastSeriesScheduler
from hermes.repositories.database import Session
from hermes.repositories.project import ForecastSeriesRepository
from hermes.utils.dateutils import local_to_utc_dict

app = typer.Typer()
console = Console()


@app.command(help="Lists existing schedules.")
def list():
    with Session() as session:
        fseries = ForecastSeriesRepository.get_all(session)

    fseries = [f for f in fseries if f.schedule_id]

    if not fseries:
        console.print("No Schedules found")
        return

    table = row_table(fseries, ['name',
                                'schedule_starttime',
                                'schedule_endtime',
                                'schedule_interval'])

    console.print(table)


@app.command(help="Schedules future Forecasts.")
def create(
    forecastseries: Annotated[str,
                              typer.Argument(
                                  help="Name or UUID of "
                                  "the ForecastSeries.")],
    config: Annotated[Path,
                      typer.Option(
                          ...,
                          resolve_path=True,
                          readable=True,
                          help="Path to json schedule "
                          "configuration file.")]):

    with open(config, "r") as project_file:
        schedule_config = json.load(project_file)

    schedule_config = local_to_utc_dict(schedule_config)

    try:
        forecastseries_oid = read_forecastseries_oid(forecastseries)
        create_schedule(forecastseries_oid, schedule_config)

        console.print(
            f'Successfully created schedule for {forecastseries}.')
    except BaseException as e:
        console.print(str(e))
        typer.Exit(code=1)


@app.command(help="Updates existing schedule.")
def update(
    forecastseries: Annotated[str,
                              typer.Argument(
                                  help="Name or UUID of "
                                  "the ForecastSeries.")],
    config: Annotated[Path,
                      typer.Option(
                          ...,
                          resolve_path=True,
                          readable=True,
                          help="Path to json schedule "
                          "configuration file.")]):

    with open(config, "r") as project_file:
        schedule_config = json.load(project_file)

    schedule_config = local_to_utc_dict(schedule_config)
    try:
        forecastseries_oid = read_forecastseries_oid(forecastseries)
        update_schedule(forecastseries_oid, schedule_config)
        console.print(
            f'Successfully updated schedule for {forecastseries}.')
    except BaseException as e:
        console.print(str(e))
        typer.Exit(code=1)


@app.command(help="Deletes existing schedule.")
def delete(
    forecastseries: Annotated[str,
                              typer.Argument(
                                  help="Name or UUID of "
                                  "the ForecastSeries.")]):

    try:
        forecastseries_oid = read_forecastseries_oid(forecastseries)

        scheduler = ForecastSeriesScheduler(forecastseries_oid)
        scheduler.delete_prefect_schedule()
        console.print(
            f'Successfully deleted schedule for {forecastseries}.')
    except BaseException as e:
        console.print(str(e))
        typer.Exit(code=1)


@app.command(help="Activate existing schedule.")
def activate(
    forecastseries: Annotated[str,
                              typer.Argument(
                                  help="Name or UUID of "
                                  "the ForecastSeries.")]):

    try:
        forecastseries_oid = read_forecastseries_oid(forecastseries)
        update_schedule(forecastseries_oid, {'schedule_active': True})

        console.print(
            f'Successfully activated schedule for {forecastseries}.')
    except BaseException as e:
        console.print(str(e))
        typer.Exit(code=1)


@app.command(help="Deactivate existing schedule.")
def deactivate(
    forecastseries: Annotated[str,
                              typer.Argument(
                                  help="Name or UUID of "
                                  "the ForecastSeries.")]):

    try:
        forecastseries_oid = read_forecastseries_oid(forecastseries)
        update_schedule(forecastseries_oid, {'schedule_active': False})

        console.print(
            f'Successfully deactivated schedule for {forecastseries}.')
    except BaseException as e:
        console.print(str(e))
        typer.Exit(code=1)


@app.command(help="Executes Forecasts for the given schedule which "
             "have scheduled start times in the past.")
def catchup():
    raise NotImplementedError
