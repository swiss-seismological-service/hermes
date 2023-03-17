import typer
from os.path import join
from prefect.client import get_client
from prefect.server.schemas.sorting import FlowSort
from ramsis.datamodel import EStage
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import typer
from prefect.deployments import run_deployment
from prefect.deployments import Deployment

import asyncio

from prefect.client import get_client
from prefect.orion.schemas.states import Scheduled
from prefect.orion.schemas.filters import FlowFilter, DeploymentFilter


from RAMSIS.db import app_settings
from RAMSIS.core.builder import (
    default_project, default_forecast, default_scenario)
from ramsis.io.hydraulics import HYDWSBoreholeHydraulicsDeserializer
from ramsis.io.seismics import QuakeMLObservationCatalogDeserializer
#from RAMSIS.flows.register import get_client
#from RAMSIS.flows.manager import manager_flow_name

# All hyd, seismic data is expected in this projection
WGS84_PROJ = "epsg:4326"
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'



async def delete_scheduled_flow_runs():
    client = get_client()
    work_pools = await client.read_work_pools()
    if not work_pools:
        raise Exception("There are no work pools configured")
    if len(work_pools) > 1:
        raise Exception("There are more than one work pools configured")
    flow_runs = await client.get_scheduled_flow_runs_for_work_pool(work_pools[0].name)
    typer.echo(f"There are {len(flow_runs)} flow runs scheduled.")
    for response in flow_runs:
        run = response.dict()["flow_run"]
        await client.delete_flow_run(run["id"])
        typer.echo(f"Flow run with id: {run['id']} with "
                   f"name: {run['name']} has been cancelled.")
    typer.echo("RAMSIS has been stopped, all currently "
               "scheduled flow runs cancelled.")


# One deployment per flow run, but then run it with different
# forecast ids with a scheduled time.


# check for a deployment with the same name as <ramsis_flow_name>/forecast_<id>
def flow_deployment(flow, deployment_name, work_queue_name="default",
                    logging_level="INFO"):
    deployment = Deployment.build_from_flow(
        flow=flow,
        name=deployment_name,
        infra_overrides={"env": {"PREFECT_LOGGING_LEVEL": logging_level}},
        work_queue_name=work_queue_name,
        apply=True
    )
    return deployment

# Don't know if we require this function
#async def scheduled_flow_runs() -> List[Dict]:
#    """
#    Get list of information about all currently scheduled flow runs
#    """
#    client = get_client()
#    work_pools = await client.read_work_pools()
#    print(work_pools)
#    if not work_pools:
#        raise Exception("There are no work pools configured")
#    if len(work_pools) > 1:
#        raise Exception("There are more than one work pools configured")
#    flow_runs = await client.get_scheduled_flow_runs_for_work_pool(
#        work_pools[0].name)
#    return flow_runs


#def cancel_flow_run(flow_run_id: str, msg: str = ""):
#    """Alter state of flow run from flow run id to Cancelled"""
#    client = get_client()
#    _ = client.set_flow_run_state(
#        flow_run_id,
#        Cancelled(msg))


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
        forecast_id, scheduled_time,
        db_url, data_dir):
    parameters = dict(
        forecast_id=forecast_id,
        connection_string=db_url,
        date=datetime.utcnow(),
        data_dir=data_dir)
    deployment_id = f"{flow_name}/{deployment_name}"
    run_deployment(deployment_id, scheduled_time=scheduled_time,
                   parameters=parameters)


async def add_new_scheduled_run(
    flow_name: str, deployment_name: str, dt: datetime,
        forecast_id, db_url, data_dir):
    parameters = dict(
        forecast_id=forecast_id,
        connection_string=db_url,
        date=dt, data_dir=data_dir)
    async with get_client() as client:
        deployments = await client.read_deployments(
            flow_filter=FlowFilter(name={"any_": [flow_name]}),
            deployment_filter=DeploymentFilter(name={"any_": [deployment_name]}),
        )
        deployment_id = deployments[0].id
        await client.create_flow_run_from_deployment(
            deployment_id=deployment_id, state=Scheduled(scheduled_time=dt),
            parameters=parameters
        )
        typer.echo(f"Scheduled new forecast run: {deployment_id} with"
                   f"parameters: {parameters}")
        

