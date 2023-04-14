from typing import List
import asyncio
import typer
import json
from dateutil.rrule import rrule, SECONDLY
from prefect.orion.schemas.schedules import RRuleSchedule
from marshmallow import EXCLUDE
from datetime import timedelta, datetime
from sqlalchemy import select
from ramsis.datamodel import ForecastSeries, Project
from ramsis.io.configuration import ForecastSeriesConfigurationSchema
from RAMSIS.db import db_url, session_handler
from RAMSIS.cli.utils import flow_deployment, add_new_scheduled_run
from pathlib import Path
from RAMSIS.flows.forecast import scheduled_ramsis_flow


app = typer.Typer()


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
def schedule(forecastseries_id: int):
    flow_to_schedule = scheduled_ramsis_flow
    with session_handler(db_url) as session:
        forecastseries = session.execute(
            select(ForecastSeries).filter_by(id=forecastseries_id)).\
            scalar_one_or_none()
        if not forecastseries:
            typer.echo("The forecastseries id does not exist")
            raise typer.Exit()

        forecasts = forecastseries.forecasts
        if forecasts:
            typer.echo("Forecasts exist, please reset forecastseries or "
                       "create a new one.")
            typer.Exit()
        deployment_name = f"forecastseries_{forecastseries_id}"
        rrule_obj = rrule(
            freq=SECONDLY, interval=forecastseries.forecastinterval,
            dtstart=forecastseries.starttime, until=forecastseries.endtime)
        rrule_str = str(rrule_obj)
        rrule_schedule = RRuleSchedule(rrule=rrule_str)
        deployment = flow_deployment(flow_to_schedule, deployment_name,
                                     rrule_schedule)
        # Check for runs that were scheduled in the past and
        # will therefore not run
        scheduled_wait_time = 0
        interval = 60
        datetime_now = datetime.utcnow()
        typer.echo(list(rrule_obj))
        for forecast_starttime in list(rrule_obj):
            if forecast_starttime <= datetime_now:
                scheduled_start_time = datetime_now + timedelta(
                    seconds=scheduled_wait_time)
                typer.echo("running async function")
                asyncio.run(
                    add_new_scheduled_run(
                        flow_to_schedule.name, deployment.name,
                        forecast_starttime, scheduled_start_time,
                        forecastseries.id, db_url))
                scheduled_wait_time += interval


#@app.command()
#def clone(forecast_id: int,
#          interval: int = typer.Argument(
#              ..., help="Interval in seconds between forecasts."),
#          clone_number: int = typer.Argument(
#              ..., help="Number of forecast clones to create."),
#          ):
#
#    with session_handler(db_url) as session:
#        forecast = session.execute(
#            select(Forecast).filter_by(id=forecast_id)).scalar_one_or_none()
#        if not forecast:
#            typer.echo("The forecast id does not exist")
#            raise typer.Exit()
#
#        new_forecasts = []
#
#        typer.echo(f"Forecasts being cloned from id: {forecast_id} "
#                   f"which has starttime: {forecast.starttime}")
#        project_settings = forecast.project.settings.config
#        # If some input data is attached to the forecast rather
#        # than being received from a webservice, this must also
#        # be cloned. with_results=True only copies input data over.
#        if not project_settings['hydws_url'] or not \
#                project_settings['fdsnws_url']:
#            with_results = True
#        else:
#            with_results = False
#        for i in range(1, clone_number + 1):
#            cloned = forecast.clone(with_results=with_results)
#            cloned.starttime = (
#                forecast.starttime + timedelta(
#                    seconds=interval * i))
#            if cloned.starttime >= cloned.endtime:
#                typer.echo("Some forecast startimes exceed the endtime, "
#                           "so they will not be created.")
#                break
#
#            cloned.project_id = forecast.project_id
#            cloned = reset_forecast(cloned)
#            session.add(cloned)
#            new_forecasts.append(cloned)
#
#        session.commit()
#        for new_forecast in new_forecasts:
#            new_forecast.name = f"Forecast {new_forecast.id}"
#            forecast_duration = (new_forecast.endtime - new_forecast.starttime).total_seconds()
#            for scenario in new_forecast.scenarios:
#                seismicity_stage = scenario[EStage.SEISMICITY]
#                if seismicity_stage.config["epoch_duration"] > forecast_duration:
#                    seismicity_stage.config["epoch_duration"] = forecast_duration
#        session.commit()
#        for forecast in new_forecasts:
#            typer.echo(f"New forecast initialized with id: {forecast.id} "
#                       f"and starttime: {forecast.starttime}")
#        typer.echo(f"{len(new_forecasts)} Forecasts added successfully.")


@app.command()
def delete(forecastseries_ids: List[int],
            force: bool = typer.Option(
                False, help="Force the deletes without asking")):
    with session_handler(db_url) as session:
        for forecastseries_id in forecastseries_ids:
            forecastseries = session.execute(
                select(ForecastSeries).filter_by(id=forecastseries_id)).scalar_one_or_none()
            if not forecastseries:
                typer.echo("The forecastseries does not exist")
                raise typer.Exit()
            if not force:
                delete = typer.confirm("Are you sure you want to delete the  "
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
        project_id: int = typer.Option(None, help=
            "Project id to associate the forecast series to. If not"
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
        merge_items = []
        for forecastseries_config in config_dict["forecastseries_configs"]:
            forecastseries = ForecastSeriesConfigurationSchema(
                    unknown=EXCLUDE, context={"session":session}).load(forecastseries_config)
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
