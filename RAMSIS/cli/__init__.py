import typer
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from RAMSIS.cli import project, model, forecastseries, forecast as _forecast
from RAMSIS.db import session_handler, db_url, app_settings
from ramsis.datamodel import Forecast, Project, EStatus
#from RAMSIS.flows import ramsis_flow
from RAMSIS.cli.utils import add_new_scheduled_run, flow_deployment, \
    delete_scheduled_flow_runs, bulk_delete_flow_runs
from RAMSIS.flows.forecast import scheduled_ramsis_flow
from prefect.server.schemas.schedules import CronSchedule

ramsis_app = typer.Typer()
ramsis_app.add_typer(_forecast.app, name="forecast")
ramsis_app.add_typer(forecastseries.app, name="forecastseries")
ramsis_app.add_typer(model.app, name="model")
ramsis_app.add_typer(project.app, name="project")


@ramsis_app.command()
def delete_scheduled_flow_runs():
    asyncio.run(bulk_delete_flow_runs(state=["Scheduled"]))

@ramsis_app.command()
def delete_incomplete_flow_runs():
    # all states except for Scheduled and Completed
    states = ['Late',
              'AwaitingRetry',
              'Pending',
              'Running',
              'Retrying',
              'Paused',
              'Cancelled',
              'Failed',
              'Crashed']
    asyncio.run(bulk_delete_flow_runs(states=states))

@ramsis_app.command()
def delete_all_flow_runs():
    # all states
    states = ['Scheduled',
              'Late',
              'AwaitingRetry',
              'Pending',
              'Running',
              'Retrying',
              'Paused',
              'Cancelled',
              'Completed',
              'Failed',
              'Crashed']
    asyncio.run(bulk_delete_flow_runs(states=states))

def main():
    ramsis_app()
