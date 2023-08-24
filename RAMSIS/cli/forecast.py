from typing import List
import asyncio
import typer
from datetime import datetime
from sqlalchemy import select
from ramsis.datamodel import Forecast, EStatus
from RAMSIS.db import db_url, session_handler
from RAMSIS.cli.utils import flow_deployment_rerun_forecast, \
    add_new_scheduled_run_rerun_forecast
from RAMSIS.utils import reset_forecast
from RAMSIS.flows.forecast import ramsis_flow


app = typer.Typer()


@app.command()
def rerun(forecast_ids: List[int],
        delay: int = typer.Option(120,
            help="number of seconds to schedule the reruns apart"),
        force: bool = typer.Option(
            False, help="Force the forecast to run again, "
            "even if completed.")):
    flow_to_schedule = ramsis_flow
    add_delay = 0.0
    with session_handler(db_url) as session:
        for forecast_id in forecast_ids:
            forecast = session.execute(
                select(Forecast).filter_by(id=forecast_id)).scalar_one_or_none()
            if not forecast:
                typer.echo("The forecast id does not exist")
                continue
            if force:
                typer.echo("Resetting RAMSIS statuses")
                forecast = reset_forecast(forecast)
                session.commit()
            else:
                typer.Exit()

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
            deployment = flow_deployment_rerun_forecast(flow_to_schedule, deployment_name, None, forecast_id, db_url)

            asyncio.run(
                add_new_scheduled_run_rerun_forecast(
                    flow_to_schedule.name, deployment_name,
                    forecast.starttime,
                    datetime.utcnow()+timedelta(seconds=add_delay),
                    forecast.id, db_url))
            add_delay += delay


@app.command()
def delete(forecast_ids: List[int],
           force: bool = typer.Option(
           False, help="Force the deletes without asking")):
    with session_handler(db_url) as session:
        for forecast_id in forecast_ids:
            forecast = session.execute(
                select(Forecast).filter_by(id=forecast_id)).\
                scalar_one_or_none()
            if not forecast:
                typer.echo("The forecast does not exist")
                raise typer.Exit()
            if not force:
                delete = typer.confirm("Are you sure you want to delete the  "
                                       f"forecast with id: {forecast_id}?")
                if not delete:
                    typer.echo("Not deleting")
                    raise typer.Abort()

            session.delete(forecast)
            session.commit()
            typer.echo(f"Finished deleting forecast {forecast_id}")