#def schedule_forecast(forecast, client, flow_run_name, label,
#                      connection_string, data_dir,
#                      dry_run=False, idempotency_key=None,
#                      scheduled_wait_time=0):
#    if forecast.starttime < datetime.utcnow():
#        scheduled_time = datetime.utcnow() \
#            + timedelta(seconds=scheduled_wait_time)
#        typer.echo(f"Forecast {forecast.id} is due to run in the past. "
#                   "Will be scheduled to run in approximately "
#                   f"{scheduled_wait_time} seconds")
#    else:
#        scheduled_time = forecast.starttime
#    parameters = dict(forecast_id=forecast.id,
#                      connection_string=connection_string,
#                      data_dir=data_dir)
#
#    options = dict(
#        project_name=prefect_project_name,
#        flow_name=manager_flow_name,
#        labels=[label],
#        run_name=flow_run_name,
#        scheduled_start_time=scheduled_time,
#        parameters=parameters,
#        context={
#            'config':
#                {'logging':
#                    {"format":
#                        "%(flow_run_name)s %(message)s"}}}) # noqa
#    if idempotency_key:
#        options.update(dict(idempotency_key=idempotency_key))
#    if not dry_run:
#        flow_run_id = create_flow_run.run(**options)
#
#        typer.echo(
#            f"Forecast {forecast.id} has been scheduled to run at "
#            f"{scheduled_time} with name {flow_run_name} and flow run id: "
#            f"{flow_run_id}")


# To add
def configure_logging(verbosity):
    """
    Configures and the root logger.

    All loggers in submodules will automatically become children of the root
    logger and inherit some of the properties.
    parser.add_argument("-v", "--verbosity", type=int, choices=[0, 1, 2],
                        default=1, help="output verbosity (0-2, default 0)")

    """
    lvl_lookup = {
        0: logging.WARN,
        1: logging.INFO,
        2: logging.DEBUG
    }
    root_logger = logging.getLogger()
    root_logger.setLevel(lvl_lookup[verbosity])
    formatter = logging.Formatter('%(asctime)s %(levelname)s: '
                                  '[%(name)s] %(message)s')
    # ...handlers from 3rd party modules - we don't like your kind here
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
    # ...setup console logging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    # Transitions is a bit noisy on the INFO level
    logging.getLogger('transitions').setLevel(logging.WARNING)


def deserialize_hydws_data(data, ramsis_proj, plan):
    deserializer = HYDWSBoreholeHydraulicsDeserializer(
        ramsis_proj=ramsis_proj,
        external_proj=WGS84_PROJ,
        ref_easting=0.0,
        ref_northing=0.0,
        transform_func_name='pyproj_transform_to_local_coords',
        plan=plan)
    ret_data = deserializer.load(data)
    return ret_data


def deserialize_qml_data(data, ramsis_proj):
    deserializer = QuakeMLObservationCatalogDeserializer(
        ramsis_proj=ramsis_proj,
        external_proj=WGS84_PROJ,
        ref_easting=0.0,
        ref_northing=0.0,
        transform_func_name='pyproj_transform_to_local_coords')
    ret_data = deserializer.load(data)
    return ret_data


