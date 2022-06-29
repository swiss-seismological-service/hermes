import typer
from RAMSIS.cli import engine, forecast as _forecast
import logging
from ramsis.datamodel import Forecast, Project, EStatus
from RAMSIS.flows.manager import manager_flow
from datetime import datetime, timedelta
from RAMSIS.db import store
from RAMSIS.core.engine.engine import Engine
from RAMSIS.flows.register import register_project, register_flows, \
    get_client, prefect_project_name
from prefect.tasks.prefect import create_flow_run, wait_for_flow_run, get_task_run_result
from RAMSIS.cli.utils import schedule_forecast, get_idempotency_id

ramsis_app = typer.Typer()
# engine to be removed after migrated to full use of prefect
ramsis_app.add_typer(engine.app, name="engine")
ramsis_app.add_typer(_forecast.app, name="forecast")




@ramsis_app.command()
def register():
    register_flows(manager_flow)
    register_project()
    typer.echo("prefect has registered flows and project for ramsis.")

@ramsis_app.command()
def run(project_id: int = typer.Option(..., help="Project id to search for forecasts when scheduling."),
        dry_run: bool = typer.Option(False, help="Show what forecasts would be scheduled and when.")
        ):
    typer.echo(f"Scheduling forecasts for project id {project_id} with prefect.")
    session = store.session
    # Check project_id exists
    project_exists = session.query(Project).filter(Project.id==project_id).one_or_none()
    if not project_exists:
        typer.echo("The project id does not exist")
        raise typer.Exit()

    forecasts_test = session.query(Forecast).all()
    print(forecasts_test, [f.project_id for f in forecasts_test])
    # get list of forecasts for scheduling
    forecasts = session.query(Forecast).filter(
            Forecast.project_id==project_id).all()
    print("forecasts", forecasts)
    if not forecasts:
        typer.echo("No forecasts exist that are in a non-complete state.")
    client = get_client()
    idempotency_id = get_idempotency_id()
    for forecast in forecasts:
        if forecast.status.state != EStatus.COMPLETE:
            typer.echo(
                f"Forecast: {forecast.id} is being scheduled.")
            schedule_forecast(forecast, client,idempotency_id=idempotency_id, dry_run=dry_run)


def main():
    logging.basicConfig(level=logging.INFO)
    ramsis_app()
