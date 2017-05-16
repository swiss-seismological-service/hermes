import logging

from PyQt4 import QtCore

from core.engine.forecastjob import ForecastJob


class Engine(QtCore.QObject):
    # Signals
    forecast_complete = QtCore.pyqtSignal()
    job_status_update = QtCore.pyqtSignal(object)

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
        project = self.core.project

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

        # Snapshot the current catalog by creating a copy
        copy = project.seismic_catalog.snapshot(forecast.forecast_time)
        forecast.input.input_catalog = copy
        project.save()

        self._forecast = forecast
        self.busy = True
        self._forecast_job = ForecastJob(forecast)
        self._forecast_job.status_changed.connect(self.on_fc_status_changed)
        self._forecast_job.run()

    def on_fc_status_changed(self, status):
        if status.sender == self._forecast_job and status.finished:
            self.busy = False
            self.forecast_complete.emit()
        else:
            self.job_status_update.emit(status)

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
