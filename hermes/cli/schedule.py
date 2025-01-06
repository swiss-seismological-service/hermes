import json
from pathlib import Path

import typer
from rich.console import Console
from typing_extensions import Annotated

from hermes.actions.crud_models import (create_schedule,
                                        read_forecastseries_oid,
                                        update_schedule)
from hermes.cli.utils import console_table, console_tree
from hermes.flows.forecastseries_scheduler import ForecastSeriesScheduler
from hermes.repositories.database import Session
from hermes.repositories.project import ForecastSeriesRepository
from hermes.schemas.project_schemas import ForecastSeriesSchedule

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

    table = console_table(fseries, ['name',
                                    'schedule_starttime',
                                    'schedule_interval',
                                    'schedule_active'])

    console.print(table)


@app.command(help="Show full details of a single schedule.")
def show(
    forecastseries: Annotated[str,
                              typer.Argument(
                                  help="Name or UUID of "
                                  "the ForecastSeries.")]):

    try:
        with Session() as session:
            forecastseries_oid = read_forecastseries_oid(forecastseries)
            forecast_series = ForecastSeriesRepository.get_by_id(
                session, forecastseries_oid)
    except ValueError as e:
        console.print(str(e))
        raise typer.Exit(code=1)
    except BaseException as e:
        raise e

    if not forecast_series.schedule_id:
        console.print("No schedule found.")
        raise typer.Exit(code=1)

    # don't display all the schedule information
    fs_config = ForecastSeriesSchedule(
        **forecast_series.model_dump(
            include=ForecastSeriesSchedule.model_fields.keys()))

    tree = console_tree(fs_config)
    console.print(tree)


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

    try:
        forecastseries_oid = read_forecastseries_oid(forecastseries)
        create_schedule(schedule_config, forecastseries_oid)

        console.print(
            f'Successfully created schedule for {forecastseries}.')
    except BaseException as e:
        console.print(str(e))
        raise typer.Exit(code=1)


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

    try:
        forecastseries_oid = read_forecastseries_oid(forecastseries)
        update_schedule(schedule_config, forecastseries_oid)
        console.print(
            f'Successfully updated schedule for {forecastseries}.')
    except BaseException as e:
        console.print(str(e))
        raise typer.Exit(code=1)


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
        raise typer.Exit(code=1)


@app.command(help="Activate existing schedule.")
def activate(
    forecastseries: Annotated[str,
                              typer.Argument(
                                  help="Name or UUID of "
                                  "the ForecastSeries.")]):

    try:
        forecastseries_oid = read_forecastseries_oid(forecastseries)
        update_schedule({'schedule_active': True}, forecastseries_oid)

        console.print(
            f'Successfully activated schedule for {forecastseries}.')
    except BaseException as e:
        console.print(str(e))
        raise typer.Exit(code=1)


@app.command(help="Deactivate existing schedule.")
def deactivate(
    forecastseries: Annotated[str,
                              typer.Argument(
                                  help="Name or UUID of "
                                  "the ForecastSeries.")]):

    try:
        forecastseries_oid = read_forecastseries_oid(forecastseries)
        update_schedule({'schedule_active': False}, forecastseries_oid)

        console.print(
            f'Successfully deactivated schedule for {forecastseries}.')
    except BaseException as e:
        console.print(str(e))
        raise typer.Exit(code=1)


@app.command(help="Executes Forecasts for the given schedule which "
             "have scheduled start times in the past.")
def catchup():
    raise NotImplementedError
