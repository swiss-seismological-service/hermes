from os.path import join, expanduser

from RAMSIS.tasks.manager import SeismicityStageCheck, \
    HazardStageCheck
from prefect import Flow, Parameter, case
from prefect.engine.results import LocalResult
from prefect.storage import Local
from RAMSIS.db import app_settings, project
from RAMSIS.flows.hazard import hazard_flow_name
from RAMSIS.flows.seismicity import seismicity_flow_name

from prefect.tasks.prefect import create_flow_run, wait_for_flow_run
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
        connection_string = Parameter('connection_string')
        data_dir = Parameter('data_dir')
        seismicity_stage_check = SeismicityStageCheck()
        with case(seismicity_stage_check(forecast_id, connection_string),
                  True):
            seismicity_flow_run = create_flow_run(
                flow_name=seismicity_flow_name, project_name=project,
                parameters=dict(forecast_id=forecast_id))
            wait_for_seismicity_flow_run = wait_for_flow_run(
                seismicity_flow_run,
                raise_final_state=True)
            hazard_stage_check = HazardStageCheck()
            with case(hazard_stage_check(forecast_id, connection_string),
                      True):
                # TODO input project name
                hazard_flow_run = create_flow_run(
                    flow_name=hazard_flow_name, project_name=project,
                    parameters={
                        "forecast_id": forecast_id,
                        "connection_string": connection_string,
                        "data_dir": data_dir})

                wait_for_flow_run(hazard_flow_run, stream_states=True,
                                  stream_logs=True)
                hazard_flow_run.set_upstream(wait_for_seismicity_flow_run)

    return manager_flow


manager_flow_name = f"{app_settings['label']}Manager"
manager_flow = manager_flow_factory(manager_flow_name)
