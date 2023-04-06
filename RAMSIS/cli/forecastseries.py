from typing import List
import asyncio
import typer
import json
from marshmallow import EXCLUDE
from datetime import timedelta, datetime
from sqlalchemy import select
from ramsis.datamodel import Forecast, Project, EStatus, Tag
from ramsis.io.configuration import ForecastSeriesConfigurationSchema
from RAMSIS.db import db_url, session_handler, app_settings
from RAMSIS.cli.utils import flow_deployment, add_new_scheduled_run
from pathlib import Path
from RAMSIS.flows.forecast import ramsis_flow


app = typer.Typer()


@app.command()
def run(forecast_id: int,
        force: bool = typer.Option(
            False, help="Force the forecast to run again, "
            "even if completed.")):
    flow_to_schedule = ramsis_flow
    with session_handler(db_url) as session:
        forecast = session.execute(
            select(Forecast).filter_by(id=forecast_id)).scalar_one_or_none()
        if not forecast:
            typer.echo("The forecast id does not exist")
            raise typer.Exit()
        if force:
            typer.echo("Resetting RAMSIS statuses")
            forecast = reset_forecast(forecast)
            session.commit()

        if forecast.status.state == EStatus.COMPLETE:
            typer.echo("forecast is already complete")
            if force:
                typer.echo("forecast will have status reset")
                forecast = reset_forecast(forecast)
                session.commit()
            else:
                typer.Exit()
        data_dir = app_settings['data_dir']
        deployment_name = f"forecast_{forecast_id}"
        deployment = flow_deployment(flow_to_schedule, deployment_name)
        # run the deployment now through the agent.
        #schedule_deployment(deployment.name, flow_to_schedule.name,
        #                    forecast_id, datetime.utcnow(), db_url, data_dir)
        asyncio.run(
            add_new_scheduled_run(
                flow_to_schedule.name, deployment.name,
                datetime.utcnow(), forecast.id, db_url, data_dir))


@app.command()
def clone(forecast_id: int,
          interval: int = typer.Argument(
              ..., help="Interval in seconds between forecasts."),
          clone_number: int = typer.Argument(
              ..., help="Number of forecast clones to create."),
          ):

    with session_handler(db_url) as session:
        forecast = session.execute(
            select(Forecast).filter_by(id=forecast_id)).scalar_one_or_none()
        if not forecast:
            typer.echo("The forecast id does not exist")
            raise typer.Exit()

        new_forecasts = []

        typer.echo(f"Forecasts being cloned from id: {forecast_id} "
                   f"which has starttime: {forecast.starttime}")
        project_settings = forecast.project.settings.config
        # If some input data is attached to the forecast rather
        # than being received from a webservice, this must also
        # be cloned. with_results=True only copies input data over.
        if not project_settings['hydws_url'] or not \
                project_settings['fdsnws_url']:
            with_results = True
        else:
            with_results = False
        for i in range(1, clone_number + 1):
            cloned = forecast.clone(with_results=with_results)
            cloned.starttime = (
                forecast.starttime + timedelta(
                    seconds=interval * i))
            if cloned.starttime >= cloned.endtime:
                typer.echo("Some forecast startimes exceed the endtime, "
                           "so they will not be created.")
                break

            cloned.project_id = forecast.project_id
            cloned = reset_forecast(cloned)
            session.add(cloned)
            new_forecasts.append(cloned)

        session.commit()
        for new_forecast in new_forecasts:
            new_forecast.name = f"Forecast {new_forecast.id}"
            forecast_duration = (new_forecast.endtime - new_forecast.starttime).total_seconds()
            for scenario in new_forecast.scenarios:
                seismicity_stage = scenario[EStage.SEISMICITY]
                if seismicity_stage.config["epoch_duration"] > forecast_duration:
                    seismicity_stage.config["epoch_duration"] = forecast_duration
        session.commit()
        for forecast in new_forecasts:
            typer.echo(f"New forecast initialized with id: {forecast.id} "
                       f"and starttime: {forecast.starttime}")
        typer.echo(f"{len(new_forecasts)} Forecasts added successfully.")


@app.command()
def delete(forecast_ids: List[int],
            force: bool = typer.Option(
                False, help="Force the deletes without asking")):
    with session_handler(db_url) as session:
        for forecast_id in forecast_ids:
            forecast = session.execute(
                select(Forecast).filter_by(id=forecast_id)).scalar_one_or_none()
            if not forecast:
                typer.echo("The forecast does not exist")
                raise typer.Exit()
            if not force:
                delete = typer.confirm("Are you sure you want to delete the  "
                                       f"forecast with id: {forecast_id}")
                if not delete:
                    typer.echo("Not deleting")
                    raise typer.Abort()

            session.delete(forecast)
            session.commit()
            typer.echo(f"Finished deleting forecast {forecast_id}")


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
        #tags = session.execute(
        #    select(Tag)).scalars()
        new_forecastseries = []
        merge_items = []
        for forecastseries_config in config_dict["forecastseries_configs"]:
            forecastseries = ForecastSeriesConfigurationSchema(
                    unknown=EXCLUDE, context={"session":session}).load(forecastseries_config)
            #session.add(forecastseries)
            #merge_items.append(forecastseries)
            new_forecastseries.append(forecastseries)
            print(dir(project))
            ##project.forecastseries.append(forecastseries)
            #for tag in forecastseries.tags:
            #    print("before tag meerge", session.new, session.dirty, session.deleted)
            #    print(tag.name)
            #    #print(tag.__dict__)
            #    session.merge(tag)
            #    print("after tag meerge", session.new, session.dirty, session.deleted)
            #    #merge_items.append(tag)

            #for item in merge_items:
            #    session.merge(item)
            
            #print(session.new, session.dirty, session.deleted)
            session.add(forecastseries)
            #print(session.new, session.dirty, session.deleted)
            print(forecastseries.tags)
            session.commit()
            print(forecastseries.tags)
            #session.merge(forecastseries)

        session.commit()
        for forecastseries in new_forecastseries:
            typer.echo(f"created forecastseries: {forecastseries.name} "
                       f"with id: {forecastseries.id} under project: "
                       f"{project.name}, with id: {project.id}"
                       f" with tags: {forecastseries.tags}")
