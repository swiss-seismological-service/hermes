import logging

from PyQt5.QtCore import pyqtSignal, QObject

from RAMSIS.core.tools.executor import ExecutionStatus
from RAMSIS.core.engine.forecastexecutor import ForecastExecutor


class Engine(QObject):
    """
    The engine is responsible for running forecasts


    """

    #: Emitted when a forecast computation has completed
    forecast_complete = pyqtSignal()
    #: Emitted whenever any part of a forecast emits a status update. Carries
    #    a :class:`~RAMSIS.core.tools.executor.ExecutionStatus` object.
    execution_status_update = pyqtSignal(object)

    def __init__(self, core):
        """

        :param RAMSIS.core.controller.Controller core: Reference to the core
        """
        super(Engine, self).__init__()
        self.busy = False
        self.core = core
        self._forecast = None
        self._forecast_executor = None
        self._logger = logging.getLogger(__name__)

    def run(self, t, forecast):
        """
        Runs the forecast

        The :class:`~RAMSIS.core.taskmanager.ForecastTask` invokes this
        whenever a new forecast is due.

        :param datetime t: Time of invocation
        :param forecast: Forecast to execute
        :type forecast: ramsis.datamodel.forecast.Forecast
        """
        assert self.core.project

        # Skip this forecast if the core is busy
        if self.busy:
            self._logger.warning('Attempted to initiate forecast while the '
                                 'core is still busy with a previously '
                                 'started forecast. Skipping at '
                                 f't={forecast.starttime}')
            return

        self._logger.info('Initiating forecast scheduled for {} at {}'.format(
            forecast.starttime, t))

        self._forecast = forecast
        self.busy = True
        self._forecast_executor = ForecastExecutor(self.core, forecast)
        self._forecast_executor.status_changed.connect(
            self.on_executor_status_changed)
        self._forecast_executor.run()

    def on_executor_status_changed(self, status):
        """
        Handle status changes from the executor chain

        :param RAMSIS.core.tools.executor.ExecutionStatus status: Status
        """
        if status.origin == self._forecast_executor:
            done = [ExecutionStatus.Flag.SUCCESS, ExecutionStatus.Flag.ERROR]
            if status.flag in done:
                self.busy = False
                self.forecast_complete.emit()
        self.execution_status_update.emit(status)
