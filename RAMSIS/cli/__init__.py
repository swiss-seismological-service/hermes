import typer
from datetime import datetime
from sqlalchemy import select
from RAMSIS.cli import project, model, engine, forecast as _forecast
from ramsis.datamodel import Forecast, Project, EStatus
from RAMSIS.flows.manager import manager_flow, manager_flow_name
from RAMSIS.flows.hazard import hazard_flow
from RAMSIS.flows.seismicity import seismicity_flow
from RAMSIS.db import store, app_settings, db_url
from RAMSIS.flows.register import register_project, register_flows, \
    get_client
from RAMSIS.cli.utils import schedule_forecast, \
    cancel_flow_run, scheduled_flow_runs, get_flow_run_label, \
    create_flow_run_name
from RAMSIS.flows.scheduled_manager import scheduled_manager_flow_factory
from prefect.schedules.clocks import CronClock
from prefect.schedules.schedules import Schedule

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

    register_project()
    register_flows(seismicity_flow, [label])
    register_flows(hazard_flow, [label])
    register_flows(manager_flow, [label])
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

    connection_string = db_url
    data_dir = app_settings['data_dir']

    scheduled_wait_time = 0
    for forecast in forecasts:
        if forecast.status.state != EStatus.COMPLETE:
            flow_run_name = create_flow_run_name(idempotency_key, forecast.id)
            typer.echo(
                f"Forecast: {forecast.id} is being scheduled.")
            schedule_forecast(forecast, client, flow_run_name, label,
                              connection_string, data_dir,
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


@ramsis_app.command()
def schedule(forecast_id: int,
             label: str = typer.Option(
                 None, help="label to associate with all runs from this "
                 "cron clock. Label links flow runs with a prefect agent."),
             cron_string: str = typer.Argument(
                 ..., help="cron string for the forecast to be "
                 "scheduled, e.g. '0 9 * * *' is every day at 9am."),
             start_date: datetime = typer.Option(
                 None, help="Optional start date for the clock"),
             end_date: datetime = typer.Option(
                 None, help="Optional start date for the clock")
             ):
    """
    Schedule the scheduled manager flow according to a cron
    schedule.
    """
    session = store.session
    forecast = session.execute(
        select(Forecast).filter_by(id=forecast_id)).scalar_one_or_none()
    if not forecast:
        typer.echo("The forecast id does not exist")
        raise typer.Exit()
    if not label:
        # get default label id if not provided
        label = get_flow_run_label()
    cron_clock = CronClock(cron_string, start_date=start_date,
                           end_date=end_date,
                           labels=[label])
    schedule = Schedule(clocks=[cron_clock])
    scheduled_manager_flow_name = f"{label}ScheduledManager"
    scheduled_manager_flow = scheduled_manager_flow_factory(
        scheduled_manager_flow_name, schedule, forecast_id, db_url)
    register_flows(scheduled_manager_flow, [label])
    # scheduled_manager_flow.visualize()
    # scheduled_manager_flow.run(
    #     parameters=dict(
    #         forecast_id=forecast_id,
    #         connection_string=db_url),
    #     run_on_schedule=True)
    typer.echo("The flow has been registered successfully."
               f"The next 5 flow will happen: {schedule.next(5)}")


def main():
    ramsis_app()
