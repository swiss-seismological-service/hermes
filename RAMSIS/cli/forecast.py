from typing import List
from rich import print
from rich.table import Table
import asyncio
import typer
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import defer
from ramsis.datamodel import Forecast, EStatus
from RAMSIS.db import db_url, session_handler
from RAMSIS.cli.utils import flow_deployment_rerun_forecast, \
    add_new_scheduled_run_rerun_forecast
from RAMSIS.utils import reset_forecast
from RAMSIS.flows.forecast import ramsis_flow


app = typer.Typer()


@app.command()
def rerun(forecast_ids: List[int],
          delay: int = typer.Option(
              120, help="number of seconds to schedule "
              "the reruns apart"),
          force: bool = typer.Option(
              False, help="Force the forecast to run again, "
              "even if completed.")):
    flow_to_schedule = ramsis_flow
    add_delay = 0.0
    with session_handler(db_url) as session:
        for forecast_id in forecast_ids:
            forecast = session.execute(
                select(Forecast).filter_by(id=forecast_id)).\
                scalar_one_or_none()
            if not forecast:
                print("The forecast id does not exist")
                continue
            if force:
                print("Resetting RAMSIS statuses")
                forecast = reset_forecast(forecast)
                session.commit()
            else:
                typer.Exit()

            if forecast.status == EStatus.COMPLETED:
                print("forecast is already complete")
                if force:
                    print("forecast will have status reset")
                    forecast = reset_forecast(forecast)
                    session.commit()
                else:
                    typer.Exit()
            deployment_name = f"forecast_{forecast_id}"
            _ = flow_deployment_rerun_forecast(
                flow_to_schedule, deployment_name,
                None, forecast_id, db_url)

            asyncio.run(
                add_new_scheduled_run_rerun_forecast(
                    flow_to_schedule.name, deployment_name,
                    forecast.starttime,
                    datetime.utcnow() + timedelta(seconds=add_delay),
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
                print("The forecast does not exist")
                raise typer.Exit()
            if not force:
                delete = typer.confirm("Are you sure you want to delete the  "
                                       f"forecast with id: {forecast_id}?")
                if not delete:
                    print("Not deleting")
                    raise typer.Abort()

            session.delete(forecast)
            session.commit()
            print(f"Finished deleting forecast {forecast_id}")


@app.command()
def ls(forecast_id: int = typer.Option(
        None, help="Option to view information on one forecast"),
        full: bool = typer.Option(
        False, help="Give all info on forecasts."),
        help="Outputs list of forecasts"):
    with session_handler(db_url) as session:
        if forecast_id:

            forecasts = session.execute(
                select(Forecast).filter_by(id=forecast_id).
                options(defer(Forecast.seismiccatalog),
                        defer(Forecast.injectionwell)).order_by(
                    Forecast.forecastseries_id)).scalars().all()
        else:
            forecasts = session.execute(
                select(Forecast).options(defer(Forecast.seismiccatalog),
                                         defer(Forecast.injectionwell)).
                order_by(
                    Forecast.forecastseries_id)).scalars().all()
        for forecast in forecasts:
            table = Table(show_footer=False,
                          title_justify="left")
            table.add_column("attribute")
            table.add_column("value")
            for attr in Forecast.__table__.columns:
                if str(attr.name) not in ['seismiccatalog', 'injectionwell']:
                    if not full and str(attr.name) not in \
                            ['id', 'status', 'starttime', 'endtime']:
                        continue
                    table.add_row(str(attr.name),
                                  str(getattr(forecast, attr.name)))

            print(table)
