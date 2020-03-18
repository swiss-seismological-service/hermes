# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Forecast executing related engine facilities.
"""
import traceback
import sys
from datetime import datetime
import logging

from sqlalchemy.orm import joinedload, subqueryload
from PyQt5.QtCore import (pyqtSignal, QObject, QThreadPool, QRunnable,
                          pyqtSlot)

from RAMSIS.core.engine.forecastexecutor import \
    SeismicityModelRunPoller, SeismicityModelRunExecutor,\
    ModelRuns, forecast_scenarios,\
    dispatched_model_runs, CatalogSnapshot, WellSnapshot,\
    FlattenTask, ScenarioSerializeData, ForecastSerializeData
from RAMSIS.core.engine.hazardexecutor import CreateHazardModelRunDir, \
    CreateHazardModelRuns, OQFiles, UpdateHazardRuns, \
    OQLogicTree, OQSourceModelFiles, OQHazardModelRunExecutor, \
    OQHazardModelRunPoller
from RAMSIS.core.engine.state_handlers import ForecastHandler, \
    HazardHandler
from ramsis.datamodel.seismicity import SeismicityModelRun, \
    ReservoirSeismicityPrediction
from ramsis.datamodel.forecast import Forecast, ForecastScenario, \
    EStage, SeismicityForecastStage, HazardStage
from ramsis.datamodel.project import Project
from ramsis.datamodel.status import EStatus

import prefect
from prefect import Flow, Parameter, unmapped
from prefect.engine.executors import LocalDaskExecutor


class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress

    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup,
    signals and wrap-up.

    :param callback: The function callback to run on this
        worker thread. Supplied args and
        kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            # If an error occurs in a thread, log it but do not propagate.
            #self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
            self.signals.finished.emit()  # Done


# For usage when forecast actually has a status.
def get_forecast_no_children(forecast_id, session):
    forecast = session.query(Forecast).\
        options(joinedload(Forecast.status)).\
        filter(Forecast.id == forecast_id)
    return forecast.one()

def forecast_for_seismicity(forecast_id, session):
    session.remove()
    forecast_query = session.query(Forecast).\
        options(
            # Load catalogs linked to forecast and project
            subqueryload(Forecast.status)).\
        options(
            # Load catalogs linked to forecast and project
            subqueryload(Forecast.seismiccatalog)).\
        options(
            # Load catalogs linked to forecast and project
            subqueryload(Forecast.well)).\
        options(
            subqueryload(Forecast.project).\
            subqueryload(Project.seismiccatalogs)).\
        options(
            subqueryload(Forecast.project).\
            subqueryload(Project.wells)).\
        options(
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.well)).\
        options(
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage))).\
        options(
            # Load result attributes for model runs (these will be written to)
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage)).\
            subqueryload(SeismicityForecastStage.runs).\
            subqueryload(SeismicityModelRun.forecaststage)).\
        options(
            # Load result attributes for model runs (these will be written to)
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage)).\
            subqueryload(SeismicityForecastStage.runs).\
            subqueryload(SeismicityModelRun.result)).\
        filter(Forecast.id == forecast_id)
    forecast = forecast_query.one()
    session.remove()
    return forecast


def forecast_for_hazard(forecast_id, session):
    session.remove()
    forecast_query = session.query(Forecast).\
        options(
            subqueryload(Forecast.project)).\
        options(
            # Load catalogs linked to forecast and project
            subqueryload(Forecast.status)).\
        options(
            # Load status of seismicity stage
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage))).\
        options(
            # Load result attributes for model runs (these will be written to)
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage)).\
            subqueryload(SeismicityForecastStage.runs).\
            subqueryload(SeismicityModelRun.result).\
            subqueryload(ReservoirSeismicityPrediction.samples)).\
        options(
            # Load models from seismicity stage
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                HazardStage)).\
            subqueryload(HazardStage.runs)).\
        options(
            # Remove this section, not needed as have new table.
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage)).\
            subqueryload(SeismicityForecastStage.runs).\
            subqueryload(SeismicityModelRun.hazardruns)).\
        filter(Forecast.id == forecast_id)
    forecast = forecast_query.one()
    session.remove()
    return forecast

class ForecastFlow(QObject):
    """
    Contains prefect flow logic for creating DAG.
    A flow is created for every forecast that is run by the
    engine.
    """
    def __init__(self, forecast, system_time, forecast_handler):
        super().__init__()
        self.forecast_handler = forecast_handler
        self.forecast = forecast
        self.system_time = system_time

    def run(self):
        with Flow("Seismicity_Execution",
                  state_handlers=[self.forecast_handler.flow_state_handler]
                  ) as seismicity_flow:
            forecast = Parameter('forecast')
            # Start Seismicity Stage
            # Snapshot seismicity catalog if required
            catalog_snapshot = CatalogSnapshot(
                state_handlers=[self.forecast_handler.
                                catalog_snapshot_state_handler])
            forecast = catalog_snapshot(forecast, self.system_time)
            
            # Snapshot hydraulic well if required
            well_snapshot = WellSnapshot(
                state_handlers=[self.forecast_handler.
                                well_snapshot_state_handler])
            forecast = well_snapshot(forecast, self.system_time)
            scenarios = forecast_scenarios(
                forecast)

            # Get seismicity model runs
            seismicity_models = ModelRuns(
                state_handlers=[self.forecast_handler.
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
            # As prefect does not allow double nested mapping, have to flatten scenarios data and pass to eash model run executor task. This data should not be large in any case as the majority of the data is in forecast_serialized_data (all catalog and well data)
            # Dispatch the model runs to remote workers
            #flatten_scenario_data = FlattenTask()
            #scenario_data_flattened = flatten_scenario_data(scenario_serialized_data)
            model_run_executor = SeismicityModelRunExecutor(
                state_handlers=[self.forecast_handler.model_run_state_handler])

            _ = model_run_executor.map(
                unmapped(forecast), unmapped(forecast_serialized_data), unmapped(scenario_serialized_data), model_runs_flattened)

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
                    self.forecast_handler.poll_seismicity_state_handler])
            model_run_poller.map(unmapped(forecast),
                                 model_runs_dispatched)
    
        # (sarsonl) To view DAG: seismicity_flow.visualize()
        #seismicity_flow.visualize()

        executor = LocalDaskExecutor(scheduler='threads')
        with prefect.context(forecast_id=self.forecast.id):
            seismicity_flow.run(parameters=dict(forecast=self.forecast,
                                                ),
                                executor=executor)


class HazardFlow(QObject):
    """
    Contains prefect flow logic for creating DAG.
    A flow is created for every forecast that is run by the
    engine.
    """
    def __init__(self, forecast, hazard_handler, data_dir):
        super().__init__()
        self.hazard_handler = hazard_handler
        self.forecast = forecast
        self.data_dir = data_dir

    def run(self):
        with Flow("Seismicity_Execution",
                  state_handlers=[self.hazard_handler.flow_state_handler]
                  ) as hazard_flow:
            forecast = Parameter('forecast')
            data_dir = Parameter('data_dir')
            scenarios_node = forecast_scenarios(
                forecast)
            # Start Hazard stage
            # Load config and validate
            #haz_forecast = Parameter('forecast')
            #scenarios = forecast_scenarios(haz_forecast)
            hazard_runs = CreateHazardModelRuns(
                state_handlers=[self.hazard_handler.\
                                create_hazard_models_state_handler])
            hazard_model_runs = hazard_runs.map(scenarios_node)

            flatten_task = FlattenTask()
            haz_model_runs_flat = flatten_task(hazard_model_runs)

            update_hazard_runs = UpdateHazardRuns(state_handlers=[self.hazard_handler.update_hazard_models_state_handler])
            haz_model_runs_updated = update_hazard_runs(haz_model_runs_flat)

            create_oq_directories = CreateHazardModelRunDir()
            oq_input_dir = create_oq_directories.map(unmapped(data_dir),
                                                     haz_model_runs_updated)
            oq_static_files = OQFiles()
            oq_static_files.map(haz_model_runs_updated, oq_input_dir)

            oq_source_models = OQSourceModelFiles()
            source_model_xml_basenames = oq_source_models.map(haz_model_runs_updated, oq_input_dir)

            oq_logic_tree = OQLogicTree()
            oq_logic_tree.map(haz_model_runs_updated, oq_input_dir, source_model_xml_basenames)
            hazard_flow.add_edge(
                hazard_flow.get_tasks('OQFiles')[0],
                hazard_flow.get_tasks('OQLogicTree')[0])

            
            model_run_executor = OQHazardModelRunExecutor(state_handlers=[self.hazard_handler.model_run_state_handler])

            _ = model_run_executor(haz_model_runs_updated, source_model_xml_basenames,
                oq_input_dir)
            hazard_flow.add_edge(
                    hazard_flow.get_tasks('OQLogicTree')[0],
                hazard_flow.get_tasks('OQHazardModelRunExecutor')[0])

            # Check which model runs are dispatched, where there may exist
            # model runs that were sent that still haven't been collected
            model_runs_dispatched = dispatched_model_runs(
                forecast, EStage.HAZARD)

            # Add dependency so that HazardModelRunExecutor must complete
            # before checking for model runs with DISPATCHED status
            hazard_flow.add_edge(
                hazard_flow.get_tasks('OQHazardModelRunExecutor')[0],
                hazard_flow.get_tasks('dispatched_model_runs')[0])

            # Poll the remote workers for tasks that have been completed.
            model_run_poller = OQHazardModelRunPoller(
                state_handlers=[
                    self.hazard_handler.poll_hazard_state_handler])
            model_run_poller.map(unmapped(forecast),
                                 model_runs_dispatched)


        # (sarsonl) To view DAG: hazard_flow.visualize()
        #hazard_flow.visualize()

        executor = LocalDaskExecutor(scheduler='threads')
        with prefect.context(forecast_id=self.forecast.id):
            hazard_flow.run(parameters=dict(forecast=self.forecast,
                                                data_dir=self.data_dir
                                                ),
                                executor=executor)
class SynchronousThread:
    """
    Class for managing db tasks which should be done synchronously
    but in a thread in threadpool. Tasks which involve loading the forecast or project are required to finish before the next
    one is started as the same object cannot be loaded by different
    sessions in sqlalchemy.
    """

    def __init__(self):
        self.thread_reserved = False

    def reserve_thread(self):
        self.thread_reserved = True

    def release_thread(self):
        self.thread_reserved = False

    def is_reserved(self):
        return self.thread_reserved

class Engine(QObject):
    """
    The engine is responsible for running forecasts
    """

    #: Emitted whenever any part of a forecast emits a status update. Carries
    #    a :class:`~RAMSIS.core.tools.executor.ExecutionStatus` object.
    execution_status_update = pyqtSignal(object)
    forecast_status_update = pyqtSignal(object)

    def __init__(self, core):
        """
        :param RAMSIS.core.controller.Controller core: Reference to the core
        """
        super().__init__()
        self.threadpool = QThreadPool()
        self.busy = False
        self.core = core
        self.session = None
        #self.synchronous_thread = SynchronousThread()

    def run(self, t, forecast_id):
        """
        Runs the forecast with a prefect flow.

        The :class:`~RAMSIS.core.taskmanager.ForecastTask` invokes this
        whenever a new forecast is due.

        :param datetime t: Time of invocation
        :param forecast: Forecast to execute
        :type forecast: ramsis.datamodel.forecast.Forecast
        """
        assert self.core.project
        if not self.session:
            self.session = self.core.store.session
        app_settings = self.core._settings
        if app_settings:
            try:
                data_dir = app_settings['data_dir']
            except KeyError:
                data_dir = None

        #self.forecast_handler.session = self.session
        #self.hazard_handler.session = self.session
        flow_runner = FlowRunner(forecast_id, self.session, data_dir)
        #                         self.forecast_handler, self.hazard_handler)
        worker = Worker(flow_runner.run)
        self.threadpool.start(worker)

class FlowRunner:
    def __init__(self, forecast_id, session, data_dir):
        self.threadpool = QThreadPool()
        self.synchronous_thread = SynchronousThread()
        self.forecast_id = forecast_id
        self.session = session
        self.data_dir = data_dir
        self.system_time = datetime.now()
        self.logger = logging.getLogger()
        self.forecast_handler = ForecastHandler(self.threadpool, self.synchronous_thread)
        self.hazard_handler = HazardHandler(self.threadpool, self.synchronous_thread)
        self.forecast_handler.session = self.session
        self.hazard_handler.session = self.session

    def update_forecast_status(self, estatus):
        forecast = self.session.query(Forecast).filter(Forecast.id==self.forecast_id).first()
        forecast.status.state = estatus
        self.session.commit()
        self.session.remove()

    def stage_states(self, estage):
        forecast = self.session.query(Forecast).filter(Forecast.id==self.forecast_id).first()
        stage_states = []
        for scenario in forecast.scenarios:
            try:
                stage = scenario[estage].status.state
                stage_states.append(stage)
            except KeyError:
                pass
        return stage_states

    def seismicity_flow(self, forecast_input):
        seismicity_stage_states = self.stage_states(EStage.SEISMICITY)
        if any(state==EStatus.ERROR for state in seismicity_stage_states):
            self.update_forecast_status(EStatus.ERROR)
            raise ValueError("One or more seismicity stages has a state "
                    "of ERROR. The next stages cannot continue")
        elif any(state!=EStatus.COMPLETE for state in seismicity_stage_states):
            forecast_flow = ForecastFlow(forecast_input,
                                     self.system_time,
                                     self.forecast_handler)
            forecast_flow.run()

            forecast = self.session.query(Forecast).first()
            plan_section = forecast.scenarios[0].well.sections[0]
            topz = plan_section.topz_value
            bottomz = plan_section.bottomz_value
            self.session.remove()
            done = self.threadpool.waitForDone()
            seismicity_stage_states = self.stage_states(EStage.SEISMICITY)
        return seismicity_stage_states

    def hazard_flow(self, seismicity_stage_states):
        forecast = forecast_for_hazard(self.forecast_id, self.session)
        hazard_stage_states = self.stage_states(EStage.HAZARD)
        if any(state==EStatus.ERROR for state in seismicity_stage_states):
            self.update_forecast_status(EStatus.ERROR)
            raise ValueError("One or more seismicity stages has a state "
                "of ERROR. The next stages cannot continue")
        if any(state!=EStatus.COMPLETE for state in seismicity_stage_states):
             self.update_forecast_status(EStatus.ERROR)
             raise ValueError("One or more seismicity stages has a state "
                    "that is not complete. The next stages cannot continue")

        if any(state!=EStatus.COMPLETE for state in hazard_stage_states):
            hazard_flow = HazardFlow(forecast,
                                         self.hazard_handler,
                                         self.data_dir)
            hazard_flow.run()

            hazard_stage_states = self.stage_states(EStage.HAZARD)
        return hazard_stage_states

    def run(self, progress_callback):
        forecast_input = forecast_for_seismicity(self.forecast_id, self.session)
        assert forecast_input.status.state != EStatus.COMPLETE
        self.update_forecast_status(EStatus.RUNNING)

        seismicity_stage_states = self.seismicity_flow(forecast_input)

        hazard_stage_states = self.hazard_flow(seismicity_stage_states)
        # Alter forecast status
        
        stage_statuses = []
        for status_list in [seismicity_stage_states, hazard_stage_states]:
            stage_statuses.extend(status_list)
        
        forecast = self.session.query(Forecast).first()
        plan_section = forecast.scenarios[0].well.sections[0]
        topz = plan_section.topz_value
        bottomz = plan_section.bottomz_value
        self.session.remove()
        if all(status==EStatus.COMPLETE for status in stage_statuses):
            self.update_forecast_status(EStatus.COMPLETE)
        else:
            self.update_forecast_status(EStatus.ERROR)
