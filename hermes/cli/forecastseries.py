import asyncio
import json
from datetime import datetime, timedelta
from os.path import abspath, dirname, isabs, join
from pathlib import Path
from typing import List

import typer
from dateutil.rrule import SECONDLY, rrule
from marshmallow import EXCLUDE
from prefect.server.schemas.schedules import RRuleSchedule
from ramsis.datamodel import EStatus, Forecast, ForecastSeries, Project
from ramsis.io.configuration import ForecastSeriesConfigurationSchema
from rich import print
from rich.table import Table
from sqlalchemy import select

from hermes.cli.utils import (add_new_scheduled_run, delete_flow_runs,
                              flow_deployment, get_deployment_name,
                              list_flow_runs_with_states)
from hermes.db import db_url, session_handler
from hermes.flows.forecast import scheduled_ramsis_flow

app = typer.Typer()


@app.command()
def stop(forecastseries_id: int,
         help="Stops all flow runs that have this forecastseries id"):
    runs = asyncio.run(list_flow_runs_with_states(
        ["Scheduled", "Running", "Pending", "Retrying"]))

    fs_runs = []
    if not runs:
        print("No forecasts scheduled/in progress for this forecast series")
    for run in runs:
        if run.parameters['forecastseries_id'] == forecastseries_id:
            fs_runs.append(run)
    asyncio.run(delete_flow_runs(fs_runs))
    print("Deleted scheduled forecast with parameters: "
          f"{[run.parameters for run in fs_runs]}")


@app.command()
def ls(full: bool = typer.Option(
        False, help="Give all info on forecast series."),
        help="Outputs list of forecast series"):
    with session_handler(db_url) as session:
        forecastseries_list = session.execute(
            select(ForecastSeries)).\
            scalars().all()
        for series in forecastseries_list:
            table = Table(show_footer=False,
                          title=f"Forecast Series {series.name}",
                          title_justify="left")
            table.add_column("attribute")
            table.add_column("value")
            for attr in ForecastSeries.__table__.columns:
                if str(attr.name) not in ['injectionplans']:
                    if not full and str(attr.name) not in \
                            ['id', 'status', 'starttime', 'endtime',
                             'forecastinterval', 'forecastduration']:
                        continue
                    table.add_row(str(attr.name), str(
                        getattr(series, attr.name)))

            print(table)


@app.command()
def schedule(forecastseries_id: int,
             overdue_interval: int = typer.Option(
                 60, help="Interval to run overdue forecasts at"),
             help="""Tells the prefect server to schedule forecasts
             to run for the parameters set on the forecast series.
             Forecasts that have a starttime in the past will be
             be run with a spacing of --overdue-interval, and these
             are scheduled in parallel to future forecasts. Future
             forecasts are always scheduled to start at the forecast
             starttime."""):
    flow_to_schedule = scheduled_ramsis_flow
    with session_handler(db_url) as session:
        forecastseries = session.execute(
            select(ForecastSeries).filter_by(id=forecastseries_id)).\
            scalar_one_or_none()
        if not forecastseries:
            print("The forecastseries id does not exist")
            raise typer.Exit()

        datetime_now = datetime.utcnow()
        forecasts = forecastseries.forecasts
        dtstart = forecastseries.starttime
        if forecasts:
            dtstart = max(f.starttime for f in forecasts)
            if forecastseries.forecastinterval:
                dtstart += timedelta(
                    seconds=forecastseries.forecastinterval)
            if dtstart == forecastseries.endtime:
                print("Forecast Series completed. Please reset forecast "
                      "series and then schedule again.")
            else:
                reschedule = typer.confirm(
                    "Forecast exist, are you sure you want to "
                    "run a new schedule to continue from the last "
                    "forecast?")
                if not reschedule:
                    print("Not rescheduling")
                    raise typer.Abort()
                else:
                    print(f"The schedule will resume from {dtstart}")
        deployment_name = get_deployment_name(forecastseries_id)

        # If there is a forecast interval, then we run multiple forecasts
        if forecastseries.forecastinterval:
            rrule_obj = rrule(
                freq=SECONDLY, interval=forecastseries.forecastinterval,
                dtstart=forecastseries.starttime, until=forecastseries.endtime)
            rrule_str = str(rrule_obj)
            rrule_schedule = RRuleSchedule(rrule=rrule_str)
            deployment = flow_deployment(flow_to_schedule, deployment_name,
                                         rrule_schedule, forecastseries.id,
                                         db_url)
            # Check for runs that were scheduled in the past and
            # will therefore not run
            scheduled_wait_time = 0
            # If times exist in the future, these are logged.
            if list(rrule_obj):
                msg = ("scheduling forecasts for the following times..."
                       f"{list(rrule_obj)[0:10]}...")
                print(msg)
                forecastseries.add_log(msg)
                session.commit()

            # Find times that occured in the past
            if forecastseries.endtime and \
                    datetime_now > forecastseries.endtime:
                overdue_limit = forecastseries.endtime - timedelta(seconds=1)
            else:
                overdue_limit = datetime_now

            overdue_rrule_obj = rrule(
                freq=SECONDLY, interval=forecastseries.forecastinterval,
                dtstart=dtstart, until=overdue_limit)
            for forecast_starttime in list(overdue_rrule_obj):
                scheduled_start_time = datetime_now + timedelta(
                    seconds=scheduled_wait_time)
                msg = ("scheduling overdue forecast with starttime: "
                       f"{forecast_starttime} to be run in: "
                       f"{scheduled_wait_time} seconds.")
                print(msg)
                forecastseries.add_log(msg)
                session.commit()
                asyncio.run(
                    add_new_scheduled_run(
                        flow_to_schedule.name, deployment.name,
                        forecast_starttime, scheduled_start_time,
                        forecastseries.id, db_url))
                scheduled_wait_time += overdue_interval
        else:
            # run single forecast
            msg = ("scheduling single forecast with "
                   f"scheduled start time: {forecastseries.starttime}")
            print(msg)
            forecastseries.add_log(msg)
            session.commit()
            asyncio.run(
                add_new_scheduled_run(
                    flow_to_schedule.name, deployment_name,
                    forecastseries.starttime, forecastseries.starttime,
                    forecastseries.id, db_url))
        forecastseries.active = True
        forecastseries.add_log("The forecast series is active.")
        session.commit()


