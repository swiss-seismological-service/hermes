
from prefect import flow
from RAMSIS.flows.seismicity import seismicity_stage_flow
from RAMSIS.tasks.seismicity_forecast import \
    run_seismicity_flow
from RAMSIS.tasks.utils import clone_forecast


@flow(name="ramsis_flow")
def ramsis_flow(forecast_id, connection_string, date):
    if run_seismicity_flow(forecast_id, connection_string):
        seismicity_stage_flow(forecast_id, connection_string, date,
                              forecast_id=forecast_id, date=date)


@flow(name="scheduled_ramsis_flow")
def scheduled_ramsis_flow(
        reference_forecast_id, connection_string,
        date):
    forecast_id = clone_forecast(reference_forecast_id,
                                 connection_string, date)
    if run_seismicity_flow(forecast_id, connection_string):
        seismicity_stage_flow(forecast_id, connection_string, date,
                              forecast_id=forecast_id, date=date)
