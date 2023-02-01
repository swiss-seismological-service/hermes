from prefect import Flow, task, Parameter
from prefect.tasks.shell import ShellTask
from RAMSIS.db import app_settings
from prefect.engine.results import LocalResult
from prefect.storage import Local

seismicity_flow_name = 'SeismiciyFlow'


@task
def format_trigger_engine_command(forecast_id):
    return f"ramsis engine run {forecast_id}"


trigger_engine = ShellTask(
    helper_script=app_settings['env/load_environment_cmd'],
    stream_output=True, log_stderr=True, return_all=True)


def seismicity_flow_factory(flow_name):
    with Flow(flow_name,
              storage=Local(),
              result=LocalResult()) as seismicity_flow:
        forecast_id = Parameter('forecast_id')
        seis_result = trigger_engine(command=format_trigger_engine_command( # noqa
            forecast_id))
    return seismicity_flow


seismicity_flow_name = "SeismicityForecast"
seismicity_flow = seismicity_flow_factory(seismicity_flow_name)