@app.command()
def reset(forecastseries_id: int,
          force: bool = typer.Option(
              False, help="Force the reset without asking"),
          help="Resets the status to PENDING and deletes existing, "
          "so that the forecast can be rerun in full."):
    with session_handler(db_url) as session:
        forecastseries = session.execute(
            select(ForecastSeries).filter_by(id=forecastseries_id)).\
            scalar_one_or_none()
        if not forecastseries:
            print("The forecastseries does not exist")
            raise typer.Exit()
        if not force:
            reset = typer.confirm(
                "Are you sure you want to reset the "
                f"forecastseries with id: {forecastseries_id}? "
                "This will delete all the existing forecasts.")
            if not reset:
                print("Not resetting")
                raise typer.Abort()

        session.query(Forecast).filter(
            Forecast.forecastseries_id == forecastseries_id).delete()
        forecastseries.status = EStatus.PENDING
        forecastseries.log = []
        session.commit()
        print(f"Finished resetting forecastseries {forecastseries_id}")


@app.command()
def delete(forecastseries_ids: List[int],
           force: bool = typer.Option(
               False, help="Force the deletes without asking"),
           help="Delete forecast series from the database."):
    with session_handler(db_url) as session:
        for forecastseries_id in forecastseries_ids:
            forecastseries = session.execute(
                select(ForecastSeries).filter_by(id=forecastseries_id)).\
                scalar_one_or_none()
            if not forecastseries:
                print("The forecastseries does not exist")
                raise typer.Exit()
            if not force:
                delete = typer.confirm(
                    "Are you sure you want to delete the "
                    f"forecastseries with id: {forecastseries_id}")
                if not delete:
                    print("Not deleting")
                    raise typer.Abort()

            session.delete(forecastseries)
            session.commit()
            print(f"Finished deleting forecast {forecastseries_id}")


@app.command()
def create(
        config: Path = typer.Option(
        ...,
        exists=True,
        readable=True,
        help="Can be absolute or relative"),
        project_id: int = typer.Option(
            None,
            help="Project id to associate the forecast series to. If not"
                 " provided, the latest project id will be used.")):

    with session_handler(db_url) as session:
        if not project_id:
            project = session.execute(
                select(Project).order_by(Project.id.desc())).first()[0]
        else:

            project = session.execute(
                select(Project).filter_by(id=project_id)).scalar_one_or_none()

        if not project:
            print(f"Project id {project_id} does not exist")
            raise typer.Exit()

        with open(config, "r") as forecastseries_json:
            config_dict = json.load(forecastseries_json)

        new_forecastseries = []
        for forecastseries_config in config_dict["forecastseries_configs"]:
            # Make sure the directory location is absolute
            if "injectionplan_dir" in forecastseries_config.keys():
                inj_dir = forecastseries_config["injectionplan_dir"]
                if not isabs(inj_dir):
                    forecastseries_config["injectionplan_dir"] = join(
                        abspath(dirname(config)), inj_dir)

            forecastseries = ForecastSeriesConfigurationSchema(
                unknown=EXCLUDE, context={"session": session}).\
                load(forecastseries_config)
            forecastseries.project = project
            new_forecastseries.append(forecastseries)
            session.add(forecastseries)
            session.commit()

        for forecastseries in new_forecastseries:
            msg = (f"created forecastseries: {forecastseries.name} "
                   f"with id: {forecastseries.id} under project: "
                   f"{project.name}, with id: {project.id}"
                   f" with tags: {forecastseries.tags}."
                   " To schedule forecast series: "
                   f"ramsis forecastseries schedule {forecastseries.id}")
            print(msg)
            forecastseries.add_log(msg)
        session.commit()
