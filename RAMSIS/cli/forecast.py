import typer
import json
from datetime import timedelta
from sqlalchemy import select
from ramsis.datamodel import Forecast, Project, EStatus, EInput
from RAMSIS.db import store
from RAMSIS.flows.register import \
    get_client
from RAMSIS.cli.utils import schedule_forecast, get_idempotency_id, \
    reset_forecast
from pathlib import Path
from RAMSIS.cli.utils import create_forecast, create_flow_run_name, \
    matched_flow_run, get_flow_run_label, restart_flow_run


app = typer.Typer()


@app.command()
def run(forecast_id: int,
        force: bool = typer.Option(
            False, help="Force the forecast to run again, "
                        "even if completed."),
        label: str = typer.Option(
            ..., help="label to associate with an agent"),
        idempotency_id: str = typer.Option(
            ..., help="idempotency id that identifies a forecast"
            "run so the same run is only run once.")):
    session = store.session
    forecast = session.execute(
        select(Forecast).filter_by(id=forecast_id)).scalar_one_or_none()
    if not forecast:
        typer.echo("The forecast id does not exist")
        raise typer.Exit()
    else:
        typer.echo(f"forecast found: {forecast}")
    if not idempotency_id:
        # get default idempotency id if not provided
        idempotency_id = get_idempotency_id()
    flow_run_name = create_flow_run_name(idempotency_id, forecast.id)
    if not label:
        # get default label id if not provided
        label = get_flow_run_label()
    existing_flow_run = matched_flow_run(flow_run_name, label)

    if force:
        typer.echo("Resetting RAMSIS statuses")
        forecast = reset_forecast(forecast)
        store.save()
        if existing_flow_run:
            typer.echo("Restarting flow run")
            restart_flow_run(existing_flow_run['id'])
            store.close()
            typer.Exit()
    else:
        if existing_flow_run:
            typer.echo("A flow run exists with the same idempotency key  and"
                       "with the following information: {existing_flow_run}."
                       "To restart this, please use the --force option which"
                       "will reschedule tasks. Results will be overwritten.")
            store.close()
            typer.Exit()

    if forecast.status.state != EStatus.COMPLETE:
        client = get_client()
        schedule_forecast(forecast, client, flow_run_name, label)
    else:
        typer.echo("Forecast is already complete.")


@app.command()
def clone(forecast_id: int,
          interval: int = typer.Argument(
              ..., help="Interval in seconds between forecasts."),
          clone_number: int = typer.Argument(
              ..., help="Number of forecast clones to create."),
          ):

    session = store.session
    forecast = session.execute(
        select(Forecast).filter_by(id=forecast_id)).scalar_one_or_none()
    if not forecast:
        typer.echo("The forecast id does not exist")
        raise typer.Exit()

    new_forecasts = []

    typer.echo(f"Forecasts being cloned from id: {forecast_id} "
               f"which has starttime: {forecast.starttime}")
    for i in range(1, clone_number + 1):
        cloned = forecast.clone(with_results=False)
        cloned.starttime = (
            forecast.starttime + timedelta(
                seconds=interval * i))
        if cloned.starttime >= cloned.endtime:
            typer.echo("Some forecast startimes exceed the endtime, "
                       "so they will not be created.")
            break

        cloned.project_id = forecast.project_id
        cloned = reset_forecast(cloned)
        store.add(cloned)
        new_forecasts.append(cloned)

    store.save()
    for new_forecast in new_forecasts:
        new_forecast.name = f"Forecast {new_forecast.id}"
    store.save()
    for forecast in new_forecasts:
        typer.echo(f"New forecast initialized with id: {forecast.id} "
                   f"and starttime: {forecast.starttime}")
    typer.echo(f"{len(new_forecasts)} Forecasts added successfully.")
    store.close()


@app.command()
def delete(forecast_id: int):
    session = store.session
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

    store.delete(forecast)
    store.save()
    typer.echo("Finished deleting forecast")
    store.close()


@app.command()
def create(
        project_id: int = typer.Option(...),
        config: Path = typer.Option(
        ...,
        exists=True,
        readable=True),
        inj_plan_data: typer.FileBinaryRead = typer.Option(
        None, help="Path of file containing the "
        "injection plans. Required if the forecast is for induced seismicity"),
        hyd_data: typer.FileBinaryRead = typer.Option(
        None, help="Path of file containing the "
        "hydraulics for forecasts without using hydws, e.g. for replays."),
        catalog_data: typer.FileBinaryRead = typer.Option(
        None, help="Path of file containing the "
        "catalog for forecasts without using fdsnws, e.g. for replays.")):

    session = store.session
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
        elif project.settings.config['seismic_catalog'] == EInput.NOT_ALLOWED.name:
            typer.echo(
                "--catalog-data may not be added if SEISMIC_CATALOG "
                "is configured"
                " to be NOT ALLOWED in the project config.")
            raise typer.Exit()
    else:
        if project.settings.config['seismic_catalog'] == EInput.REQUIRED.name and \
                not project.settings.config['fdsnws_url']:
            typer.echo(
                "--catalog-data must be added if SEISMIC_CATALOG "
                "is configured"
                " to be REQUIRED in the project config.")
            raise typer.Exit()

    if inj_plan_data:
        if project.settings.config['scenario'] == EInput.NOT_ALLOWED.name:
            typer.echo(
                "--inj-plan-data may not be added if SCENARIO "
                "is configured"
                " to be NOT ALLOWED in the project config.")
            raise typer.Exit()
    else:
        if project.settings.config['scenario'] == EInput.REQUIRED.name:
            typer.echo(
                "--inj-plan-data must be added if SCENARIO "
                "is configured"
                " to be REQUIRED in the project config.")
            raise typer.Exit()

    with open(config, "r") as forecast_json:
        forecast_config_list = json.load(forecast_json)
    new_forecasts = []
    for forecast_config in forecast_config_list["FORECASTS"]:
        forecast = create_forecast(
            project, forecast_config, inj_plan_data,
            hyd_data, catalog_data)
        new_forecasts.append(forecast)
        project.forecasts.append(forecast)
    store.save()

    for forecast in new_forecasts:
        typer.echo(f"created forecast {forecast.name} "
                   f"with id: {forecast.id} under project "
                   f"{forecast.project.id}")

    store.close()
