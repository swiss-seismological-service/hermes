
import typer

from prefect.tasks.prefect import create_flow_run, wait_for_flow_run, get_task_run_result
from datetime import datetime, timedelta
from RAMSIS.flows.register import register_project, register_flows, \
    get_client, prefect_project_name

def schedule_forecast(forecast, client, dry_run=False):
    if forecast.starttime < datetime.utcnow():
        scheduled_time = datetime.utcnow()
        typer.echo(f"Forecast {forecast.id} is due to run in the past. "
                   "Scheduled to run as soon as possible.")
    else:
        scheduled_time = forecast.starttime
    parameters = dict(forecast_id=forecast.id)
    if not dry_run:
        flow_run_id = create_flow_run.run(
            project_name=prefect_project_name,
            flow_name="Manager",
            labels=["main-flow"],
            run_name=f"forecast_run_{forecast.id}",
            scheduled_start_time=scheduled_time,
            idempotency_key=f"forecast_run_{forecast.id}",
            parameters=parameters)

    typer.echo(f"Forecast {forecast.id} has been scheduled to run at {scheduled_time} with name forecast_run_{forecast.id}")
