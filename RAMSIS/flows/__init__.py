from prefect import Flow, Parameter, unmapped
from RAMSIS.core.engine.forecastexecutor import \
    SeismicityModelRunPoller, SeismicityModelRunExecutor,\
    ModelRuns, forecast_scenarios, UpdateFdsn, UpdateHyd,\
    dispatched_model_runs,\
    FlattenTask, ScenarioSerializeData, ForecastSerializeData
from ramsis.datamodel import EStage
from RAMSIS.core import engine

from prefect.storage import Local


# Seismicity Forecast Flow
with Flow("SeismicityForecast",
          storage=Local(),
          ) as seismicity_flow:
    forecast = Parameter('forecast')
    system_time = Parameter('system_time')
    update_fdsn = UpdateFdsn(
        state_handlers=[engine.forecast_handler.
                        forecast_catalog_state_handler],
        log_stdout=True)
    forecast_with_catalog = update_fdsn(forecast, system_time)

    update_hyd = UpdateHyd(
        state_handlers=[engine.forecast_handler.
                        forecast_well_state_handler],
        log_stdout=True)
    forecast = update_hyd(forecast_with_catalog, system_time)
    scenarios = forecast_scenarios(
        forecast)

    # Get seismicity model runs
    seismicity_models = ModelRuns(
        state_handlers=[engine.forecast_handler.
                        scenario_models_state_handler])
    seismicity_model_runs = seismicity_models.map(
        scenarios, unmapped(EStage.SEISMICITY))
    # Flatten list of lists of runs so mapping can take place.
    # (prefect currently does not allow mapping at multiple levels)
    flatten_task = FlattenTask()
    model_runs_flattened = flatten_task(seismicity_model_runs)

    forecast_serializer = ForecastSerializeData(log_stdout=True)
    forecast_serialized_data = forecast_serializer(forecast)

    scenario_serializer = ScenarioSerializeData()
    scenario_serialized_data = scenario_serializer.map(scenarios)

    model_run_executor = SeismicityModelRunExecutor(
        state_handlers=[engine.forecast_handler.model_run_state_handler],
        log_stdout=True)

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
            engine.forecast_handler.poll_seismicity_state_handler],
        log_stdout=True)
    model_run_poller.map(unmapped(forecast),
                         model_runs_dispatched)
