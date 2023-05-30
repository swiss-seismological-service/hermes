from typing import List
import asyncio
import typer
import json
from datetime import timedelta, datetime
from sqlalchemy import select
from ramsis.datamodel import Forecast, Project, EStatus, EInput
from RAMSIS.db import db_url, session_handler, app_settings
from RAMSIS.cli.utils import flow_deployment, schedule_deployment, add_new_scheduled_run
from RAMSIS.utils import reset_forecast
from pathlib import Path
from RAMSIS.flows.forecast import ramsis_flow


app = typer.Typer()


@app.command()
def rerun(forecast_id: int,
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
        data_dir = app_settings['data_dir']
        deployment_name = f"forecast_{forecast_id}"
        deployment = flow_deployment(flow_to_schedule, deployment_name)

        asyncio.run(
            add_new_scheduled_run(
                flow_to_schedule.name, deployment_name,
                datetime.utcnow(),
                forecast.id, db_url))


@app.command()
def delete(forecast_ids: List[int],
            force: bool = typer.Option(
                False, help="Force the deletes without asking")):
    with session_handler(db_url) as session:
        for forecast_id in forecast_ids:
            forecast = session.execute(
                select(Forecast).filter_by(id=forecast_id)).scalar_one_or_none()
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
