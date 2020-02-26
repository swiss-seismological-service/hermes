# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Forecast executing related engine facilities.
"""
from copy import deepcopy
import traceback
import sys
from datetime import datetime
import logging

from sqlalchemy.orm import joinedload, subqueryload
from sqlalchemy import inspect
from PyQt5.QtCore import (pyqtSignal, QObject, QThreadPool, QRunnable,
                          pyqtSlot)

from RAMSIS.core.engine.forecastexecutor import \
    SeismicityModelRunPoller, SeismicityModelRunExecutor,\
    ModelRuns, forecast_scenarios,\
    dispatched_seismicity_model_runs, CatalogSnapshot, WellSnapshot,\
    FlattenTask
from RAMSIS.core.engine.hazardexecutor import CreateHazardModelRunDir, \
    CreateHazardModelRuns, OQFiles, UpdateHazardRuns, \
    OQLogicTree, OQSourceModelFiles
from ramsis.datamodel.seismicity import SeismicityModelRun, \
    ReservoirSeismicityPrediction
from ramsis.datamodel.forecast import Forecast, ForecastScenario, \
    EStage, SeismicityForecastStage, HazardStage
from ramsis.datamodel.status import EStatus
from ramsis.datamodel.seismics import SeismicCatalog
from ramsis.datamodel.well import InjectionWell, WellSection
from ramsis.datamodel.hydraulics import InjectionPlan, Hydraulics
from ramsis.datamodel.project import Project
from ramsis.datamodel.hazard import HazardModelRun

import prefect
from prefect import Flow, Parameter, unmapped
from prefect.engine.executors import LocalDaskExecutor
from prefect.engine.result import NoResultType


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
    print("removed the session")
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
            subqueryload(SeismicityModelRun.result)).\
        filter(Forecast.id == forecast_id)
    forecast = forecast_query.one()
    print("made the query")
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


class BaseHandler(QObject):
    """
    Handles status changes and results emitted from prefect
    flows. SQLalchemy model objects that are returned are
    merged back into the database and pyqt signals alert the
    GUI to display changes.

    This class is initialized at the same time as the Engine,
    so the session is attached later.

    Prefect status handlers follow the form:
    :param obj: The task that the status update is from
    :param old_state: prefect.engine.state
    :param new_state: prefect.engine.state
    """
    execution_status_update = pyqtSignal(object)
    forecast_status_update = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.session = None

    def update_db(self):
        if self.session.dirty:
            print("committing")
            self.session.commit()
        else:
            print("not committing", self.session().dirty)
        self.session.remove()

    def state_evaluator(self, new_state, func_list):
        conditions_met = True
        for func in func_list:
            if not func(new_state):
                conditions_met = False
        return conditions_met

    def task_finished(self, new_state):
        conditions_met = False
        if (new_state.is_finished() and not
            new_state.is_skipped() and not
            new_state.is_mapped() and not
                new_state.is_looped()):
            conditions_met = True
        return conditions_met

    def successful_result(self, new_state):
        conditions_met = False
        if (new_state.is_successful() and not
                isinstance(new_state.result, NoResultType)):
            conditions_met = True
        return conditions_met

    def error_result(self, new_state):
        conditions_met = False
        if (new_state.is_failed() and not
                isinstance(new_state.result, NoResultType)):
            conditions_met = True
        return conditions_met


class ForecastHandler(BaseHandler):
    """
    Handles status changes and results emitted from prefect
    flows. SQLalchemy model objects that are returned are
    merged back into the database and pyqt signals alert the
    GUI to display changes.

    This class is initialized at the same time as the Engine,
    so the session is attached later.

    Prefect status handlers follow the form:
    :param obj: The task that the status update is from
    :param old_state: prefect.engine.state
    :param new_state: prefect.engine.state
    """
    @staticmethod
    def scenario_stage_status(scenario):
        # If all model runs are complete without error, then the
        stage = scenario[EStage.SEISMICITY]
        # stage is a success
        model_success = all([
            True if model.status.state == EStatus.COMPLETE else False
            for model in [r for r in stage.runs if r.enabled]])
        if model_success:
            stage.status.state = EStatus.COMPLETE
        else:
            stage.status.state = EStatus.ERROR

        # If all stages are complete without error, then the
        # scenario is a success
        stage_states = [stage.status.state for stage in [s for s in scenario.stages if s.enabled]]
        if all([state == EStatus.COMPLETE
                for state in stage_states]):
            scenario.status.state = EStatus.COMPLETE
        elif any([state == EStatus.ERROR
                for state in stage_states]):
            scenario.status.state = EStatus.ERROR
        elif any([state == EStatus.PENDING
                for state in stage_states]):
            scenario.status.state = EStatus.RUNNING

        return scenario

    def flow_state_handler(self, obj, old_state, new_state):
        """
        Set the forecast state according to the end state
        of the flow.
        """
        forecast_id = prefect.context.forecast_id
        forecast = self.session.query(Forecast).filter(
            Forecast.id == forecast_id).first()

        if new_state.is_running():
            forecast.status.state = EStatus.RUNNING
            for scenario in forecast.scenarios:
                if scenario.enabled:
                    scenario.status.state = EStatus.RUNNING
            self.update_db()

        elif new_state.is_finished():
            for scenario in forecast.scenarios:
                scenario = self.scenario_stage_status(scenario)

            self.update_db()
            self.session.remove()
        return new_state

    def scenario_models_state_handler(self, obj, old_state, new_state):
        """
        Set the model runs status to RUNNING when this task suceeds.
        """
        if self.state_evaluator(new_state, [self.task_finished,
                                            self.successful_result]):
            model_runs = new_state.result
            for run in model_runs:
                run.status.state = EStatus.RUNNING
                self.session.commit()
            self.update_db()
        return new_state

    def model_run_state_handler(self, obj, old_state, new_state):
        """
        The seismicity model run task sends a Sucessful state
        when the remote model worker has accepted a task.
        A Failed state is sent from the task otherwise.

        A pyqt signal will be sent on success or failure of the task.
        """
        logger = prefect.context.get("logger")

        if self.state_evaluator(new_state, [self.task_finished]):
            if self.state_evaluator(new_state, [self.successful_result]):
                model_run = new_state.result

                update_model_run = self.session.query(SeismicityModelRun).\
                    filter(SeismicityModelRun.id == model_run.id).first()
                update_model_run.runid = model_run.runid
                logger.info(f"Model run with runid={model_run.runid}"
                            "has been dispatched to the remote worker.")
                update_model_run.status.state = model_run.status.state
            elif self.state_evaluator(new_state, [self.error_result]):
                # prefect Fail should be raised with model_run as a result
                logger.warning(f"Model run has failed: {new_state.result}. "
                               f"Message: {new_state.message}")
                model_run = new_state.result
                update_model_run = self.session.query(SeismicityModelRun).\
                    filter(SeismicityModelRun.id == model_run.id).first()
                update_model_run.status.state = EStatus.ERROR

            # The sent status is not used, as the whole scenario must
            # be refreshed from the db in the gui thread.
            self.update_db()
            logger.info("execution status... {}".format(self.execution_status_update))
            print("execution status update", self.execution_status_update)
            self.execution_status_update.emit((
                new_state, type(model_run),
                model_run.id))
        return new_state

    def poll_seismicity_state_handler(self, obj, old_state, new_state):
        """
        The polling task sends a Sucessful state when the remote
        model worker has returned a forecast and this has been
        deserialized sucessfully. A Failed state is sent from the
        task otherwise.
        A pyqt signal will be sent on success or failure of the task.
        """
        logger = prefect.context.get("logger")

        if self.state_evaluator(new_state, [self.task_finished]):
            if self.state_evaluator(new_state, [self.successful_result]):
                model_run, model_result = new_state.result
                logger.info(f"Model with runid={model_run.runid} "
                            "has returned without error from the "
                            "remote worker.")
                update_model_run = self.session.query(SeismicityModelRun).\
                    filter(SeismicityModelRun.id == model_run.id).first()
                print("Updating the model run to complete")
                update_model_run.status.state = EStatus.COMPLETE
                update_model_run.result = model_result
                print("model run state: ", update_model_run.status.state)

            elif self.state_evaluator(new_state, [self.error_result]):
                model_run = new_state.result
                logger.error(f"Model with runid={model_run.runid}"
                             "has returned an error from the "
                             "remote worker.")
                update_model_run = self.session.query(SeismicityModelRun).\
                    filter(SeismicityModelRun.id == model_run.id).first()
                update_model_run.status.state = EStatus.ERROR
            print("session dirty", self.session.dirty)
            self.update_db()
            self.execution_status_update.emit((
                new_state, type(model_run),
                model_run.id))
            print("model run state: ", update_model_run.status.state)
        return new_state

    def catalog_snapshot_state_handler(self, obj, old_state, new_state):
        """
        When the catalog snapshot task has been skipped, then the forecast
        already has a catalog snapshot and this is not overwritten.
        If this task has completed successfully, the new snapshot is added
        to the session and forecast merged as an attribute was modified.
        """
        logger = prefect.context.get("logger")
        if self.state_evaluator(new_state, [self.task_finished,
                                            self.successful_result]):
            forecast = new_state.result
            # A forecast may only have one seismiccatalog associated
            # This is enforced in code rather than at db level.
            assert(len(forecast.seismiccatalog) == 1)
            if forecast.seismiccatalog[0] not in self.session():
                self.session.add(forecast.seismiccatalog[0])
                self.session.commit()
                self.session.merge(forecast)
                self.update_db()
                logger.info(f"Forecast id={forecast.id} has made a snapshot"
                            " of the seismic catalog")
            else:
                logger.info(f"Forecast id={forecast.id} already has a snapshot"
                            " of the seismic catalog. "
                            "No new snapshot is being made.")
        self.session.remove()
        return new_state

    def well_snapshot_state_handler(self, obj, old_state, new_state):
        """
        When the well snapshot task has been skipped, then the forecast
        already has a well snapshot and this is not overwritten.
        If this task has completed successfully, the new snapshot is added
        to the session and forecast merged as an attribute was modified.
        """
        logger = prefect.context.get("logger")
        if self.state_evaluator(new_state, [self.task_finished,
                                            self.successful_result]):
            forecast = new_state.result
            # A forecast may only have one well associated
            # This is enforced in code rather than at db level.
            assert(len(forecast.well) == 1)
            if forecast.seismiccatalog[0] not in self.session():
                self.session.add(forecast.well[0])
                self.session.commit()
                self.session.merge(forecast)
                logger.info(f"Forecast id={forecast.id} already has a snapshot"
                            " of the well. "
                            "No new snapshot is being made.")
                self.update_db()
        return new_state


class HazardHandler(BaseHandler):
    """
    Handles status changes and results emitted from prefect
    flows. SQLalchemy model objects that are returned are
    merged back into the database and pyqt signals alert the
    GUI to display changes.

    This class is initialized at the same time as the Engine,
    so the session is attached later.

    Prefect status handlers follow the form:
    :param obj: The task that the status update is from
    :param old_state: prefect.engine.state
    :param new_state: prefect.engine.state
    """
    @staticmethod
    def scenario_stage_status(scenario):
        # If all model runs are complete without error, then the
        stage = scenario[EStage.HAZARD]
        # stage is a success
        model_success = all([
            True if model.status.state == EStatus.COMPLETE else False
            for model in [r for r in stage.runs if r.enabled]])
        if model_success:
            stage.status.state = EStatus.COMPLETE
        else:
            stage.status.state = EStatus.ERROR

        # If all stages are complete without error, then the
        # scenario is a success
        # TODO sarsonl: need to check that not only is the stage enabled,
        # but also that there are models/model runs associated
        stage_success = all([
            True if stage.status.state == EStatus.COMPLETE else False
            for stage in [s for s in scenario.stages if s.enabled]])
        if stage_success:
            scenario.status.state = EStatus.COMPLETE
        else:
            scenario.status.state = EStatus.ERROR

        return scenario

    def flow_state_handler(self, obj, old_state, new_state):
        """
        Set the forecast state according to the end state
        of the flow.
        """
        forecast_id = prefect.context.forecast_id
        forecast = self.session.query(Forecast).filter(
            Forecast.id == forecast_id).first()

        if new_state.is_running():
            forecast.status.state = EStatus.RUNNING
            for scenario in forecast.scenarios:
                if scenario.enabled:
                    scenario.status.state = EStatus.RUNNING
            self.update_db()

        elif new_state.is_finished():
            for scenario in forecast.scenarios:
                scenario = self.scenario_stage_status(scenario)
            self.update_db()
            self.session.remove()
        return new_state

    def update_db(self):
        if self.session.dirty:
            self.session.commit()
        self.session.remove()

    def create_hazard_models_state_handler(self, obj, old_state, new_state):
        """
        """
        logger = prefect.context.get("logger")
        if self.state_evaluator(new_state, [self.task_finished,
                                            self.successful_result]):
            runs = new_state.result
            for run in runs:
                self.session.add(run)
                self.update_db()
        return new_state

    def update_hazard_models_state_handler(self, obj, old_state, new_state):
        """
        """
        logger = prefect.context.get("logger")
        if self.state_evaluator(new_state, [self.task_finished,
                                            self.successful_result]):
            runs = new_state.result
            for run in runs:
                print("run in haz runs: ", run.id)
                #print('dirty', self.session.dirty, run.id)
                print("about to find tha haz run", run.id)
                hazard_run = self.session.query(HazardModelRun).filter(HazardModelRun.id==run.id).first()
                print("after to find tha haz run", run.id)
                #hazard_run.seismicitymodelruns = run.seismicitymodelruns

                #print("after assigning seismicity to the haz run", run.id)
                for seis_run in run.seismicitymodelruns:
                    update_seis_run = self.session.query(SeismicityModelRun).filter(SeismicityModelRun.id==seis_run.id).first()
                    update_seis_run.hazardruns.append(hazard_run)
                    self.update_db()
                print("have updated db for model run:", run.id)
        return new_state

    #def prepare_inputs_state_handler(self, obj, old_state, new_state):
    #    """
    #    """
    #    logger = prefect.context.get("logger")
    #    if not isinstance(new_state.result, NoResultType) and new_state.is_finished() and new_state.is_successful() and not new_state.is_skipped() and not new_state.is_mapped():
    #        run = new_state.result
    #        print("update state handler: ", run)
    #        hazard_run = self.session.query(HazardModelRun).filter(HazardModelRun.id==run.id).first()
    #        hazard_run.status.state = EStatus.
    #        self.update_db()
    #    return new_state

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
            # Dispatch the model runs to remote workers
            model_run_executor = SeismicityModelRunExecutor(
                state_handlers=[self.forecast_handler.model_run_state_handler])

            _ = model_run_executor.map(
                unmapped(forecast), model_runs_flattened)

            # Check which model runs are dispatched, where there may exist
            # model runs that were sent that still haven't been collected
            dispatched_model_runs = dispatched_seismicity_model_runs(
                forecast)

            # Add dependency so that SeismicityModelRunExecutor must complete
            # before checking for model runs with DISPATCHED status
            seismicity_flow.add_edge(
                seismicity_flow.get_tasks('SeismicityModelRunExecutor')[0],
                seismicity_flow.get_tasks(
                    'dispatched_seismicity_model_runs')[0])

            # Poll the remote workers for tasks that have been completed.
            model_run_poller = SeismicityModelRunPoller(
                state_handlers=[
                    self.forecast_handler.poll_seismicity_state_handler])
            model_run_poller.map(unmapped(forecast),
                                 dispatched_model_runs)
    
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
        print('haz handler', hazard_handler)
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





        # (sarsonl) To view DAG: hazard_flow.visualize()
        #hazard_flow.visualize()

        executor = LocalDaskExecutor(scheduler='threads')
        with prefect.context(forecast_id=self.forecast.id):
            hazard_flow.run(parameters=dict(forecast=self.forecast,
                                                data_dir=self.data_dir
                                                ),
                                executor=executor)

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
        self.forecast_handler = ForecastHandler()
        self.hazard_handler = HazardHandler()

    def run(self, t, forecast_id):
        """
        Runs the forecast with a prefect flow.

        The :class:`~RAMSIS.core.taskmanager.ForecastTask` invokes this
        whenever a new forecast is due.

        :param datetime t: Time of invocation
        :param forecast: Forecast to execute
        :type forecast: ramsis.datamodel.forecast.Forecast
        """
        print("called the engine")
        assert self.core.project
        if not self.session:
            self.session = self.core.store.session
        app_settings = self.core._settings
        if app_settings:
            try:
                data_dir = app_settings['data_dir']
            except KeyError:
                data_dir = None

        self.forecast_handler.session = self.session
        self.hazard_handler.session = self.session
        flow_runner = FlowRunner(forecast_id, self.session, data_dir,
                                 self.forecast_handler, self.hazard_handler)
        worker = Worker(flow_runner.run)
        print("starting the worker")
        self.threadpool.start(worker)

