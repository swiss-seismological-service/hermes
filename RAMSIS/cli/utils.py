import typer
from prefect.client import get_client
import logging
from datetime import datetime
from prefect.deployments import run_deployment
from prefect.deployments import Deployment

from prefect.orion.schemas.states import Scheduled
from prefect.orion.schemas.filters import FlowFilter, DeploymentFilter


from RAMSIS.db import app_settings
from ramsis.io.hydraulics import HYDWSBoreholeHydraulicsDeserializer
from ramsis.io.seismics import QuakeMLObservationCatalogDeserializer

# All hyd, seismic data is expected in this projection
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
def flow_deployment(flow, deployment_name, schedule, work_queue_name="default",
                    logging_level="INFO"):
    print("type schedule", type(schedule))
    deployment = Deployment.build_from_flow(
        flow=flow,
        name=deployment_name,
        infra_overrides={"env": {"PREFECT_LOGGING_LEVEL": logging_level}},
        work_queue_name=work_queue_name,
        schedule=schedule,
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
        forecastseries_id, forecast_starttime,
        db_url, data_dir):
    parameters = dict(
        forecastseries_id=forecastseries_id,
        connection_string=db_url,
        date=forecast_starttime,
        data_dir=data_dir)
    deployment_id = f"{flow_name}/{deployment_name}"
    run_deployment(deployment_id, scheduled_time=forecast_starttime,
                   parameters=parameters)


async def add_new_scheduled_run(
    flow_name: str, deployment_name: str,
    forecast_starttime: datetime, scheduled_starttime: datetime,
        forecastseries_id, db_url):
    parameters = dict(
        forecastseries_id=forecastseries_id,
        connection_string=db_url,
        date=forecast_starttime)
    print("parameters", parameters)
    async with get_client() as client:
        deployments = await client.read_deployments(
            flow_filter=FlowFilter(name={"any_": [flow_name]}),
            deployment_filter=DeploymentFilter(name={"any_": [deployment_name]}),
        )
        deployment_id = deployments[0].id
        await client.create_flow_run_from_deployment(
            deployment_id=deployment_id, state=Scheduled(scheduled_time=scheduled_starttime),
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
        plan=plan)
    ret_data = deserializer.load(data)
    return ret_data


def deserialize_qml_data(data, ramsis_proj):
    deserializer = QuakeMLObservationCatalogDeserializer()
    ret_data = deserializer.load(data)
    return ret_data
