import logging

from PyQt4 import QtCore

from core.engine.forecastjob import ForecastJob


class Engine(QtCore.QObject):
    # Signals
    forecast_complete = QtCore.pyqtSignal()

    def __init__(self, settings):
        super(Engine, self).__init__()
        self.busy = False
        self._project = None
        self._forecast = None
        self._forecast_job = None
        self._forecast_task = None
        self._settings = settings
        self._logger = logging.getLogger(__name__)

    def run(self, t, forecast):
        assert self._project

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

        # Copy the current catalog
        copy = self.project.seismic_catalog.copy()
        forecast.forecast_input.input_catalog = copy

        self._forecast = forecast
        self.busy = True
        # in future we may run more than one scenario
        self._forecast_job = ForecastJob(self._settings)
        self._forecast_job.forecast_job_complete.connect(self.fc_job_complete)
        self._forecast_job.run_forecast(self._forecast)

    def fc_job_complete(self):
        self._forecast.result = [self._forecast_job.result]
        self._project.store.commit()
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
