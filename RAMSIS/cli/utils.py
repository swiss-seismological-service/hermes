
import typer
from ramsis.datamodel import EStage, EStatus

from prefect.tasks.prefect import create_flow_run
from datetime import datetime
from RAMSIS.flows.register import prefect_project_name
from RAMSIS.db import app_settings


def get_idempotency_id():

    idempotency_id = ""
    try:
        idempotency_id = app_settings["idempotency_id"]
    except KeyError:
        idempotency_id = ""
        typer.echo(
            "No idempotency_id set in config file - this could lead to "
            "problems if ramsis is run from multiple locations.")
    return idempotency_id


def schedule_forecast(forecast, client, idempotency_id='', dry_run=False):
    if forecast.starttime < datetime.utcnow():
        scheduled_time = datetime.utcnow()
        typer.echo(f"Forecast {forecast.id} is due to run in the past. "
                   "Scheduled to run as soon as possible.")
    else:
        scheduled_time = forecast.starttime
    parameters = dict(forecast_id=forecast.id)
    flow_run_name = f"{idempotency_id}forecast_run_{forecast.id}"
    if not dry_run:
        flow_run_id = create_flow_run.run(
            project_name=prefect_project_name,
            flow_name="Manager",
            labels=["main-flow"],
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
