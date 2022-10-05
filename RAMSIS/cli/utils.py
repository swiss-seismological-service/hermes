import typer
from ramsis.datamodel import EStage, EStatus
from RAMSIS.db import store
import logging
import io

from prefect.tasks.prefect import create_flow_run
from datetime import datetime
from RAMSIS.flows.register import prefect_project_name
from RAMSIS.db import app_settings
from RAMSIS.core.builder import (
    default_project, default_forecast, default_scenario)
from ramsis.io.hydraulics import HYDWSBoreholeHydraulicsDeserializer
from ramsis.io.seismics import QuakeMLObservationCatalogDeserializer
from prefect.engine.state import Cancelled, Scheduled
from prefect.utilities.graphql import EnumValue, with_args
from typing import List, Dict

from RAMSIS.flows.register import get_client
from RAMSIS.flows.manager import manager_flow_name

# All hyd, seismic data is expected in this projection
WGS84_PROJ = "epsg:4326"


def matched_flow_run(idempotency_key: str,
                     label: str,
                     flow_name: str = manager_flow_name) -> Dict:
    """
    Get list of information about all currently scheduled flow runs
    with the input flow name.
    # maybe add project name too? how to make sure that
    """
    order = {"created": EnumValue("desc")}

    where = {
        "_and": {
            "flow": {
                "_and": {
                    "name": {"_eq": flow_name},
                }
            },
            "_and": {
                "idempotency_key": {"_eq": idempotency_key},
                "labels": {"_has_key": label}
            }
        }
    }

    query = {
        "query": {
            with_args(
                "flow_run", {"where": where, "order_by": order}
            ): {
                "flow": {"name": True},
                "id": True,
                "created": True,
                "state": True,
                "name": True,
                "start_time": True,
                "scheduled_start_time": True,
            }
        }
    }

    client = get_client()
    result = client.graphql(query)
    flow_run_list = result.data.flow_run
    if len(flow_run_list) > 1:
        raise Exception("Number of matching flow runs exceeds 1, "
                        f"{flow_run_list}")
    flow_run = flow_run_list[0] if flow_run_list else None
    return flow_run


def scheduled_flow_runs(flow_name: str = manager_flow_name,
                        state: str = "Scheduled") -> List[Dict]:
    """
    Get list of information about all currently scheduled flow runs
    with the input flow name.
    """
    order = {"created": EnumValue("desc")}

    where = {
        "_and": {
            "flow": {
                "_and": {
                    "name": {"_eq": flow_name},
                }
            },
            "state": {"_eq": state},
        }
    }

    query = {
        "query": {
            with_args(
                "flow_run", {"where": where, "order_by": order}
            ): {
                "flow": {"name": True},
                "id": True,
                "created": True,
                "state": True,
                "name": True,
                "start_time": True,
                "scheduled_start_time": True,
            }
        }
    }

    client = get_client()
    result = client.graphql(query)
    flow_run_list = result.data.flow_run
    return flow_run_list


def cancel_flow_run(flow_run_id: str, msg: str = ""):
    """Alter state of flow run from flow run id to Cancelled"""
    client = get_client()
    _ = client.set_flow_run_state(
        flow_run_id,
        Cancelled(msg))


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


def schedule_forecast(forecast, client, flow_run_name, label,
                      dry_run=False):
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
            flow_name=manager_flow_name,
            labels=[label],
            run_name=flow_run_name,
            scheduled_start_time=scheduled_time,
            idempotency_key=flow_run_name,
            parameters=parameters)

        typer.echo(
            f"Forecast {forecast.id} has been scheduled to run at "
            f"{scheduled_time} with name {flow_run_name} and flow run id: "
            f"{flow_run_id}")


def reset_forecast(forecast):
    forecast.status.state = EStatus.PENDING
    for scenario in forecast.scenarios:
        scenario.status.state = EStatus.PENDING
        stage = scenario[EStage.SEISMICITY]
        stage.status.state = EStatus.PENDING
        for run in stage.runs:
            run.status.state = EStatus.PENDING
    return forecast


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


def create_scenario(project, scenario_config, inj_plan_data):
    scenario = default_scenario(store, project.model_settings.config,
                                name=scenario_config["SCENARIO_NAME"])
    # Seismicity Stage
    seismicity_stage = scenario[EStage.SEISMICITY]
    seismicity_stage.config = {
        'epoch_duration': scenario_config["EPOCH_DURATION"]}
    scenario.reservoirgeom = scenario_config["RESERVOIR"]

    if inj_plan_data:
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

    return scenario


