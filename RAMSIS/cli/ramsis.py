#import typer
#
#from ramsis.datamodel import Forecast, Project, EStatus
#from RAMSIS.flows.manager import manager_flow
#from datetime import datetime, timedelta
#from RAMSIS.db import store
#from RAMSIS.core.engine.engine import Engine
#from RAMSIS.flows.register import register_project, register_flows, \
#    get_client, prefect_project_name
#from prefect.tasks.prefect import create_flow_run, wait_for_flow_run, get_task_run_result
#from RAMSIS.cli import ramsis_app
#
##app = typer.Typer()
#
#ramsis_app = typer.Typer()
#
#def schedule_forecast(forecast, client, dry_run=False):
#    if forecast.starttime < datetime.utcnow():
#        scheduled_time = datetime.utcnow()
#        typer.echo(f"Forecast {forecast.id} is due to run in the past. "
#                   "Scheduled to run as soon as possible.")
#    else:
#        scheduled_time = forecast.starttime
#    parameters = dict(forecast_id=forecast.id)
#    if not dry_run:
#        flow_run_id = create_flow_run.run(
#            project_name=prefect_project_name,
#            flow_name="Manager",
#            labels=["main-flow"],
#            run_name=f"forecast_run_{forecast.id}",
#            scheduled_start_time=scheduled_time,
#            idempotency_key=f"forecast_run_{forecast.id}",
#            parameters=parameters)
#
#    typer.echo(f"Forecast {forecast.id} has been scheduled to run at {scheduled_time} with name forecast_run_{forecast.id}")
#
#@ramsis_app.command()
#def register():
#    register_flows(manager_flow)
#    register_project()
#    typer.echo("prefect has registered flows and project for ramsis.")
#
#@ramsis_app.command()
#def run(project_id: int = typer.Option(..., help="Project id to search for forecasts when scheduling."),
#        dry_run: bool = typer.Option(False, help="Show what forecasts would be scheduled and when.")
#        ):
#    typer.echo(f"Scheduling forecasts for project id {project_id} with prefect.")
#    session = store.session
#    # Check project_id exists
#    project_exists = session.query(Project).filter(Project.id==project_id).one_or_none()
#    if not project_exists:
#        typer.echo("The project id does not exist")
#        raise typer.Exit()
#
#    # get list of forecasts for scheduling
#    forecasts = session.query(Forecast).filter(
#            Forecast.project_id==project_id).all()
#    if not forecasts:
#        typer.echo("No forecasts exist that are in a non-complete state.")
#    client = get_client()
#    for forecast in forecasts:
#        if forecast.status.state != EStatus.COMPLETE:
#            schedule_forecast(forecast, client, dry_run=dry_run)
#