def create_scenario(session, project, scenario_config,
                    epoch_duration,
                    seismicity_stage_enabled, hazard_stage_enabled,
                    inj_plan_directory):
    scenario = default_scenario(session, project.model_settings.config,
                                seismicity_stage_enabled, hazard_stage_enabled,
                                name=scenario_config["SCENARIO_NAME"])
    # Seismicity Stage
    seismicity_stage = scenario[EStage.SEISMICITY]
    # redefine epoch duration if defined.
    if "EPOCH_DURATION" in scenario_config.keys():
        if scenario_config["EPOCH_DURATION"]:
            epoch_duration = scenario_config["EPOCH_DURATION"]
    seismicity_stage.config = {
        'epoch_duration': epoch_duration}
    session.add_all(seismicity_stage.runs)
    scenario.reservoirgeom = scenario_config["RESERVOIR"]

    with open(join(inj_plan_directory,
              scenario_config["SCENARIO_JSON"]), 'rb') as inj_plan_data:
        scenario.well = deserialize_hydws_data(
            inj_plan_data, project.proj_string, True)
    # Which models are run for which scenario is defined by RUN_MODELS.
    # This can either be "ALL" or
    # a string containing the model name. "MLE, BAYES"
    # Where if the model name is contained in the string, it will be enabled
    # for that scenario
    run_models = scenario_config["RUN_MODELS"]
    for run in seismicity_stage.runs:
        if run_models == "ALL":
            run.enabled = True
        elif run.model.name in run_models:
            run.enabled = True
        else:
            run.enabled = False
    if hazard_stage_enabled:
        try:
            hazard_stage = scenario[EStage.HAZARD]
            hazard_stage.model_id = scenario_config["HAZARD_MODEL_ID"]
        except KeyError:
            raise KeyError("Please add a HAZARD_MODEL_ID to the "
                           "scenario config")

    return scenario


def create_forecast(session,
                    project,
                    forecast_config,
                    inj_plan_directory,
                    hyd_data,
                    catalog_data):

    forecast_start = datetime.strptime(forecast_config['FORECAST_STARTTIME'],
                                       DATETIME_FORMAT)
    forecast_end = datetime.strptime(forecast_config['FORECAST_ENDTIME'],
                                     DATETIME_FORMAT)
    assert forecast_start < forecast_end
    # assign default epoch duration
    default_epoch_duration = (forecast_end - forecast_start).total_seconds()

    fc = default_forecast(
        session,
        starttime=forecast_config["FORECAST_STARTTIME"],
        endtime=forecast_config["FORECAST_ENDTIME"],
        num_scenarios=0,
        name=forecast_config["FORECAST_NAME"])
    session.add(fc)
    fc.project = project

    scenarios_json = forecast_config['SCENARIOS']
    scenarios = [create_scenario(session,
                                 project,
                                 scenario_config,
                                 default_epoch_duration,
                                 forecast_config["SEISMICITY_STAGE"],
                                 forecast_config["HAZARD_STAGE"],
                                 inj_plan_directory)
                 for scenario_config in scenarios_json]
    fc.scenarios = scenarios
    session.add_all(fc.scenarios)
    if hyd_data:
        well = deserialize_hydws_data(hyd_data, project.proj_string, False)
        fc.well = [well]
        session.add(well)
    if catalog_data:
        cat = deserialize_qml_data(
            catalog_data, project.proj_string)
        fc.seismiccatalog = [cat]
        session.add(cat)
    typer.echo(f"catalog_data, {catalog_data}")
    session.commit()
    return fc


def update_model_settings(project, project_config):

    project.settings.config = dict(
        fdsnws_url=project_config['FDSNWS_URL'],
        hydws_url=project_config['HYDWS_URL'],
        seismic_catalog=project_config['SEISMIC_CATALOG'],
        well=project_config['WELL'],
        scenario=project_config['SCENARIO'])

    project.model_settings.config = project_config['MODEL_PROJECT_CONFIG']
    return project


def create_project(project_config):

    project = default_project(
        name=project_config["PROJECT_NAME"],
        description=project_config["PROJECT_DESCRIPTION"],
        starttime=project_config["PROJECT_STARTTIME"],
        endtime=project_config["PROJECT_ENDTIME"],
        proj_string=project_config["RAMSIS_PROJ"])

    project = update_model_settings(project, project_config)
    return project


def update_project(project, project_config):

    project.name = project_config["PROJECT_NAME"],
    project.description = project_config["PROJECT_DESCRIPTION"]
    project.starttime = project_config["PROJECT_STARTTIME"]
    project.endtime = project_config["PROJECT_ENDTIME"]
    project.proj_string = project_config["RAMSIS_PROJ"]

    project = update_model_settings(project, project_config)
    return project

