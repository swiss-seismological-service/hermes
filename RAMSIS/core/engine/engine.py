# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Forecast executing related engine facilities.
"""
from copy import deepcopy
import logging
import traceback
import sys
from datetime import datetime

import sqlalchemy
from sqlalchemy.orm import joinedload, joinedload_all, subqueryload, contains_eager
from random import randint
from PyQt5.QtCore import (pyqtSignal, QObject, QThreadPool, QRunnable,
                          QTimer, QEventLoop, QThread, pyqtSlot)

from RAMSIS.core.tools.executor import ExecutionStatus, ExecutionStatusPrefect
from RAMSIS.core.engine.forecastexecutor import ForecastExecutor,\
    SeismicityForecastStageExecutor,\
    SeismicityModelRunPoller, SeismicityModelRunExecutor,\
    seismicity_models, forecast_scenarios, data_snapshot,\
    dispatched_seismicity_model_runs, DataSnapshot
from ramsis.datamodel.seismicity import SeismicityModelRun
from ramsis.datamodel.forecast import Forecast, ForecastScenario, EStage, SeismicityForecastStage
from ramsis.datamodel.status import Status, EStatus
from ramsis.datamodel.seismics import SeismicCatalog
from ramsis.datamodel.well import InjectionWell, WellSection
from ramsis.datamodel.hydraulics import HydraulicSample, InjectionPlan, Hydraulics
from ramsis.datamodel.project import Project
import prefect
from prefect import task, Task, Flow, Parameter, unmapped
from datetime import timedelta
from prefect.schedules import IntervalSchedule
from prefect.engine.executors import DaskExecutor, LocalDaskExecutor
from dask.distributed import Client
from prefect.engine.result_handlers.result_handler import ResultHandler

class ForecastResultHandler(ResultHandler):
    def __init__(self, session):
        super().__init__()
    def read(self, forecast):
        print("in result handler read", forecast)
        return forecast
    def write(self, forecast):
        print("in result handler!", forecast)
        return forecast

def prefect_estatus_conversion(prefect_status, context=None):
    status_dict = {
        prefect_status.is_pending: EStatus.PENDING,
        prefect_status.is_running: EStatus.RUNNING,
        prefect_status.is_successful: EStatus.COMPLETE,
        prefect_status.is_failed: EStatus.ERROR
                                           }
    model_run_status_dict = {
        prefect_status.is_pending: EStatus.PENDING,
        prefect_status.is_running: EStatus.RUNNING,
        prefect_status.is_successful: EStatus.RUNNING,
        prefect_status.is_failed: EStatus.ERROR
                                           }

    use_dict = model_run_status_dict if context == 'model_run' else status_dict
    estatus = None
    for fnc, val in use_dict.items():
        if fnc():
            estatus = val

    # model runs that have been submitted to a remote worker
    # should show a status of RUNNING if this task completed.
    #if context == 'model_run':
    #    if prefect == EStatus.RUNNING:
    #        estatus = EStatus.PENDING
    #    elif estatus == EStatus.COMPLETE:
    #        print("setting model_run to have estatus of RUNNING rather than COMPLETE")
    #        estatus = EStatus.RUNNING

    #estatus = status_dict.get()
    #if prefect_status.is_pending():
    #    estatus = EStatus.PENDING
    #elif prefect_status.is_running():
    #    estatus = EStatus.RUNNING
    #elif prefect_status.is_successful():
    #    if context == 'model_run':
    #        estatus = EStatus.RUNNING
    #    else:
    #        estatus = EStatus.COMPLETE
    #elif prefect_status.is_failed():
    #    estatus = EStatus.ERROR
    if not estatus:
        print(f"WARNING: prefect status is not handled: {prefect_status}")
    return estatus



@task
def flatten_task(nested_list):
    flattened_list = [item for sublist in nested_list for item in sublist]
    return flattened_list

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
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()  # Done

# For usage when forecast actually has a status.
def get_forecast_no_children(forecast_id, session):
    forecast = session.query(Forecast).\
            options(
                    joinedload(Forecast.status)).\
            filter(Forecast.id == forecast_id)
    return forecast.one()

#schedule = IntervalSchedule(interval=timedelta(minutes=1))
def get_forecast_seismicity(forecast_id, session):
    forecast_query = session.query(Forecast).\
            options(
                    subqueryload(Forecast.project).\
                    subqueryload(Project.wells).\
                    subqueryload(InjectionWell.sections).\
                    subqueryload(WellSection.hydraulics).\
                    subqueryload(Hydraulics.samples)
                    ).\
            options(
                    subqueryload(Forecast.project).\
                    subqueryload(Project.wells).\
                    subqueryload(InjectionWell.sections).\
                    subqueryload(WellSection.injectionplan).\
                    subqueryload(InjectionPlan.samples)
                    ).\
            options(
                    subqueryload(Forecast.scenarios).\
                    subqueryload(ForecastScenario.\
                                 stages.of_type(SeismicityForecastStage)).\
                    subqueryload(SeismicityForecastStage.runs).\
                    subqueryload(SeismicityModelRun.result)
                    ).\
            options(
                    subqueryload(Forecast.seismiccatalog_history)).\
            options(subqueryload(Forecast.well_history)).\
            options(subqueryload(Forecast.scenarios).\
                    subqueryload(ForecastScenario.well_history).\
                    subqueryload(InjectionWell.sections).\
                    subqueryload(WellSection.injectionplan).\
                    subqueryload(InjectionPlan.samples)).\
            filter(Forecast.id == forecast_id)
    forecast = forecast_query.one()
    forecast_copy = deepcopy(forecast)
    session.expunge(forecast)
    return forecast_copy

class ForecastStatus(object):
    def __init__(self, forecast_id, status):
        self.forecast_id
        self.status = status

class ForecastHandler(QObject):

    execution_status_update = pyqtSignal(object)
    forecast_status_update = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.session = None

    def model_run_state_handler(self, obj, old_state, new_state):
        msg = "\nTask state has changed from {0}:\n{1} to {2}\n"
        print("In model run state handler...", msg.format(obj, old_state, new_state), new_state.result)
        #forecast_status = ForecastStatus(obj.id, new_status)
        if new_state.is_finished():
            if new_state.is_successful() and not new_state.is_mapped(): 
                old_model_run = self.session.query(SeismicityModelRun).filter(SeismicityModelRun.id==new_state.result.id).one()
                #print("have got the old model_run object: ", old_model_run, old_model_run.id)
                print("attempting to merge the modelrun object: ", new_state.result)
                self.session.merge(new_state.result)
                self.session.commit()
                self.session.remove()
            self.execution_status_update.emit(new_state.result)
        return new_state

    def poll_seismicity_state_handler(self, obj, old_state, new_state):
        msg = "\nTask state has changed from {0}:\n{1} to {2}\n"
        print("In model run state handler...", msg.format(obj, old_state, new_state), new_state.result)
        #forecast_status = ForecastStatus(obj.id, new_status)
        if new_state.is_finished():
            if new_state.is_successful() and not new_state.is_mapped(): 
                model_run, model_result = new_state.result
                # Make sure old model run is in session before merging new one in.
                print("getting old model run: ", model_run)
                self.session.query(SeismicityModelRun).filter(SeismicityModelRun.id==model_run.id).one()
                print("About to merge model run")
                self.session.merge(model_run)
                print("About to add model result: ", model_result)
                self.session.merge(model_result)
                self.session.commit()
                self.session.remove()
            self.execution_status_update.emit(new_state.result)
        return new_state

    def snapshot_state_handler(self, obj, old_state, new_state):
        msg = "\nTask state has changed from {0}:\n{1} to {2}\n"
        print("In snapshot state handler...", msg.format(obj, old_state, new_state), new_state.result)
        print(dir(new_state), type(new_state))
        if new_state.is_finished():
            if new_state.is_successful():
                forecast, seismiccatalog, well = new_state.result
                #self.session.query(Forecast).filter(Forecast.id==new_state.result.id).one()
                # Is merging correct to do here and does it merge children?
                print("forecast in session", forecast in self.session())
                print("well in session", well in self.session())
                print("catalog in session", seismiccatalog in self.session())
                self.session.merge(forecast)
                print("2 forecast in session", forecast in self.session())
                self.session.add(seismiccatalog)
                print("2, catalog in session", seismiccatalog in self.session())
                self.session.add(well)
                print("2 well in session", well in self.session())
                self.session.commit()
                self.session.remove()
                print("3 forecast in session", forecast in self.session())
            self.execution_status_update.emit(new_state.result)
        return new_state

    def forecast_state_handler(self, obj, old_state, new_state):
        msg = "\nTask state has changed from {0}:\n{1} to {2}\n"
        print("In state handler...", msg.format(obj, old_state, new_state), new_state.result)
        print(dir(new_state), type(new_state))
        if new_state.is_finished():
            self.session.query(Forecast).filter(Forecast.id==new_state.result.id).one()
            self.session.merge(new_state.result)
            self.session.commit()
            self.session.remove()
        self.execution_status_update.emit(new_state.result)
        return new_state

class ForecastFlow(QObject):
    def __init__(self, forecast, system_time, forecast_handler):
        self.forecast = forecast
        self.system_time = system_time
        self.forecast_handler = forecast_handler

    def run(self, progress_callback):
        with Flow("Seismicity_Execution") as seismicity_flow:
            data_snapshot = DataSnapshot(
                state_handlers=[self.forecast_handler.snapshot_state_handler])
            forecast_data = data_snapshot(self.forecast, self.system_time)
            scenarios = forecast_scenarios(
                forecast_data)
            model_runs = seismicity_models.map(
                scenarios)

            model_runs_flattened = flatten_task(model_runs)
            
            model_run_executor = SeismicityModelRunExecutor(
                state_handlers=[self.forecast_handler.model_run_state_handler])
            #seismicity_flow.add_edge(model_run_executor.map(
            #    unmapped(self.session), model_runs_flattened),
            #    
            #    model_run_poller.map(unmapped(self.session), model_runs_flattened))
            models = dispatched_seismicity_model_runs(forecast_data)
            executed_model_runs = model_run_executor.map(unmapped(forecast_data), models)
            seismicity_flow.add_edge(seismicity_flow.get_tasks('flatten_task')[0],
                    seismicity_flow.get_tasks('dispatched_seismicity_model_runs')[0])
                #forecast_data).set_upstream(dispatched_seismicity_model_runs(forecast_data), mapped=True, key='model_run')
            model_run_poller = SeismicityModelRunPoller(state_handlers=[self.forecast_handler.poll_seismicity_state_handler])
            poll_results = model_run_poller.map(unmapped(forecast_data), executed_model_runs)

        #seismicity_flow.visualize()
        
        #client = Client(n_workers=1, threads_per_worker=2)
        executor = LocalDaskExecutor(scheduler='threads')
        #executor = DaskExecutor(address=client.scheduler.address)
        seismicity_flow.run(executor=executor)


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
        self._forecast_id = None
        self._forecast_executor = None
        self.forecast_handler = ForecastHandler()
        #self._logger = logging.getLogger(__name__)


    def run(self, t, forecast_id):
        """
        Runs the forecast

        The :class:`~RAMSIS.core.taskmanager.ForecastTask` invokes this
        whenever a new forecast is due.

        :param datetime t: Time of invocation
        :param forecast: Forecast to execute
        :type forecast: ramsis.datamodel.forecast.Forecast
        """
        assert self.core.project
        if not self.session:
            self.session = self.core.store.session
            self.forecast_handler.session = self.session
        forecast_input = get_forecast_seismicity(forecast_id, self.session)#self.session.query(Forecast).filter(Forecast.id==forecast_id).first()
        #forecast_input = deepcopy(forecast)
        #print("printing the seismiccatalog hybrid", [i.creationinfo_creationtime for i in forecast.seismiccatalog_history], forecast.seismiccatalog)

        system_time = datetime.now()
        #seismicity_flow = Flow("Seismicity_Execution")
        #data_snapshot = DataSnapshot(
        #    state_handlers=[self.forecast_handler.snapshot_state_handler])
        #    model_run_executor = SeismicityModelRunExecutor(
        #        state_handlers=[self.forecast_handler.model_run_state_handler])
        #seismicity_flow.chain(
        #    data_snapshot(forecast, system_time),
        #    forecast_scenarios()
                
        #        )
        forecast_flow = ForecastFlow(forecast_input, system_time, self.forecast_handler) 
        worker = Worker(forecast_flow.run)
        self.threadpool.start(worker)

    def flow_state_handler(self, obj, old_state, new_state):
        msg = "\nForecast state has changed from {0}:\n{1} to {2}\n"
        #print("In state handler...", msg.format(obj, old_state, new_state))

    def seismicity_stage_state_handler(self, obj, old_state, new_state):
        msg = "\nTask state has changed from {0}:\n{1} to {2}\n"
        #print("In state handler...", msg.format(obj, old_state, new_state), obj.status)
        #self.execution_status_update.emit(obj.status)
        #return new_state

    #def forecast_state_handler(self, obj, old_state, new_state):
    #    msg = "\nTask state has changed from {0}:\n{1} to {2}\n"
    #    print("In state handler...", msg.format(obj, old_state, new_state), obj.status, new_state.result)
    #    self.execution_status_update.emit(obj.status)
    #    return new_state

    #
    #def model_run_state_handler(self, obj, old_state, new_state):
    #    msg = "\nTask state has changed from {0}:\n{1} to {2}\n"
    #    if obj.model_run_id:
    #        estatus = prefect_estatus_conversion(new_state, context='model_run')
    #        if estatus:
    #            # Completion of tasks means that model is running.
    #            model_run = self.session.query(SeismicityModelRun).filter(
    #                SeismicityModelRun.id == obj.model_run_id).one_or_none()
    #            model_run.status.state = estatus
    #            self.session.add(model_run)
    #            self.session.commit()
    #            self.session.expunge(model_run)
    #            self.execution_status_update.emit(new_state)
    #    return new_state


    #def on_forecast_status_changed(self, status):
    #    if isinstance(status.origin, ForecastExecutor):
    #        if status.flag == ExecutionStatus.Flag.SUCCESS:
    #            self.threadpool.waitForDone()
    #            self.core.store.close()
    #            self.forecast_status_update.emit(ExecutionStatus(
    #                self.forecast, flag=ExecutionStatus.Flag.RUNNING))
    #    if isinstance(status.origin, SeismicityModelRunExecutor):
    #        if status.flag == ExecutionStatus.Flag.RUNNING:
    #            if not self.core.model_results.running:
    #                self.core.model_results.start()
    #    self.execution_status_update.emit(status)


class DataCaptureThread(QThread):

    model_run_status_update = pyqtSignal(object)

    def __init__(self, core):
        """
        :param RAMSIS.core.controller.Controller core: Reference to the core
        """
        super().__init__()
        self.core = core
        self.running = False
        self.session = None
        self._logger = logging.getLogger("DataCaptureThread")
        QThread.__init__(self)
        self.dataCollectionTimer = QTimer()
        self.dataCollectionTimer.moveToThread(self)
        self.dataCollectionTimer.timeout.connect(self.collectProcessData)

    def accepted_model_runs(self):

        model_runs = self.session.query(SeismicityModelRun).join(
            SeismicityModelRun.status).filter(
                Status.state.in_([EStatus.RUNNING])).all()
        for run in model_runs:
            self.session.expunge(run)
        model_run_ids = [run.runid for run in model_runs]
        return model_run_ids

    def collectProcessData(self):
        if self.session is not None:
            pass
        else:
            self.session = self.core.store

        # To be removed when better solution in place
        accepted_model_run_ids = self.accepted_model_runs()
        self._logger.info("Waiting model runs: {}".format(
            accepted_model_run_ids))
        for run in accepted_model_run_ids:
            self._logger.info("model run ids {}".format(run))
            poller = SeismicityModelRunPoller(self.session, run)
            poller.status_changed.connect(
                self.on_model_run_status_changed)
            poller.poll()
        if not accepted_model_run_ids:
            self.loop.exit()
            self.running = False

    def run(self):
        self.session = self.core.store.session
        self.running = True
        self.dataCollectionTimer.start(3000)
        self.loop = QEventLoop()
        self.loop.exec_()

    def on_model_run_status_changed(self, status):
        if isinstance(status.origin, SeismicityModelRunPoller):
            self.model_run_status_update.emit(status)
