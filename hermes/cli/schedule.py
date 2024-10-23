import json
from pathlib import Path

import typer
from rich.console import Console
from typing_extensions import Annotated

from hermes.actions.crud import read_forecastseries_oid
from hermes.flows.forecastseries_scheduler import ForecastSeriesScheduler

app = typer.Typer()
console = Console()


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
                          help="Path to json Forecastseries "
                          "configuration file.")]):

    with open(config, "r") as project_file:
        schedule_config = json.load(project_file)

    try:
        forecastseries_oid = read_forecastseries_oid(forecastseries)

        scheduler = ForecastSeriesScheduler(forecastseries_oid)
        scheduler.create_prefect_schedule(schedule_config)
    except BaseException as e:
        console.print(str(e))
        typer.Exit(code=1)

    console.print(
        f'Successfully created schedule for {forecastseries}.')
