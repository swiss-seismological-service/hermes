
from RAMSIS.utils import SynchronousThread
import concurrent.futures
from RAMSIS.core.engine.state_handlers import ForecastHandler, \
    HazardHandler, HazardPreparationHandler
from RAMSIS.db import store

forecast_context_format = "forecast_id: {forecast_id} |"
scenario_context_format = "forecast_id: {forecast_id} scenario_id: " \
    "{scenario_id}|"
model_run_context_format = "forecast_id: {forecast_id} scenario_id: " \
    "{scenario_id} model_run_id: {model_run_id}|"

threadpoolexecutor = concurrent.futures.ThreadPoolExecutor(
    max_workers=3)
synchronous_thread = SynchronousThread()

forecast_handler = ForecastHandler(
    threadpoolexecutor, synchronous_thread)
forecast_handler.session = store.session

hazard_preparation_handler = HazardPreparationHandler(
    threadpoolexecutor, synchronous_thread)
hazard_preparation_handler.session = store.session

hazard_handler = HazardHandler(
    threadpoolexecutor, synchronous_thread)
hazard_handler.session = store.session
