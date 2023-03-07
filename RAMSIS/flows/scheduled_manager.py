#from os.path import join, expanduser
#import prefect
#from RAMSIS.tasks.manager import SeismicityStageCheck, \
#    CloneForecast
#from prefect import Flow, Parameter, case
#from prefect.engine.results import LocalResult
#from prefect.storage import Local
#from RAMSIS.db import project
#from RAMSIS.flows.seismicity import seismicity_flow_name
#
#from prefect.tasks.prefect import create_flow_run, wait_for_flow_run
#from RAMSIS.flows.state_handler import state_handler
#task_result_format = '{task_name}_{flow_run_id}'
#result_location = expanduser('~/prefect_results')
#manager_task_location = join(result_location, task_result_format)
#
## https://github.com/PrefectHQ/prefect/issues/4570#issuecomment-1013146154
#
#
#def scheduled_manager_flow_factory(flow_name, schedule,
#                                   input_forecast_id,
#                                   input_connection_string):
#    # Manager flow
#    with Flow(flow_name,
#              schedule=schedule,
#              storage=Local(),
#              state_handlers=[state_handler],
#              result=LocalResult(),
#              ) as manager_flow:
#        reference_forecast_id = Parameter('forecast_id',
#                                          default=input_forecast_id)
#        connection_string = Parameter('connection_string',
#                                      default=input_connection_string)
#        seismicity_stage_check = SeismicityStageCheck()
#        clone_forecast = CloneForecast()
#        forecast_id = clone_forecast(reference_forecast_id, connection_string)
#        with prefect.context(forecast_id=forecast_id):
#            with case(seismicity_stage_check(forecast_id, connection_string),
#                      True):
#                seismicity_flow_run = create_flow_run(
#                    flow_name=seismicity_flow_name, project_name=project,
#                    parameters=dict(forecast_id=forecast_id))
#                _ = wait_for_flow_run(
#                    seismicity_flow_run,
#                    raise_final_state=True)
#
#    return manager_flow
