import typer
from RAMSIS.cli import project, model, engine, forecast as _forecast
import logging
from ramsis.datamodel import Forecast, Project, EStatus
from RAMSIS.flows.manager import manager_flow, manager_flow_name
from RAMSIS.db import store
from RAMSIS.flows.register import register_project, register_flows, \
    get_client
from RAMSIS.cli.utils import schedule_forecast, get_idempotency_id, \
    cancel_flow_run, scheduled_flow_runs
from prefect.utilities.logging import prefect_logger

ramsis_app = typer.Typer()
# engine to be removed after migrated to full use of prefect
ramsis_app.add_typer(engine.app, name="engine")
ramsis_app.add_typer(_forecast.app, name="forecast")
ramsis_app.add_typer(model.app, name="model")
ramsis_app.add_typer(project.app, name="project")


@ramsis_app.command()
def register():
    register_flows(manager_flow)
    register_project()
    typer.echo("prefect has registered flows and project for ramsis.")


@ramsis_app.command()
def run(project_id: int = typer.Option(
        ..., help="Project id to search for forecasts when scheduling."),
        dry_run: bool = typer.Option(
            False, help="Show what forecasts would be scheduled and when.")
        ):
    typer.echo(f"Scheduling forecasts for project id {project_id}.")
    session = store.session
    # Check project_id exists
    project_exists = session.query(Project).filter(Project.id == project_id).\
        one_or_none()
    if not project_exists:
        typer.echo("The project id does not exist")
        raise typer.Exit()

    forecasts = session.query(Forecast).filter(
        Forecast.project_id == project_id).all()
    print("forecasts", forecasts)
    if not forecasts:
        typer.echo("No forecasts exist that are in a non-complete state.")
    client = get_client()
    idempotency_id = get_idempotency_id()
    for forecast in forecasts:
        if forecast.status.state != EStatus.COMPLETE:
            typer.echo(
                f"Forecast: {forecast.id} is being scheduled.")
            schedule_forecast(forecast, client, idempotency_id=idempotency_id,
                              dry_run=dry_run)


@ramsis_app.command()
def stop():
    # TODO add project-id parameter, and also search for flow runs
    # that have the same prefix (or maybe label) so that if there
    # are multiple users, their runs will not be affected.

    # Manager is the scheduling flow that then triggers
    # the ramsis engine flow which does the main work.
    flow_runs = scheduled_flow_runs(manager_flow_name)
    typer.echo(f"There are {len(flow_runs)} flow runs scheduled.")
    for flow_run in flow_runs:
        cancel_flow_run(flow_run["id"],
                        msg="RAMSIS has been stopped, all currently "
                        "scheduled flow runs cancelled.")
        typer.echo(f"Flow run with id: {flow_run['id']} with "
                   f"name: {flow_run['name']} has been cancelled.")


def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('RAMSIS')
    prefect_logger = logger
    ramsis_app()
