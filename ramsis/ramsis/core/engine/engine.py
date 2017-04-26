import logging

from PyQt4 import QtCore

from core.engine.forecastjob import ForecastJob


class Engine(QtCore.QObject):
    # Signals
    forecast_complete = QtCore.pyqtSignal()

    def __init__(self, core):
        super(Engine, self).__init__()
        self.busy = False
        self.core = core
        self._forecast = None
        self._forecast_job = None
        self._forecast_task = None
        self._logger = logging.getLogger(__name__)

    def run(self, t, forecast):
        assert self.core.project

        # Skip this forecast if the core is busy
        if self.busy:
            self._logger.warning('Attempted to initiate forecast while the '
                                 'core is still busy with a previously'
                                 'started forecast. Skipping at '
                                 't=' + str(forecast.forecast_time))
            return

        self._logger.info(6 * '----------')
        self._logger.info('Initiating forecast {} at {}'.format(
            forecast.forecast_time, t))

        # Copy the current catalog and change the owner from the project
        # to the forecast input
        copy = self.core.project.store.copy(self.core.project.seismic_catalog)
        copy.project = None
        forecast.input.input_catalog = copy
        self.core.project.save()

        self._forecast = forecast
        self.busy = True
        self._forecast_job = ForecastJob(forecast)
        self._forecast_job.complete.connect(self.fc_job_complete)
        self._forecast_job.run()

    def fc_job_complete(self):
        self.busy = False
        self.forecast_complete.emit()

    def observe_project(self, project):
        """
        Start observing a new project

        :param Project project: Project to observe

        """
        project.will_close.connect(self._on_project_close)
        self._project = project

    def _on_project_close(self, project):
        project.will_close.disconnect(self._on_project_close)
        self._project = None
