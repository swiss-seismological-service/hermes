import typer
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from RAMSIS.cli import project, model, forecast as _forecast
from RAMSIS.db import session_handler, db_url, app_settings
from ramsis.datamodel import Forecast, Project, EStatus
from RAMSIS.flows import ramsis_flow
from RAMSIS.cli.utils import add_new_scheduled_run, flow_deployment, \
    delete_scheduled_flow_runs
from RAMSIS.flows import scheduled_ramsis_flow
from prefect.server.schemas.schedules import CronSchedule

ramsis_app = typer.Typer()
ramsis_app.add_typer(_forecast.app, name="forecast")
ramsis_app.add_typer(model.app, name="model")
ramsis_app.add_typer(project.app, name="project")


@ramsis_app.command()
def run(project_id: int = typer.Option(
        ..., help="Project id to search for forecasts when scheduling."),
        dry_run: bool = typer.Option(
            False, help="Show what forecasts would be scheduled and when."),
        interval: int = typer.Option(
            0, help="Interval to wait (seconds) between scheduled forecasts "
            "in the case that the forecasts are in the past."
            " This would help in the case where too many forecasts "
            "run at the same time would overload the system.")
        ):
    flow_to_schedule = ramsis_flow
    datetime_now = datetime.utcnow()
    typer.echo(f"Scheduling forecasts for project id {project_id}.")
    non_scheduling_statuses = [EStatus.ERROR, EStatus.COMPLETE, EStatus.RUNNING]
    with session_handler(db_url) as session:

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
            forecasts_to_schedule = [f for f in forecasts if f.status.state not in
                    non_scheduling_statuses]
            typer.echo(f"{len(forecasts_to_schedule)} forecasts found to schedule")

        data_dir = app_settings['data_dir']
        deployment_name = datetime_now.strftime("%y-%d-%mT%H:%M:%S")
        deployment = flow_deployment(
            flow_to_schedule, deployment_name)

        scheduled_wait_time = 0
        for forecast in forecasts:
            if forecast.status.state not in non_scheduling_statuses:
                forecast_start_time = forecast.starttime
                if forecast_start_time <= datetime_now:
                    forecast_start_time = datetime_now + timedelta(seconds=scheduled_wait_time)
                    scheduled_wait_time += interval
                typer.echo(f"running forecast {forecast.id} at time {forecast_start_time}")
                # run the deployment now through the agent.
                asyncio.run(
                    add_new_scheduled_run(
                        flow_to_schedule.name, deployment.name,
                        forecast_start_time, forecast.id, db_url, data_dir))
                #schedule_deployment(deployment.name, flow_to_schedule.name,
                #             forecast.id, scheduled_datetime, db_url)


@ramsis_app.command()
def stop():
    # TODO add project-id parameter, and also search for flow runs
    # that have the same prefix (or maybe label) so that if there
    # are multiple users, their runs will not be affected.

    # Manager is the scheduling flow that then triggers
    # the ramsis engine flow which does the main work.
    asyncio.run(
        delete_scheduled_flow_runs())



@ramsis_app.command()
def schedule(forecast_id: int,
             cron_string: str = typer.Argument(
                 ..., help="cron string for the forecast to be "
                 "scheduled, e.g. '0 9 * * *' is every day at 9am.")
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
    cron_clock = CronSchedule(cron=cron_string)
    deployment = flow_deployment(
        scheduled_ramsis_flow, f"scheduled_flow{cron_string}",
        schedule=[cron_clock])
    # scheduled_manager_flow.visualize()
    # scheduled_manager_flow.run(
    #     parameters=dict(
    #         forecast_id=forecast_id,
    #         connection_string=db_url),
    #     run_on_schedule=True)
    scheduled_dates = asyncio.run(cron_clock.get_dates(5))
    typer.echo("The flow has been registered successfully."
               f"The next 5 flow will happen: {scheduled_dates}")


def main():
    ramsis_app()
