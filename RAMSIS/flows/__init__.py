
from prefect import flow
from RAMSIS.flows.seismicity import seismicity_stage_flow
from RAMSIS.flows.hazard import hazard_stage_flow
from RAMSIS.tasks.seismicity_forecast import \
    run_seismicity_flow
from RAMSIS.tasks.hazard import \
    run_hazard_flow
from RAMSIS.tasks.utils import clone_forecast, set_statuses, \
    update_status
from ramsis.datamodel import EStage, EStatus


@flow(name="ramsis_flow")
def ramsis_flow(forecast_id, connection_string, date, data_dir):
    initial_update_status_running = update_status(
        forecast_id, connection_string, EStatus.RUNNING)
    if run_seismicity_flow(forecast_id, connection_string, wait_for=[initial_update_status_running]):
        seismicity_stage_flow(forecast_id, connection_string, date)
    set_statuses(forecast_id, EStage.SEISMICITY,
                     connection_string)
    if run_hazard_flow(forecast_id, connection_string):
        hazard_stage_flow(forecast_id, connection_string, data_dir)
    set_statuses(forecast_id, EStage.HAZARD,
                     connection_string)


@flow(name="scheduled_ramsis_flow")
def scheduled_ramsis_flow(
        reference_forecast_id, connection_string,
        date):
    forecast_id = clone_forecast(reference_forecast_id,
                                 connection_string, date)
    if run_seismicity_flow(forecast_id, connection_string):
        seismicity_stage_flow(forecast_id, connection_string, date,
                              forecast_id=forecast_id, date=date)
