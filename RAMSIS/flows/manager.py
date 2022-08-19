from os.path import join, expanduser

from RAMSIS.tasks.manager import StartForecastCheck, UpdateForecastStatus,\
    format_trigger_engine_command, trigger_engine
from prefect import Flow, Parameter, case
from ramsis.datamodel import EStatus
from prefect.engine.results import LocalResult
from prefect.storage import Local
from RAMSIS.db import app_settings

from RAMSIS.flows.state_handler import state_handler
task_result_format = '{task_name}_{flow_run_id}'
result_location = expanduser('~/prefect_results')
manager_task_location = join(result_location, task_result_format)

# https://github.com/PrefectHQ/prefect/issues/4570#issuecomment-1013146154


def manager_flow_factory(flow_name):
    # Manager flow
    with Flow(flow_name,
              storage=Local(),
              state_handlers=[state_handler],
              result=LocalResult(),
              ) as manager_flow:
        # Check if seismicity forecast should be run, returning
        # True if so. (if statuses are not complete)
        forecast_id = Parameter('forecast_id')
        start_forecast_check = StartForecastCheck(
            result=LocalResult(location=manager_task_location))
        update_forecast_status = UpdateForecastStatus()
        with case(start_forecast_check(forecast_id), True):
            forecast = update_forecast_status( # noqa
                forecast_id, estatus=EStatus.RUNNING)
            trigger_engine(command=format_trigger_engine_command(forecast_id))
    return manager_flow


manager_flow_name = f"{app_settings['label']}Manager"
manager_flow = manager_flow_factory(manager_flow_name)
