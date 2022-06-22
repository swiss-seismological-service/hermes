from RAMSIS.core.engine.forecastexecutor import \
    DummyTask, UpdateHyd, UpdateFdsn
from os.path import join, dirname, expanduser
from PyQt5.QtCore import QObject, QThreadPool

from RAMSIS.core.engine.state_handlers import ForecastHandler
from RAMSIS.core.engine.engine import ForecastFlow, HazardFlow, \
    scenario_for_hazard, HazardPreparationFlow, forecast_for_seismicity

from RAMSIS.tasks.manager import StartForecastCheck, UpdateForecastStatus,\
    format_trigger_engine_command, trigger_engine, dummy_shell_task
import prefect
from RAMSIS.db import store
from prefect import Flow, Parameter, task, case, Task
from prefect.engine.executors import LocalDaskExecutor
from ramsis.datamodel import EStatus, Forecast, EStage
from prefect.engine.results import LocalResult
from prefect.storage import Local

from RAMSIS.flows.state_handler import state_handler
task_result_format = '{task_name}_{flow_run_id}'
result_location = expanduser('~/prefect_results')
manager_task_location = join(result_location, task_result_format)

# https://github.com/PrefectHQ/prefect/issues/4570#issuecomment-1013146154

# Manager flow
with Flow("Manager",
          storage=Local(),
          state_handlers=[state_handler],
          result=LocalResult(),
          ) as manager_flow:
    # Check if seismicity forecast should be run, returning
    # True if so. (if statuses are not complete)
    forecast_id = Parameter('forecast_id')
    start_forecast_check = StartForecastCheck(result=LocalResult(location=manager_task_location))
    update_forecast_status = UpdateForecastStatus()
    with case(start_forecast_check(forecast_id), True):
        forecast = update_forecast_status(forecast_id, estatus=EStatus.RUNNING)
        trigger_engine(command=format_trigger_engine_command(forecast_id))
        #dummy_shell_task(command="pwd; ls; printenv")

