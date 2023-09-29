from typing import List
import asyncio
import typer
import json
from dateutil.rrule import rrule, SECONDLY
from prefect.server.schemas.schedules import RRuleSchedule
from marshmallow import EXCLUDE
from datetime import timedelta, datetime
from sqlalchemy import select
from ramsis.datamodel import ForecastSeries, Project
from ramsis.io.configuration import ForecastSeriesConfigurationSchema
from RAMSIS.db import db_url, session_handler
from RAMSIS.cli.utils import flow_deployment, add_new_scheduled_run, \
    get_deployment_name, set_schedule_inactive

from pathlib import Path
from RAMSIS.flows.forecast import scheduled_ramsis_flow


app = typer.Typer()


@app.command()
def disable_schedule(forecastseries_id: int):
    with session_handler(db_url) as session:
        forecastseries = session.execute(
            select(ForecastSeries).filter_by(id=forecastseries_id)).\
            scalar_one_or_none()
        if not forecastseries:
            typer.echo("The forecastseries id does not exist")
            raise typer.Exit()
        asyncio.run(set_schedule_inactive(forecastseries.id))
        # Need to add enabled to the db and update here.


@app.command()
def ls(forecastseries_id: int):
    with session_handler(db_url) as session:
        forecastseries_list = session.execute(
            select(ForecastSeries)).\
            scalars().all()
        for series in forecastseries_list:
            typer.echo(
                f"ForecastSeries id: {series.id}, name: {series.name}"
                f" tags: {series.tags}, project: {series.project}, "
                f"forecast interval {series.forecastinterval}, "
                f"forecasts: {series.forecasts}, injectionplans: "
                f"{series.injectionplans}")


@app.command()
def schedule(forecastseries_id: int,
             overdue_interval: int = typer.Option(
                 60, help="Interval to run overdue forecasts at")):
    flow_to_schedule = scheduled_ramsis_flow
    with session_handler(db_url) as session:
        forecastseries = session.execute(
            select(ForecastSeries).filter_by(id=forecastseries_id)).\
            scalar_one_or_none()
        if not forecastseries:
            typer.echo("The forecastseries id does not exist")
            raise typer.Exit()

        datetime_now = datetime.utcnow()
        forecasts = forecastseries.forecasts
        if forecasts:
            typer.echo("Forecasts exist, please reset forecastseries or "
                       "create a new one.")
            typer.Exit()
        deployment_name = get_deployment_name(forecastseries_id)
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
            typer.echo("scheduling forecasts for the following times..."
                       f"{list(rrule_obj)[0:10]}...")
            overdue_rrule_obj = rrule(
                freq=SECONDLY, interval=forecastseries.forecastinterval,
                dtstart=forecastseries.starttime, until=datetime_now)
            for forecast_starttime in list(overdue_rrule_obj):
                scheduled_start_time = datetime_now + timedelta(
                    seconds=scheduled_wait_time)
                typer.echo(f"scheduling forecast for {forecast_starttime}")
                asyncio.run(
                    add_new_scheduled_run(
                        flow_to_schedule.name, deployment.name,
                        forecast_starttime, scheduled_start_time,
                        forecastseries.id, db_url))
                scheduled_wait_time += overdue_interval
        else:
            # run single forecast
            asyncio.run(
                add_new_scheduled_run(
                    flow_to_schedule.name, deployment_name,
                    forecastseries.starttime, forecastseries.starttime,
                    forecastseries.id, db_url))


@app.command()
def delete(forecastseries_ids: List[int],
           force: bool = typer.Option(
               False, help="Force the deletes without asking")):
    with session_handler(db_url) as session:
        for forecastseries_id in forecastseries_ids:
            forecastseries = session.execute(
                select(ForecastSeries).filter_by(id=forecastseries_id)).\
                scalar_one_or_none()
            if not forecastseries:
                typer.echo("The forecastseries does not exist")
                raise typer.Exit()
            if not force:
                delete = typer.confirm(
                    "Are you sure you want to delete the "
                    f"forecastseries with id: {forecastseries_id}")
                if not delete:
                    typer.echo("Not deleting")
                    raise typer.Abort()

            session.delete(forecastseries)
            session.commit()
            typer.echo(f"Finished deleting forecast {forecastseries_id}")


@app.command()
def create(
        config: Path = typer.Option(
        ...,
        exists=True,
        readable=True),
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
            typer.echo(f"Project id {project_id} does not exist")
            raise typer.Exit()

        with open(config, "r") as forecastseries_json:
            config_dict = json.load(forecastseries_json)
        new_forecastseries = []
        for forecastseries_config in config_dict["forecastseries_configs"]:
            forecastseries = ForecastSeriesConfigurationSchema(
                unknown=EXCLUDE, context={"session": session}).\
                load(forecastseries_config)
            forecastseries.project = project
            new_forecastseries.append(forecastseries)
            session.add(forecastseries)
            session.commit()

        session.commit()
        for forecastseries in new_forecastseries:
            typer.echo(f"created forecastseries: {forecastseries.name} "
                       f"with id: {forecastseries.id} under project: "
                       f"{project.name}, with id: {project.id}"
                       f" with tags: {forecastseries.tags}")
