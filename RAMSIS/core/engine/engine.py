# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Forecast executing related engine facilities.
"""
from copy import deepcopy
import traceback
import sys
from datetime import datetime

from sqlalchemy.orm import joinedload, subqueryload
from PyQt5.QtCore import (pyqtSignal, QObject, QThreadPool, QRunnable,
                          pyqtSlot)

from RAMSIS.core.engine.forecastexecutor import \
    SeismicityModelRunPoller, SeismicityModelRunExecutor,\
    SeismicityModels, forecast_scenarios,\
    dispatched_seismicity_model_runs, CatalogSnapshot, WellSnapshot,\
    flatten_task
from ramsis.datamodel.seismicity import SeismicityModelRun
from ramsis.datamodel.forecast import Forecast, ForecastScenario, \
    EStage, SeismicityForecastStage
from ramsis.datamodel.status import EStatus
from ramsis.datamodel.seismics import SeismicCatalog
from ramsis.datamodel.well import InjectionWell, WellSection
from ramsis.datamodel.hydraulics import InjectionPlan, Hydraulics
from ramsis.datamodel.project import Project
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
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()  # Done


# For usage when forecast actually has a status.
def get_forecast_no_children(forecast_id, session):
    forecast = session.query(Forecast).\
        options(joinedload(Forecast.status)).\
        filter(Forecast.id == forecast_id)
    return forecast.one()


def get_forecast_seismicity(forecast_id, session):
    session.remove()
    forecast_query = session.query(Forecast).\
        options(
            # Load catalogs linked to forecast and project
            subqueryload(Forecast.status)).\
        options(
            # Load catalogs linked to forecast and project
            subqueryload(Forecast.seismiccatalog).\
            subqueryload(SeismicCatalog.events)).\
        options(
            subqueryload(Forecast.project).\
            subqueryload(Project.seismiccatalogs).\
            subqueryload(SeismicCatalog.events)).\
        options(
            # Load well and injection plan linked to project
            subqueryload(Forecast.project).\
            subqueryload(Project.wells).\
            subqueryload(InjectionWell.sections).\
            subqueryload(WellSection.hydraulics).\
            subqueryload(Hydraulics.samples)).\
        options(
            subqueryload(Forecast.project).\
            subqueryload(Project.wells).\
            subqueryload(InjectionWell.sections).\
            subqueryload(WellSection.injectionplan).\
            subqueryload(InjectionPlan.samples)).\
        options(
            # Load status of seismicity stage
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage)).\
            subqueryload(SeismicityForecastStage.status)).\
        options(
            # Load models from seismicity stage
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage)).\
            subqueryload(SeismicityForecastStage.runs).\
            subqueryload(SeismicityModelRun.model)).\
        options(
            # Load model run status from seismicity stage
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage)).\
            subqueryload(SeismicityForecastStage.runs).\
            subqueryload(SeismicityModelRun.status)).\
        options(
            # Load result attributes for model runs (these will be written to)
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage)).\
            subqueryload(SeismicityForecastStage.runs).\
            subqueryload(SeismicityModelRun.result)).\
        options(
            # Load well attached to forecast
            subqueryload(Forecast.well).\
            subqueryload(InjectionWell.sections).\
            subqueryload(WellSection.hydraulics).\
            subqueryload(Hydraulics.samples)).\
        options(
            # Load injection plan attached to scenario
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.well).\
            subqueryload(InjectionWell.sections).\
            subqueryload(WellSection.injectionplan).\
            subqueryload(InjectionPlan.samples)).\
        filter(Forecast.id == forecast_id)
    forecast = forecast_query.one()
    forecast_copy = deepcopy(forecast)
    session.remove()
    return forecast_copy


class ForecastHandler(QObject):
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
            self.session.commit()
            self.session.remove()

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
            if new_state.is_failed():
                forecast.status.state = EStatus.ERROR
            elif new_state.is_successful():
                forecast.status.state = EStatus.COMPLETE
            for scenario in forecast.scenarios:
                self.session.merge(self.scenario_stage_status(scenario))
                self.session.commit()
            self.update_db()
        self.session.remove()
        return new_state

    def scenario_models_state_handler(self, obj, old_state, new_state):
        """
        Set the model runs status to RUNNING when this task suceeds.
        """
        if (new_state.is_finished() and
                new_state.is_successful() and not
                new_state.is_mapped()):
            model_runs = new_state.result
            for run in model_runs:
                run.status.state = EStatus.RUNNING
                self.session.merge(run)
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

        if new_state.is_finished() and not new_state.is_mapped():
            if new_state.is_successful():
                model_run = new_state.result
                logger.info(f"Model run with runid={model_run.runid}"
                            "has been dispatched to the remote worker.")
                model_run.status.state = EStatus.DISPATCHED
                self.session.merge(model_run)
            elif not new_state.is_successful():
                # prefect Fail should be raised with model_run as a result
                model_run = new_state.result
                model_run.status.state = EStatus.ERROR
                self.session.merge(model_run)
            # The sent status is not used, as the whole scenario must
            # be refreshed from the db in the gui thread.
            self.update_db()
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

        if (new_state.is_finished() and not
                new_state.is_mapped() and not
                new_state.is_looped()):
            if new_state.is_successful():
                model_run, model_result = new_state.result
                logger.info(f"Model with runid={model_run.runid} "
                            "has returned without error from the "
                            "remote worker.")
                model_run.status.state = EStatus.COMPLETE
                self.session.merge(model_run)
            elif new_state.is_failed():
                model_run = new_state.result
                logger.error(f"Model with runid={model_run.runid}"
                             "has returned an error from the "
                             "remote worker.")
                model_run.status.state = EStatus.ERROR
                self.session.merge(model_run)
            self.update_db()
            self.execution_status_update.emit((
                new_state, type(model_run),
                model_run.id))
        return new_state

    def catalog_snapshot_state_handler(self, obj, old_state, new_state):
        """
        When the catalog snapshot task has been skipped, then the forecast
        already has a catalog snapshot and this is not overwritten.
        If this task has completed successfully, the new snapshot is added
        to the session and forecast merged as an attribute was modified.
        """
        logger = prefect.context.get("logger")
        if new_state.is_finished() and new_state.is_successful():
            forecast = new_state.result
            if new_state.is_skipped():
                logger.info(f"Forecast id={forecast.id} already a snapshot"
                            " of the seismic catalog attached.")
            else:
                logger.info(f"Forecast id={forecast.id} has made a snapshot"
                            " of the seismic catalog")
                # A forecast may only have one seismiccatalog associated
                # This is enforced in code rather than at db level.
                assert(len(forecast.seismiccatalog) == 1)
                self.session.add(forecast.seismiccatalog[0])
                self.session.commit()
                self.session.merge(forecast)
                self.update_db()
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
        if new_state.is_finished() and new_state.is_successful():
            forecast = new_state.result
            if new_state.is_skipped():
                logger.info(f"Forecast id={forecast.id} already a snapshot"
                            " of hydraulic well attached.")
            else:
                logger.info(f"Forecast id={forecast.id} has made a snapshot"
                            " of the hydraulic well")
                # A forecast may only have one well associated
                # This is enforced in code rather than at db level.
                assert(len(forecast.well) == 1)
                self.session.add(forecast.well[0])
                self.session.commit()
                self.session.merge(forecast)
                self.update_db()
        return new_state


class ForecastFlow(QObject):
    """
    Contains prefect flow logic for creating DAG.
    A flow is created for every forecast that is run by the
    engine.
    """
    def __init__(self, forecast, system_time, forecast_handler):
        self.system_time = system_time
        self.forecast_handler = forecast_handler
        self.forecast = forecast

    def run(self, progress_callback):
        with Flow("Seismicity_Execution",
                  state_handlers=[self.forecast_handler.flow_state_handler]
                  ) as seismicity_flow:
            forecast = Parameter('forecast')
            catalog_snapshot = CatalogSnapshot(
                skip_on_upstream_skip=False,
                state_handlers=[self.forecast_handler.
                                catalog_snapshot_state_handler])
            forecast_data = catalog_snapshot(forecast, self.system_time)

            well_snapshot = WellSnapshot(
                skip_on_upstream_skip=False,
                state_handlers=[self.forecast_handler.
                                well_snapshot_state_handler])
            forecast_data = well_snapshot(forecast_data, self.system_time)

            scenarios = forecast_scenarios(
                forecast_data)
            seismicity_models = SeismicityModels(
                skip_on_upstream_skip=False,
                state_handlers=[self.forecast_handler.
                                scenario_models_state_handler])
            model_runs = seismicity_models.map(
                scenarios)

            model_runs_flattened = flatten_task(model_runs)
            model_run_executor = SeismicityModelRunExecutor(
                state_handlers=[self.forecast_handler.model_run_state_handler],
                skip_on_upstream_skip=False)

            _ = model_run_executor.map(
                unmapped(forecast_data), model_runs_flattened)

            dispatched_model_runs = dispatched_seismicity_model_runs(
                forecast_data)

            # Add dependency so that SeismicityModelRunExecutor must complete
            # before checking for model runs with DISPATCHED status.
            seismicity_flow.add_edge(
                seismicity_flow.get_tasks('SeismicityModelRunExecutor')[0],
                seismicity_flow.get_tasks(
                    'dispatched_seismicity_model_runs')[0])

            model_run_poller = SeismicityModelRunPoller(
                state_handlers=[
                    self.forecast_handler.poll_seismicity_state_handler],
                skip_on_upstream_skip=False)
            _ = model_run_poller.map(unmapped(forecast_data),
                                     dispatched_model_runs)

        # (sarsonl) To view DAG: seismicity_flow.visualize()

        executor = LocalDaskExecutor(scheduler='threads')
        with prefect.context(forecast_id=self.forecast.id):
            seismicity_flow.run(parameters=dict(forecast=self.forecast),
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
            self.forecast_handler.session = self.session
        forecast_input = get_forecast_seismicity(forecast_id, self.session)
        assert forecast_input.status.state != EStatus.COMPLETE

        # The current time is required for snapshots of catalog and well data
        # TODO (sarsonl) should get this from the scheduler module.
        system_time = datetime.now()
        forecast_flow = ForecastFlow(forecast_input, system_time,
                                     self.forecast_handler)
        worker = Worker(forecast_flow.run)
        self.threadpool.start(worker)
