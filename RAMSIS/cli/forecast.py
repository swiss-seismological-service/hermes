import typer
import json
from datetime import timedelta, datetime
from sqlalchemy import select
from ramsis.datamodel import Forecast, Project, EStatus, EInput, EStage
from RAMSIS.db import db_url, session_handler
from RAMSIS.cli.utils import flow_deployment, schedule_deployment
from RAMSIS.utils import reset_forecast
from pathlib import Path
from RAMSIS.cli.utils import create_forecast
from RAMSIS.flows import ramsis_flow


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
        # data_dir = app_settings['data_dir']
        deployment_name = f"forecast_{forecast_id}"
        deployment = flow_deployment(flow_to_schedule, deployment_name)
        # run the deployment now through the agent.
        schedule_deployment(deployment.name, flow_to_schedule.name,
                            forecast_id, datetime.utcnow(), db_url)


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
def delete(forecast_id: int):
    with session_handler(db_url) as session:
        forecast = session.execute(
            select(Forecast).filter_by(id=forecast_id)).scalar_one_or_none()
        if not forecast:
            typer.echo("The forecast does not exist")
            raise typer.Exit()
        delete = typer.confirm("Are you sure you want to delete the  "
                               f"forecast with id: {forecast_id}")
        if not delete:
            typer.echo("Not deleting")
            raise typer.Abort()

        session.delete(forecast)
        session.commit()
        typer.echo("Finished deleting forecast")


# TODO add check to seismicity and hazard stage that configured properly.
@app.command()
def create(
        project_id: int = typer.Option(...),
        config: Path = typer.Option(
        ...,
        exists=True,
        readable=True),
        inj_plan_directory: str = typer.Option(
        None, help="Path of directory containing the "
        "injection plans. Required if the forecast is for induced seismicity"),
        hyd_data: typer.FileBinaryRead = typer.Option(
        None, help="Path of file containing the "
        "hydraulics for forecasts without using hydws, e.g. for replays."),
        catalog_data: typer.FileBinaryRead = typer.Option(
        None, help="Path of file containing the "
        "catalog for forecasts without using fdsnws, e.g. for replays.")):

    with session_handler(db_url) as session:
        project = session.execute(
            select(Project).filter_by(id=project_id)).scalar_one_or_none()

        # Validataions
        if not project:
            typer.echo(f"Project id {project_id} does not exist")
            raise typer.Exit()
        if hyd_data:
            if project.settings.config['hydws_url']:
                typer.echo(
                    "--hyd-data may not be added if a HYDWS_URL"
                    " is configured in the project config.")
                raise typer.Exit()
            elif project.settings.config['well'] == EInput.NOT_ALLOWED.name:
                typer.echo(
                    "--hyd-data may not be added if WELL is configured"
                    " to be NOT ALLOWED in the project config.")
                raise typer.Exit()
        else:
            if project.settings.config['well'] == EInput.REQUIRED.name and \
                    not project.settings.config['hydws_url']:
                typer.echo(
                    "--hyd-data must be added if WELL "
                    "is configured"
                    " to be REQUIRED in the project config.")
                raise typer.Exit()

        if catalog_data:
            if project.settings.config['fdsnws_url']:
                typer.echo(
                    "--catalog-data may not be added if a FDSNWS_URL"
                    " is configured in the project config.")
                raise typer.Exit()
            elif project.settings.config['seismic_catalog'] == \
                    EInput.NOT_ALLOWED.name:
                typer.echo(
                    "--catalog-data may not be added if SEISMIC_CATALOG "
                    "is configured"
                    " to be NOT ALLOWED in the project config.")
                raise typer.Exit()
        else:
            if project.settings.config['seismic_catalog'] == \
                    EInput.REQUIRED.name and \
                    not project.settings.config['fdsnws_url']:
                typer.echo(
                    "--catalog-data must be added if SEISMIC_CATALOG "
                    "is configured"
                    " to be REQUIRED in the project config.")
                raise typer.Exit()

        if inj_plan_directory:
            if project.settings.config['scenario'] == EInput.NOT_ALLOWED.name:
                typer.echo(
                    "--inj-plan-directory may not be added if SCENARIO "
                    "is configured"
                    " to be NOT ALLOWED in the project config.")
                raise typer.Exit()
        else:
            if project.settings.config['scenario'] == EInput.REQUIRED.name:
                typer.echo(
                    "--inj-plan-directory must be added if SCENARIO "
                    "is configured"
                    " to be REQUIRED in the project config.")
                raise typer.Exit()

        with open(config, "r") as forecast_json:
            forecast_config_list = json.load(forecast_json)
        new_forecasts = []
        for forecast_config in forecast_config_list["FORECASTS"]:
            forecast = create_forecast(
                session, project, forecast_config, inj_plan_directory,
                hyd_data, catalog_data)
            new_forecasts.append(forecast)
            project.forecasts.append(forecast)
        session.commit

        for forecast in new_forecasts:
            typer.echo(f"created forecast {forecast.name} "
                       f"with id: {forecast.id} under project "
                       f"{forecast.project.id}")