def create_forecast(project,
                    forecast_config,
                    inj_plan_data,
                    hyd_data,
                    catalog_data):

    fc = default_forecast(
        store,
        starttime=forecast_config["FORECAST_STARTTIME"],
        endtime=forecast_config["FORECAST_ENDTIME"],
        num_scenarios=0,
        name=forecast_config["FORECAST_NAME"])
    store.add(fc)

    scenarios_json = forecast_config['SCENARIOS']
    scenarios = [create_scenario(project,
                                 scenario_config, inj_plan_data)
                 for scenario_config in scenarios_json]
    fc.scenarios = scenarios
    if hyd_data:
        fc.well = [deserialize_hydws_data(hyd_data, project.proj_string, False)]
    typer.echo(f"catalog_data, {catalog_data}")
    if catalog_data:
        cats = [deserialize_qml_data(catalog_data, project.proj_string)]
        for cat in cats:
            store.add(cat)
            cat.forecast_id = fc.id
        typer.echo(fc.seismiccatalog)
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


def get_failed_task_runs(flow_run_id):
    client = get_client()
    return client.graphql(
        query="""
            query FailedTaskRuns($flowRunId: uuid, $failedStates: [String!]) {
            task_run(where: {flow_run_id: {_eq: $flowRunId}, state:
            {_in: $failedStates}})
                {
                id
                task_id
                version
            }
        }
    """,
        variables={
            "flowRunId": flow_run_id,
            "failedStates": ["Cancelled", "Failed", "TimedOut",
                             "TriggerFailed"],
        },
    )["data"]["task_run"]


def get_utility_downstream_tasks(flow_run_id, task_ids):
    client = get_client()
    return client.graphql(
        query="""
    query taskRunUtilityDownstreamTasks($flowRunId: uuid, $taskIds: _uuid) {
        utility_downstream_tasks(args: {start_task_ids: $taskIds}) {
            task_id
            depth
            task {
                task_runs(where: {flow_run_id: {_eq: $flowRunId}}) {
                    id
                    map_index
                    version
                }
            }
        }
    }
    """,
        variables={
            "flowRunId": flow_run_id,
            "taskIds": "{%s}" % ",".join(task_ids),
        },
    )["data"]["utility_downstream_tasks"]


def mark_run_for_restart(tasks_info):
    # https://github.com/PrefectHQ/ui/blob/f896513fd6b4ee7ffe961ed0e16733f68f37811d/src/pages/FlowRun/Restart-Dialog.vue#L90
    client = get_client()
    client.graphql(
        query="""
            mutation setTaskRunStates($input: [set_task_run_state_input!]!) {
                set_task_run_states(input: {states: $input}) {
                    states {
                    id
                }
            }
        }
        """,
        variables={
            "input": [
                {
                    "version": task_run_info["version"],
                    "task_run_id": task_run_info["id"],
                    "state": {
                        "type": "Pending",
                        "message": "null restarted this flow run",
                    },
                }
                for task_run_info in tasks_info
            ]
        },
    )


def restart_flow_run(flow_run_id):
    failed_tasks = get_failed_task_runs(flow_run_id=flow_run_id)
    failed_tasks_ids = [task["id"] for task in failed_tasks]

    downstream_tasks = get_utility_downstream_tasks(
        flow_run_id=flow_run_id, task_ids=[task["task_id"] for
                                           task in failed_tasks]
    )

    mark_run_for_restart(
        # https://github.com/PrefectHQ/ui/blob/f896513fd6b4ee7ffe961ed0e16733f68f37811d/src/pages/FlowRun/Restart-Dialog.vue#L70
        [
            {"id": run["id"], "version": run["version"]}
            for task in downstream_tasks
            for run in task["task"]["task_runs"]
            if run["id"] in failed_tasks_ids or
            (not run.get("map_index", None) and run["map_index"] != 0)
        ]
    )

    # https://github.com/PrefectHQ/ui/blob/f896513fd6b4ee7ffe961ed0e16733f68f37811d/src/pages/FlowRun/Restart-Dialog.vue#L108
    client = get_client()
    return client.set_flow_run_state(
        flow_run_id=flow_run_id,
        state=Scheduled(),
    )
