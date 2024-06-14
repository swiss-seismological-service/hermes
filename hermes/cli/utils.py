from datetime import datetime

import typer
from prefect.client import get_client
# from prefect.server.api.deployments import set_schedule_inactive \
#     as deployment_set_schedule_inactive
from prefect.deployments import Deployment, run_deployment
from prefect.server.schemas.filters import (DeploymentFilter, FlowFilter,
                                            FlowRunFilter, FlowRunFilterState,
                                            FlowRunFilterStateName)
from prefect.server.schemas.states import Scheduled

from hermes.db import app_settings

# All hyd, seismic data is expected in this projection
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


def get_deployment_name(forecastseries_id):
    return f"forecastseries_{forecastseries_id}"


# check for a deployment with the same name as <ramsis_flow_name>/forecast_<id>
def flow_deployment_rerun_forecast(flow, deployment_name,
                                   schedule, forecast_id,
                                   db_url, work_queue_name="default",
                                   logging_level="INFO"):
    parameters = dict(
        forecast_id=forecast_id,
        connection_string=db_url)
    deployment = Deployment.build_from_flow(
        flow=flow,
        name=deployment_name,
        parameters=parameters,
        infra_overrides={"env": {"PREFECT_LOGGING_LEVEL": logging_level}},
        work_queue_name=work_queue_name,
        schedule=schedule,
        apply=True
    )
    return deployment


# check for a deployment with the same name as <ramsis_flow_name>/forecast_<id>
def flow_deployment(flow, deployment_name, schedule, forecastseries_id,
                    db_url, work_queue_name="default",
                    logging_level="INFO"):
    parameters = dict(
        forecastseries_id=forecastseries_id,
        connection_string=db_url)
    deployment = Deployment.build_from_flow(
        flow=flow,
        name=deployment_name,
        parameters=parameters,
        infra_overrides={"env": {"PREFECT_LOGGING_LEVEL": logging_level}},
        work_queue_name=work_queue_name,
        schedule=schedule,
        apply=True
    )
    return deployment


def get_idempotency_id():

    idempotency_id = ""
    try:
        idempotency_id = app_settings["idempotency_id"]
    except KeyError:
        typer.echo(
            "No idempotency_id set in config file - this could lead to "
            "problems if ramsis is run from multiple locations.")
    return idempotency_id


def get_flow_run_label():
    label = ''
    try:
        label = app_settings["label"]
    except KeyError:
        typer.echo(
            "No label set in config file - this could lead to "
            "problems as the prefect agent must have at least "
            "one label in common with the flow run.")
    return label


def create_flow_run_name(idempotency_id, forecast_id):
    return f"{idempotency_id}forecast_run_{forecast_id}"


def schedule_deployment(
        deployment_name, flow_name,
        forecastseries_id, forecast_starttime,
        db_url, data_dir):
    parameters = dict(
        forecastseries_id=forecastseries_id,
        connection_string=db_url)
    deployment_id = f"{flow_name}/{deployment_name}"
    run_deployment(deployment_id, scheduled_time=forecast_starttime,
                   parameters=parameters)


async def add_new_scheduled_run_rerun_forecast(
    flow_name: str, deployment_name: str,
    forecast_starttime: datetime, scheduled_starttime: datetime,
        forecast_id, db_url):
    parameters = dict(
        forecast_id=forecast_id,
        connection_string=db_url,
        date=forecast_starttime)
    async with get_client() as client:
        deployments = await client.read_deployments(
            flow_filter=FlowFilter(name={"any_": [flow_name]}),
            deployment_filter=DeploymentFilter(
                name={"any_": [deployment_name]}),
        )
        deployment_id = deployments[0].id
        await client.create_flow_run_from_deployment(
            deployment_id=deployment_id,
            state=Scheduled(scheduled_time=scheduled_starttime),
            parameters=parameters
        )
        typer.echo(f"Scheduled new forecast run: {deployment_id} with"
                   f"parameters: {parameters}")


async def add_new_scheduled_run(
    flow_name: str, deployment_name: str,
    forecast_starttime: datetime, scheduled_starttime: datetime,
        forecastseries_id, db_url):
    parameters = dict(
        forecastseries_id=forecastseries_id,
        connection_string=db_url,
        date=forecast_starttime)
    async with get_client() as client:
        deployments = await client.read_deployments(
            flow_filter=FlowFilter(name={"any_": [flow_name]}),
            deployment_filter=DeploymentFilter(
                name={"any_": [deployment_name]}),
        )
        deployment_id = deployments[0].id
        await client.create_flow_run_from_deployment(
            deployment_id=deployment_id,
            state=Scheduled(scheduled_time=scheduled_starttime),
            parameters=parameters
        )
        typer.echo(f"Scheduled new forecast run: {deployment_id} with"
                   f"parameters: {parameters}")


async def list_flow_runs_with_states(states: list):
    async with get_client() as client:
        flow_runs = await client.read_flow_runs(
            flow_run_filter=FlowRunFilter(
                state=FlowRunFilterState(
                    name=FlowRunFilterStateName(any_=states)
                )
            )
        )
    return flow_runs


async def delete_flow_runs(flow_runs):
    async with get_client() as client:
        for flow_run in flow_runs:
            await client.delete_flow_run(flow_run_id=flow_run.id)


async def bulk_delete_flow_runs(states: list):
    flow_runs = await list_flow_runs_with_states(states)

    if len(flow_runs) == 0:
        print(f"There are no flow runs in states {states}")
        return

    print(f"There are {len(flow_runs)} flow runs with states {states}\n")

    for idx, flow_run in enumerate(flow_runs):
        print(f"[{idx + 1}] Flow '{flow_run.name}' with ID '{flow_run.id}'")

    if input("\n[Y/n] Do you wish to proceed: ") == "Y":
        print(f"Deleting {len(flow_runs)} flow runs...")
        await delete_flow_runs(flow_runs)
        print("Done.")
    else:
        print("Aborting...")


async def limit_model_runs(concurrency_limit):
    async with get_client() as client:
        # set a concurrency limit of 10 on the 'small_instance' tag
        _ = await client.create_concurrency_limit(
            # This tag is set within the task definitions at
            # RAMSIS/tasks/forecast.py
            tag="model_run",
            concurrency_limit=concurrency_limit)


async def remove_limit_model_runs():
    async with get_client() as client:
        # remove a concurrency limit on the 'small_instance' tag
        await client.delete_concurrency_limit_by_tag(tag="model_run")


async def read_limit_model_runs():
    async with get_client() as client:
        # query the concurrency limit on the 'small_instance' tag
        limit = await client.read_concurrency_limit_by_tag(tag="model_run")
        return limit
