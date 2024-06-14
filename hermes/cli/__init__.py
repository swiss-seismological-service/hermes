import asyncio
import json
from os.path import join
from pathlib import Path

import typer
from prefect.exceptions import ObjectNotFound
from ramsis.datamodel import Project
from ramsis.io.configuration import (MasterConfigurationSchema,
                                     ProjectConfigurationSchema)
from rich import print
from rich.table import Table
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError

from hermes.cli import forecast as _forecast
from hermes.cli import forecastseries, model, project
from hermes.cli.utils import (bulk_delete_flow_runs, limit_model_runs,
                              list_flow_runs_with_states,
                              read_limit_model_runs, remove_limit_model_runs)
from hermes.db import db_url, session_handler

ramsis_app = typer.Typer()
ramsis_app.add_typer(_forecast.app, name="forecast")
ramsis_app.add_typer(forecastseries.app, name="forecastseries")
ramsis_app.add_typer(model.app, name="model")
ramsis_app.add_typer(project.app, name="project")


@ramsis_app.command()
def list_scheduled_forecasts():
    runs = asyncio.run(list_flow_runs_with_states(["Scheduled"]))
    if not runs:
        print("No scheduled runs")
    else:
        print(runs[0].parameters)
        table = Table(show_footer=False,
                      title="Scheduled forecast runs",
                      title_justify="left")
        table.add_column("expected starttime")
        table.add_column("parameters")
        table.add_column("state type")
        for run in runs:
            table.add_row(str(run.expected_start_time),
                          json.dumps(run.parameters),
                          str(run.state_name))
        print(table)


@ramsis_app.command()
def delete_scheduled_flow_runs():
    asyncio.run(bulk_delete_flow_runs(states=["Scheduled"]))


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


@ramsis_app.command()
def create_all(
        directory: Path = typer.Option(
            ...,
            exists=True,
            readable=True),
        config: str = typer.Option(
            'config.json',
            help="name of the master config file within the directory "
            "that contains names of the various project, "
            "forecast series etc configurations."),
        delete_existing: bool = typer.Option(False)):

    # Needs a file in the directory called config.json what contains all
    # following information.
    with open(join(directory, config)) as m_config:
        json_config = json.load(m_config)
        master_config_dict = MasterConfigurationSchema().load(json_config)

    project_config = master_config_dict["project_config"]

    with open(join(directory, project_config)) as p_config:
        json_config = json.load(p_config)
        project_config_list = ProjectConfigurationSchema(many=True).\
            load(json_config["project_configs"])
    for project_config in project_config_list:
        project_name = project_config.name

        with session_handler(db_url) as session:

            try:
                matching_project = session.execute(
                    select(Project).where(
                        Project.name == project_name)).scalar_one_or_none()
            except ProgrammingError:
                # In the case where a db is not populated by tables yet.
                matching_project = False
            if matching_project:
                if delete_existing:
                    delete = typer.confirm(
                        "Are you sure you want to delete the  "
                        f"project with id: {matching_project.id}")
                    if not delete:
                        print("Not deleting")
                        raise typer.Abort()

                    session.delete(matching_project)
                    session.commit()
                else:
                    raise Exception(
                        "Project name: "
                        f"{matching_project.name} already exists "
                        f"with id: {matching_project.id}. Please set "
                        "delete-existing.")
        if 'catalog' in master_config_dict.keys():
            catalog_data = open(join(
                directory, master_config_dict['catalog']), 'r')
        else:
            catalog_data = None

        if 'wells' in master_config_dict.keys():
            wells = open(join(directory, master_config_dict['wells']), 'r')
        else:
            wells = None

        project.create(
            join(directory, master_config_dict['project_config']),
            catalog_data=catalog_data,
            well_data=wells)
        model.load(join(directory, master_config_dict['model_config']))

        new_project = session.execute(
            select(Project).where(
                Project.name == project_name)).scalar_one_or_none()

        forecastseries.create(
            join(directory, master_config_dict['forecastseries_config']),
            new_project.id)
    print("Complete")


@ramsis_app.command()
def update_model_run_concurrency(
        concurrency_limit: int,
        help=(
        "Set concurrency limit for the number of tasks running which either"
        " starts a model run or is polling for it. No new model runs should be"
        " started once the limit is reached. This stops too many model runs "
        " running at the same time and crashing in the case of high memory "
        "usage.")):
    asyncio.run(limit_model_runs(concurrency_limit))


@ramsis_app.command()
def remove_model_run_concurrency(
        help=(
        "Remove concurrency limit for the number of model runs "
        "being executed at the same time.")):
    asyncio.run(remove_limit_model_runs())


@ramsis_app.command()
def read_model_run_concurrency(
        help=(
        "Return concurrency limit for the number of model runs "
        "being executed at the same time.")):
    try:
        limit = asyncio.run(read_limit_model_runs())
        print(f"Limit: {limit.concurrency_limit}")
    except ObjectNotFound:
        print("No concurrency limit set.")


def main():
    ramsis_app()
