from prefect.schedules.clocks import DatesClock
import os
from ramsis.datamodel import Forecast
from RAMSIS.flows import client, prefect_project_name
from RAMSIS.flows.manager import manager_flow, task_result_format, result_location, manager_task_location
from datetime import datetime, timedelta
from prefect.tasks.prefect.flow_run import get_task_run_result, wait_for_flow_run
from prefect.tasks.prefect import create_flow_run, wait_for_flow_run, get_task_run_result
import time
from prefect.backend import FlowRunView
import cloudpickle
from RAMSIS.core.engine.engine import Engine


# create clock that include date(s) that a specific forecast task should run at
# a run has alredy been created that includes all the forecast data, just need to
# schedule it.



if __name__ == "__main__":

    engine = Engine()
    if not os.path.exists(result_location):
        os.makedirs(result_location)
    ##### move registering flows to somewhere else away from ramsis executed code 
    #manager_flow_id = manager_flow.register(project_name=prefect_project_name)
    #print("manager_flow_id", manager_flow_id)
    #print(manager_flow.serialize())
    forecast_starttime = datetime.utcnow() + timedelta(seconds=30)
    datetimes_list = [forecast_starttime]
    system_time = datetime.utcnow().isoformat()
    forecast_id = 40
    parameters = dict(forecast_id=forecast_id, system_time=system_time)
    manager_flow.run(parameters=parameters)
    # only need to create a schedule if want to create many at same time.
    #schedule = DatesClock(datetimes_list, parameter_defaults=parameters)
    client.create_flow_run(manager_flow_id, labels=["main-flow"],
        parameters=parameters)
    flow_run_id = create_flow_run.run(
        project_name=prefect_project_name,
        flow_name="Manager",
        labels=["main-flow"],
        scheduled_start_time=forecast_starttime,
        idempotency_key="do-not-create-two-runs",
        parameters=parameters)

    #task_result_name = manager_task_location.format(task_name='StartForecastCheck', flow_run_id=flow_run_id)
    #with open(task_result_name, 'rb') as f:
    #    content = f.read()
    #a = cloudpickle.loads(content)
    #print(a, type(a))
    #if a:
    #forecast_flow_state = engine.run(system_time, forecast_id)
