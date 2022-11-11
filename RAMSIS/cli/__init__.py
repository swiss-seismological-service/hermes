import typer
from sqlalchemy import select
from RAMSIS.cli import project, model, engine, forecast as _forecast
from ramsis.datamodel import Forecast, Project, EStatus
from RAMSIS.flows.manager import manager_flow, manager_flow_name
from RAMSIS.db import store
from RAMSIS.flows.register import register_project, register_flows, \
    get_client
from RAMSIS.cli.utils import schedule_forecast, \
    cancel_flow_run, scheduled_flow_runs, get_flow_run_label, \
    create_flow_run_name

ramsis_app = typer.Typer()
# engine to be removed after migrated to full use of prefect
ramsis_app.add_typer(engine.app, name="engine")
ramsis_app.add_typer(_forecast.app, name="forecast")
ramsis_app.add_typer(model.app, name="model")
ramsis_app.add_typer(project.app, name="project")


@ramsis_app.command()
def register(label: str = typer.Option(
             None, help="label to associate with a prefect agent")):

    if not label:
        label = get_flow_run_label()

    register_flows(manager_flow, [label])
    register_project()
    typer.echo("prefect has registered flows and project for ramsis.")


@ramsis_app.command()
def run(project_id: int = typer.Option(
        ..., help="Project id to search for forecasts when scheduling."),
        dry_run: bool = typer.Option(
            False, help="Show what forecasts would be scheduled and when."),
        label: str = typer.Option(
            None, help="label to associate with an agent"),
        interval: int = typer.Option(
            0, help="Interval to wait (seconds) between scheduled forecasts "
            "in the case that the forecasts are in the past."
            " This would help in the case where too many forecasts "
            "run at the same time would overload the system."),
        idempotency_key: str = typer.Option(
            "", help="Key that is used by the prefect cloud "
            "to avoid rerunning forecasts that have already been"
            " scheduled.")
        ):
    typer.echo(f"Scheduling forecasts for project id {project_id}.")
    session = store.session

    project = session.execute(
        select(Project).filter_by(id=project_id)).scalar_one_or_none()
    if not project:
        typer.echo("The project id does not exist")
        raise typer.Exit()

    forecasts = session.execute(
        select(Forecast).filter_by(project_id=project_id)).scalars().all()
    if not forecasts:
        typer.echo("No forecasts exist that are in a non-complete state.")
    else:
        typer.echo(f"{len(forecasts)} found to schedule")
    client = get_client()

    if not label:
        label = get_flow_run_label()

    scheduled_wait_time = 0
    for forecast in forecasts:
        if forecast.status.state != EStatus.COMPLETE:
            flow_run_name = create_flow_run_name(idempotency_key, forecast.id)
            typer.echo(
                f"Forecast: {forecast.id} is being scheduled.")
            schedule_forecast(forecast, client, flow_run_name, label,
                              idempotency_key=idempotency_key, dry_run=dry_run,
                              scheduled_wait_time=scheduled_wait_time)
            scheduled_wait_time += interval


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
    ramsis_app()
