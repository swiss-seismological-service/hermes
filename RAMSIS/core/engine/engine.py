# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Forecast executing related engine facilities.
"""
import time
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
    OQHazardModelRunPoller, dispatched_model_runs_scenario,\
    get_hazard_model_runs_prepared
from RAMSIS.core.engine.state_handlers import ForecastHandler, \
    HazardHandler, HazardPreparationHandler
from ramsis.datamodel.seismicity import SeismicityModelRun, \
    ReservoirSeismicityPrediction
from ramsis.datamodel.forecast import Forecast, ForecastScenario, \
    EStage, SeismicityForecastStage, HazardStage
from ramsis.datamodel.project import Project
from ramsis.datamodel.status import EStatus
from ramsis.datamodel.hazard import HazardModelRun, HazardMap, HazardCurve,\
    HazardPointValue

import prefect
from prefect import Flow, Parameter, unmapped
from prefect.engine.executors import LocalDaskExecutor


class WorkerSignals(QObject):
    """
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

    """
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    """
    Worker thread

    Inherits from QRunnable to handler worker thread setup,
    signals and wrap-up.

    :param callback: The function callback to run on this
        worker thread. Supplied args and
        kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    """

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
        else:
            self.signals.result.emit(result)
            self.signals.finished.emit()  # Done


def get_forecast_no_children(forecast_id, session):
    """
    For use when forecast with status needs to be queried.
    """
    forecast = session.query(Forecast).\
        options(joinedload(Forecast.status)).\
        filter(Forecast.id == forecast_id)
    return forecast.one()


def forecast_for_seismicity(forecast_id, session):
    """
    Returns the forecast for seismicity forcast flow.
    The forecast table is joined to all the tables required.
    """
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
        options(
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                HazardStage)).\
            subqueryload(HazardStage.runs).\
            subqueryload(HazardModelRun.hazardmaps).\
            subqueryload(HazardMap.samples).\
            subqueryload(HazardPointValue.geopoint)).\
        options(
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                HazardStage)).\
            subqueryload(HazardStage.runs).\
            subqueryload(HazardModelRun.hazardcurves).\
            subqueryload(HazardCurve.samples).\
            subqueryload(HazardPointValue.geopoint)).\
        filter(Forecast.id == forecast_id)
    forecast = forecast_query.one()
    session.remove()
    return forecast


def scenario_for_hazard(scenario_id, session):
    session.remove()
    scenario_query = session.query(ForecastScenario).\
        options(subqueryload(ForecastScenario.forecast)).\
        options(
            subqueryload(ForecastScenario.forecast).
            subqueryload(Forecast.project)).\
        options(
            # Load catalogs linked to forecast and project
            subqueryload(ForecastScenario.forecast).\
            subqueryload(Forecast.status)).\
        options(
            # Load status of seismicity stage
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage))).\
        options(
            # Load result attributes for model runs (these will be written to)
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage)).\
            subqueryload(SeismicityForecastStage.runs).\
            subqueryload(SeismicityModelRun.result).\
            subqueryload(ReservoirSeismicityPrediction.samples)).\
        options(
            # Load models from seismicity stage
            subqueryload(ForecastScenario.stages.of_type(
                HazardStage)).\
            subqueryload(HazardStage.runs).\
            subqueryload(HazardModelRun.hazardmaps).\
            subqueryload(HazardMap.samples).\
            subqueryload(HazardPointValue.geopoint)).\
        options(
            subqueryload(ForecastScenario.stages.of_type(
                HazardStage)).\
            subqueryload(HazardStage.runs).\
            subqueryload(HazardModelRun.hazardcurves).\
            subqueryload(HazardCurve.samples).\
            subqueryload(HazardPointValue.geopoint)).\
        options(
            # Load models from seismicity stage
            subqueryload(ForecastScenario.stages.of_type(
                HazardStage)).\
            subqueryload(HazardStage.model)).\
        options(
            # Remove this section, not needed as have new table.
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage)).\
            subqueryload(SeismicityForecastStage.runs).\
            subqueryload(SeismicityModelRun.hazardruns)).\
        filter(ForecastScenario.id == scenario_id)
    scenario = scenario_query.one()
    session.remove()
    return scenario


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

            model_run_executor = SeismicityModelRunExecutor(
                state_handlers=[self.forecast_handler.model_run_state_handler])

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
                    self.forecast_handler.poll_seismicity_state_handler])
            model_run_poller.map(unmapped(forecast),
                                 model_runs_dispatched)

        # (sarsonl) To view DAG: seismicity_flow.visualize()
        executor = LocalDaskExecutor(scheduler='threads')
        with prefect.context(forecast_id=self.forecast.id):
            seismicity_flow.run(parameters=dict(forecast=self.forecast,
                                                ),
                                executor=executor)


class HazardPreparationFlow(QObject):
    """
    Contains prefect flow logic for creating DAG.
    This DAG runs tasks that prepare the model runs for
    hazard stage.
    A flow is created for every forecast that is run by the
    engine.
    """
    def __init__(self, scenario, hazard_handler, data_dir):
        super().__init__()
        self.hazard_handler = hazard_handler
        self.scenario = scenario
        self.data_dir = data_dir

    def run(self):
        with Flow("Hazard_Preparation_Execution",
                  state_handlers=[self.hazard_handler.flow_state_handler]
                  ) as prepared_hazard_flow:
            scenario = Parameter('scenario')
            data_dir = Parameter('data_dir')
            # Start Hazard stage
            hazard_runs = CreateHazardModelRuns(
                state_handlers=[self.hazard_handler.
                                create_hazard_models_state_handler])
            hazard_model_runs = hazard_runs(scenario)

            update_hazard_runs = UpdateHazardRuns(
                state_handlers=[
                    self.hazard_handler.update_hazard_models_state_handler])
            haz_model_runs_updated = update_hazard_runs(hazard_model_runs)

            create_oq_directories = CreateHazardModelRunDir()
            oq_input_dir = create_oq_directories.map(unmapped(data_dir),
                                                     haz_model_runs_updated)
            oq_static_files = OQFiles()
            oq_static_files.map(haz_model_runs_updated, oq_input_dir)

            oq_source_models = OQSourceModelFiles()
            source_model_xml_basenames = oq_source_models.map(
                haz_model_runs_updated, oq_input_dir)

            oq_logic_tree = OQLogicTree()
            oq_logic_tree.map(haz_model_runs_updated, oq_input_dir,
                              source_model_xml_basenames)
            prepared_hazard_flow.add_edge(
                prepared_hazard_flow.get_tasks('OQFiles')[0],
                prepared_hazard_flow.get_tasks('OQLogicTree')[0])

        executor = LocalDaskExecutor(scheduler='threads')
        with prefect.context(scenario_id=self.scenario.id):
            prepared_hazard_flow.run(parameters=dict(scenario=self.scenario,
                                                     data_dir=self.data_dir),
                                     executor=executor)


class HazardFlow(QObject):
    """
    Contains prefect flow logic for creating DAG.
    A flow is created for every forecast that is run by the
    engine.
    """
    def __init__(self, scenario, hazard_handler, data_dir):
        super().__init__()
        self.hazard_handler = hazard_handler
        self.scenario = scenario
        self.data_dir = data_dir

    def run(self):
        with Flow("Hazard_Execution",
                  state_handlers=[self.hazard_handler.flow_state_handler]
                  ) as hazard_flow:
            scenario = Parameter('scenario')
            data_dir = Parameter('data_dir')

            model_runs_prepared = get_hazard_model_runs_prepared(scenario)
            model_run_executor = OQHazardModelRunExecutor(
                state_handlers=[self.hazard_handler.model_run_state_handler])

            _ = model_run_executor.map(
                model_runs_prepared, unmapped(scenario),
                unmapped(data_dir))
            # Check which model runs are dispatched, where there may exist
            # model runs that were sent that still haven't been collected
            model_runs_dispatched = dispatched_model_runs_scenario(

                scenario, EStage.HAZARD)

            # Add dependency so that HazardModelRunExecutor must complete
            # before checking for model runs with DISPATCHED status
            hazard_flow.add_edge(
                hazard_flow.get_tasks('OQHazardModelRunExecutor')[0],
                hazard_flow.get_tasks('dispatched_model_runs_scenario')[0])

            # Poll the remote workers for tasks that have been completed.
            model_run_poller = OQHazardModelRunPoller(
                state_handlers=[
                    self.hazard_handler.poll_hazard_state_handler])
            model_run_poller.map(unmapped(scenario),
                                 model_runs_dispatched)

        # (sarsonl) To view DAG: hazard_flow.visualize()
        # hazard_flow.visualize()

        executor = LocalDaskExecutor(scheduler='threads')
        with prefect.context(scenario_id=self.scenario.id):
            print("running hazard flow")
            hazard_flow.run(parameters=dict(scenario=self.scenario,
                                            data_dir=self.data_dir),
                            executor=executor)


class SynchronousThread:
    """
    Class for managing db tasks which should be done synchronously
    but in a thread in threadpool. Tasks which involve loading the forecast
    or project are required to finish before the next
    one is started as the same object cannot be loaded by different
    sessions in sqlalchemy.
    """

    def __init__(self):
        self.thread_reserved = False
        self.model_runs = 0
        self.model_runs_count = 0

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

        self.flow_runner = FlowRunner(forecast_id, self.session, data_dir)
        worker = Worker(self.flow_runner.run)
        self.flow_runner.forecast_handler.execution_status_update.connect(
            self.on_executor_status_changed)
        self.flow_runner.hazard_handler.execution_status_update.connect(
            self.on_executor_status_changed)
        self.flow_runner.hazard_preparation_handler.\
            execution_status_update.connect(
                self.on_executor_status_changed)

        self.threadpool.start(worker)

    def on_executor_status_changed(self, status):
        """
        Handle status changes from the executor chain

        :param RAMSIS.core.tools.executor.ExecutionStatus status: Status
        """
        # if status.origin == self._forecast_executor:
        #     done = [ExecutionStatus.Flag.SUCCESS, ExecutionStatus.Flag.ERROR]
        #     if status.flag in done:
        #         self.busy = False
        #         self.forecast_complete.emit()
        self.execution_status_update.emit(status)


class FlowRunner:
    def __init__(self, forecast_id, session, data_dir):
        self.threadpool = QThreadPool()
        self.synchronous_thread = SynchronousThread()
        self.forecast_id = forecast_id
        self.session = session
        self.data_dir = data_dir
        self.system_time = datetime.now()
        self.logger = logging.getLogger()
        self.forecast_handler = ForecastHandler(
            self.threadpool, self.synchronous_thread)
        self.hazard_preparation_handler = HazardPreparationHandler(
            self.threadpool, self.synchronous_thread)
        self.hazard_handler = HazardHandler(
            self.threadpool, self.synchronous_thread)
        self.forecast_handler.session = self.session
        self.hazard_handler.session = self.session
        self.hazard_preparation_handler.session = self.session
        self.stage_results = []

    def update_forecast_status(self, estatus):
        forecast = self.session.query(Forecast).filter(
            Forecast.id == self.forecast_id).first()
        forecast.status.state = estatus
        self.session.commit()
        self.session.remove()

    def stage_states(self, estage):
        forecast = self.session.query(Forecast).filter(
            Forecast.id == self.forecast_id).first()
        stage_states = []
        for scenario in forecast.scenarios:
            try:
                stage = scenario[estage].status.state
                stage_states.append(stage)
            except KeyError:
                pass
        self.session.remove()
        return stage_states

    def seismicity_flow(self, forecast_input):
        seismicity_stage_states = self.stage_states(EStage.SEISMICITY)
        if any(state == EStatus.ERROR for state in seismicity_stage_states):
            self.update_forecast_status(EStatus.ERROR)
            raise ValueError("One or more seismicity stages has a state "
                             "of ERROR. The next stages cannot continue")
        elif any(state != EStatus.COMPLETE for state in
                 seismicity_stage_states):
            forecast_flow = ForecastFlow(forecast_input,
                                         self.system_time,
                                         self.forecast_handler)
            forecast_flow.run()

            self.threadpool.waitForDone()
            seismicity_stage_states = self.stage_states(EStage.SEISMICITY)
        return seismicity_stage_states

    def hazard_flow(self, seismicity_stage_states, scenario_ref):
        scenario = scenario_for_hazard(scenario_ref.id, self.session)
        seismicity_status = scenario[EStage.SEISMICITY].status.state
        if seismicity_status == EStatus.ERROR:
            self.update_forecast_status(EStatus.ERROR)
            raise ValueError("One or more seismicity stages has a state "
                             "of ERROR. The next stages cannot continue")
        elif seismicity_status != EStatus.COMPLETE:
            self.update_forecast_status(EStatus.ERROR)
            raise ValueError("One or more seismicity stages has a state "
                             "that is not complete. The next stages cannot "
                             "continue")
        hazard_status = scenario[EStage.HAZARD].status.state
        if hazard_status != EStatus.COMPLETE:
            if hazard_status != EStatus.PREPARED:
                hazard_prep_flow = HazardPreparationFlow(
                    scenario, self.hazard_preparation_handler,
                    self.data_dir)
                hazard_prep_flow.run()
                print("waiting for done")
                self.threadpool.waitForDone()
                print("waited for done")
                # Will the hazard status update here?
                if hazard_status == EStatus.ERROR:
                    self.update_forecast_status(EStatus.ERROR)
                    raise ValueError(
                        "One or more seismicity stages has a state "
                        "of ERROR. The next stages cannot continue")
            # Assume that all the hazard stages must be in state PREPARED now,
            # if not ERROR

            scenario = scenario_for_hazard(scenario_ref.id, self.session)
            hazard_flow = HazardFlow(scenario,
                                     self.hazard_handler,
                                     self.data_dir)
            print("#### start hazard flow")
            hazard_flow.run()
            self.threadpool.waitForDone()
            while (self.synchronous_thread.model_runs_count <
                   self.synchronous_thread.model_runs_count):
                time.sleep(5)
            hazard_stage_states = self.stage_states(EStage.HAZARD)
        return hazard_stage_states

    def run_stage(self, forecast_input, estage):
        stage_enabled = False
        try:
            scenarios = forecast_input.scenarios
            for scenario in scenarios:
                if scenario[estage].enabled:
                    stage_enabled = True
        except AttributeError as err:
            print('err...', err)
            pass
        print("stage enabled", stage_enabled)
        return stage_enabled

    def run(self, progress_callback):
        forecast_input = forecast_for_seismicity(self.forecast_id,
                                                 self.session)
        assert forecast_input.status.state != EStatus.COMPLETE
        self.update_forecast_status(EStatus.RUNNING)

        if self.run_stage(forecast_input, EStage.SEISMICITY):
            seismicity_stage_states = self.seismicity_flow(forecast_input)
            self.stage_results.extend(seismicity_stage_states)

        # Run hazard stage per scenario
        for scenario in forecast_input.scenarios:
            try:
                hazard_stage = scenario[EStage.HAZARD]
                if hazard_stage.enabled:

                    hazard_stage_states = self.hazard_flow(
                        seismicity_stage_states,
                        scenario)
                    self.stage_results.extend(hazard_stage_states)
            except KeyError:
                pass
        # Alter forecast status

        if all(status == EStatus.COMPLETE for status in self.stage_results):
            self.update_forecast_status(EStatus.COMPLETE)
        else:
            self.update_forecast_status(EStatus.ERROR)
        print("at the real end of the engine/...")