# There is no easy way to restart a flow run with the client, it is much
# easier with the UI. This workaround is found here:
# https://github.com/PrefectHQ/prefect/issues/5516
# Place where ths code came from within the issue:
# https://github.com/PrefectHQ/ui/blob/f896513fd6b4ee7ffe961ed0e16733f68f37811d/src/pages/FlowRun/Actions.vue#L118


#def get_failed_task_runs(flow_run_id):
#    client = get_client()
#    return client.graphql(
#        query="""
#            query FailedTaskRuns($flowRunId: uuid, $failedStates: [String!]) {
#            task_run(where: {flow_run_id: {_eq: $flowRunId}, state:
#            {_in: $failedStates}})
#                {
#                id
#                task_id
#                version
#            }
#        }
#    """,
#        variables={
#            "flowRunId": flow_run_id,
#            "failedStates": ["Cancelled", "Failed", "TimedOut",
#                             "TriggerFailed"],
#        },
#    )["data"]["task_run"]
#
#
#def get_utility_downstream_tasks(flow_run_id, task_ids):
#    client = get_client()
#    return client.graphql(
#        query="""
#    query taskRunUtilityDownstreamTasks($flowRunId: uuid, $taskIds: _uuid) {
#        utility_downstream_tasks(args: {start_task_ids: $taskIds}) {
#            task_id
#            depth
#            task {
#                task_runs(where: {flow_run_id: {_eq: $flowRunId}}) {
#                    id
#                    map_index
#                    version
#                }
#            }
#        }
#    }
#    """,
#        variables={
#            "flowRunId": flow_run_id,
#            "taskIds": "{%s}" % ",".join(task_ids),
#        },
#    )["data"]["utility_downstream_tasks"]
#
#
#def mark_run_for_restart(tasks_info):
#    # https://github.com/PrefectHQ/ui/blob/f896513fd6b4ee7ffe961ed0e16733f68f37811d/src/pages/FlowRun/Restart-Dialog.vue#L90
#    client = get_client()
#    client.graphql(
#        query="""
#            mutation setTaskRunStates($input: [set_task_run_state_input!]!) {
#                set_task_run_states(input: {states: $input}) {
#                    states {
#                    id
#                }
#            }
#        }
#        """,
#        variables={
#            "input": [
#                {
#                    "version": task_run_info["version"],
#                    "task_run_id": task_run_info["id"],
#                    "state": {
#                        "type": "Pending",
#                        "message": "null restarted this flow run",
#                    },
#                }
#                for task_run_info in tasks_info
#            ]
#        },
#    )


#def restart_flow_run(flow_run_id):
#    failed_tasks = get_failed_task_runs(flow_run_id=flow_run_id)
#    failed_tasks_ids = [task["id"] for task in failed_tasks]
#
#    downstream_tasks = get_utility_downstream_tasks(
#        flow_run_id=flow_run_id, task_ids=[task["task_id"] for
#                                           task in failed_tasks]
#    )
#
#    mark_run_for_restart(
#        # https://github.com/PrefectHQ/ui/blob/f896513fd6b4ee7ffe961ed0e16733f68f37811d/src/pages/FlowRun/Restart-Dialog.vue#L70
#        [
#            {"id": run["id"], "version": run["version"]}
#            for task in downstream_tasks
#            for run in task["task"]["task_runs"]
#            if run["id"] in failed_tasks_ids or
#            (not run.get("map_index", None) and run["map_index"] != 0)
#        ]
#    )
#
#    # https://github.com/PrefectHQ/ui/blob/f896513fd6b4ee7ffe961ed0e16733f68f37811d/src/pages/FlowRun/Restart-Dialog.vue#L108
#    client = get_client()
#    return client.set_flow_run_state(
#        flow_run_id=flow_run_id,
#        state=Scheduled(),
#    )
