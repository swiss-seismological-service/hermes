
from prefect import Flow, Parameter, unmapped
from RAMSIS.core.engine.forecastexecutor import \
    SeismicityModelRunPoller, SeismicityModelRunExecutor,\
    ModelRuns, forecast_scenarios, UpdateFdsn, UpdateHyd,\
    dispatched_model_runs, DummyTask,\
    FlattenTask, ScenarioSerializeData, ForecastSerializeData
from ramsis.datamodel import EStage
from RAMSIS.core.engine.state_handlers import ForecastHandler
from RAMSIS.utils import SynchronousThread
from RAMSIS.db import store
from RAMSIS.flows.manager import StartForecastCheck, UpdateForecastStatus
from RAMSIS.flows.state_handler import state_handler

from PyQt5.QtCore import QThreadPool
from prefect.storage import Local
from RAMSIS.flows.manager import manager_flow



forecast_handler = ForecastHandler(QThreadPool(), SynchronousThread())
forecast_handler.session = store.session






# Seismicity Forecast Flow
with Flow("SeismicityForecast",
          storage=Local(),
          ) as seismicity_flow:
    forecast = Parameter('forecast')
    system_time = Parameter('system_time')
    remove_data_task = DummyTask(
        state_handlers=[forecast_handler.forecast_data_delete])
    forecast_no_data = remove_data_task(forecast)
    update_fdsn = UpdateFdsn(
        state_handlers=[forecast_handler.
                        forecast_catalog_state_handler])
    forecast_with_catalog = update_fdsn(forecast_no_data, system_time)

    update_hyd = UpdateHyd(
        state_handlers=[forecast_handler.
                        forecast_well_state_handler])
    forecast = update_hyd(forecast_with_catalog, system_time)
    scenarios = forecast_scenarios(
        forecast)

    # Get seismicity model runs
    seismicity_models = ModelRuns(
        state_handlers=[forecast_handler.
                        scenario_models_state_handler])
    seismicity_model_runs = seismicity_models.map(
        scenarios, unmapped(EStage.SEISMICITY))
    # Flatten list of lists of runs so mapping can take place.
    # (prefect currently does not allow mapping at multiple levels)
    flatten_task = FlattenTask()
    model_runs_flattened = flatten_task(seismicity_model_runs)

    forecast_serializer = ForecastSerializeData()
    forecast_serialized_data = forecast_serializer(forecast)

    scenario_serializer = ScenarioSerializeData()
    scenario_serialized_data = scenario_serializer.map(scenarios)

    model_run_executor = SeismicityModelRunExecutor(
        state_handlers=[forecast_handler.model_run_state_handler])

    _ = model_run_executor.map(
        unmapped(forecast), unmapped(forecast_serialized_data),
        unmapped(scenario_serialized_data), model_runs_flattened)

    # Check which model runs are dispatched, where there may exist
    # model runs that were sent that still haven't been collected
    model_runs_dispatched = dispatched_model_runs(
        forecast, EStage.SEISMICITY)

    # Add dependency so that SeismicityModelRunExecutor must complete
    # before checking for model runs with DISPATCHED status
    seismicity_flow.add_edge(
        seismicity_flow.get_tasks('SeismicityModelRunExecutor')[0],
        seismicity_flow.get_tasks(
            'dispatched_model_runs')[0])

    # Poll the remote workers for tasks that have been completed.
    model_run_poller = SeismicityModelRunPoller(
        state_handlers=[
            forecast_handler.poll_seismicity_state_handler])
    model_run_poller.map(unmapped(forecast),
                         model_runs_dispatched)

# Only register once the flow has been converted to something that can be serializable. - next step.
# recreated internally every time it runs at the moment, not stored on the cloud.
#seismicity_flow_id = client.register(seismicity_flow,
#                                     project_name=prefect_project_name)