class FlowRunner:
    def __init__(self, forecast_id, session, data_dir,
                 forecast_handler, hazard_handler):
        self.forecast_id = forecast_id
        self.session = session
        self.data_dir = data_dir
        self.system_time = datetime.now()
        self.logger = logging.getLogger()
        self.forecast_handler = forecast_handler
        self.hazard_handler = hazard_handler

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
        print("before seismicity stage states", seismicity_stage_states)
        if any(state==EStatus.ERROR for state in seismicity_stage_states):
            self.update_forecast_status(EStatus.ERROR)
            raise ValueError("One or more seismicity stages has a state "
                    "of ERROR. The next stages cannot continue")
        elif any(state!=EStatus.COMPLETE for state in seismicity_stage_states):
            forecast_flow = ForecastFlow(forecast_input,
                                     self.system_time,
                                     self.forecast_handler)
            forecast_flow.run()
            seismicity_stage_states = self.stage_states(EStage.SEISMICITY)
            print("after seismicity flow, states:", seismicity_stage_states)
        return seismicity_stage_states

    def hazard_flow(self, seismicity_stage_states):
        forecast = forecast_for_hazard(self.forecast_id, self.session)
        hazard_stage_states = self.stage_states(EStage.HAZARD)
        print("hazard stage states: ", hazard_stage_states)
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
        print("running the flow handler")
        forecast_input = forecast_for_seismicity(self.forecast_id, self.session)
        print("got the forecast_input")
        assert forecast_input.status.state != EStatus.COMPLETE
        self.update_forecast_status(EStatus.RUNNING)
        print("updted the forecast status")

        print("starting the seismicity flow assessment")
        seismicity_stage_states = self.seismicity_flow(forecast_input)

        print("starting the hazard flow assessment")
        hazard_stage_states = self.hazard_flow(seismicity_stage_states)
        # Alter forecast status
        
        stage_statuses = []
        for status_list in [seismicity_stage_states, hazard_stage_states]:
            stage_statuses.extend(status_list)
        
        print("status list", stage_statuses)
        if all(status==EStatus.COMPLETE for status in stage_statuses):
            print("marking forecast as complete")
            self.update_forecast_status(EStatus.COMPLETE)
        else:
            print("marking forecast as error")
            self.update_forecast_status(EStatus.ERROR)
