# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Forecast executing related engine facilities.
"""

import logging
import traceback
import sys

from PyQt5.QtCore import (pyqtSignal, QObject, QThreadPool, QRunnable,
                          QTimer, QEventLoop, QThread, pyqtSlot)

from RAMSIS.core.tools.executor import ExecutionStatus
from RAMSIS.core.engine.forecastexecutor import ForecastExecutor,\
    SeismicityModelRunPoller, SeismicityModelRunExecutor
from ramsis.datamodel.seismicity import SeismicityModelRun
from ramsis.datamodel.forecast import Forecast
from ramsis.datamodel.status import Status, EStatus


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
        self._forecast_id = None
        self._forecast_executor = None
        self._logger = logging.getLogger(__name__)

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
        self._forecast_id = forecast_id
        self.forecast = self.core.store.session.query(Forecast).filter(
            Forecast.id == forecast_id).one_or_none()
        # Skip this forecast if the core is busy
        if self.busy:
            self._logger.warning('Attempted to initiate forecast while the '
                                 'core is still busy with a previously '
                                 'started forecast. Skipping at '
                                 f't={self.forecast.starttime}')
            return

        self._logger.info('Initiating forecast scheduled for {} at {}'.format(
            self.forecast.starttime, t))

        self.core.store.session.expunge(self.forecast)
        self._forecast_executor = ForecastExecutor(self.core,
                                                   self._forecast_id)
        self._forecast_executor.status_changed.connect(
            self.on_forecast_status_changed)
        worker = Worker(self._forecast_executor.run)
        self.threadpool.start(worker)

    def on_forecast_status_changed(self, status):
        if isinstance(status.origin, ForecastExecutor):
            if status.flag == ExecutionStatus.Flag.SUCCESS:
                self.threadpool.waitForDone()
                self.core.store.close()
                self.forecast_status_update.emit(ExecutionStatus(
                    self.forecast, flag=ExecutionStatus.Flag.RUNNING))
        if isinstance(status.origin, SeismicityModelRunExecutor):
            if status.flag == ExecutionStatus.Flag.RUNNING:
                if not self.core.model_results.running:
                    self.core.model_results.start()
        self.execution_status_update.emit(status)


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
