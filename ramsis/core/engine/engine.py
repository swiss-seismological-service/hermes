import logging

from PyQt4 import QtCore

from core.engine.forecastjob import ForecastJob
from core.data.forecast import Forecast, ForecastInput, Scenario
from core.data.hydraulics import InjectionPlan, InjectionSample


class Engine:
    # Signals
    forecast_complete = QtCore.pyqtSignal()

    def __init__(self, settings):
        self.busy = False
        self._project = None
        self._forecast = None
        self._forecast_job = None
        self._forecast_task = None
        self._settings = settings
        self._logger = logging.getLogger(__name__)

    def run(self, task_run_info):
        assert self._project
        t_run = task_run_info.t_project

        # Skip this forecast if the core is busy
        if self.busy:
            self._logger.warning('Attempted to initiate forecast while the '
                                 'core is still busy with a previously'
                                 'started forecast. Skipping at '
                                 't=' + str(t_run))
            return

        self._logger.info(6 * '----------')
        self._logger.info('Initiating forecast')

        self._forecast = self._create_forecast(t_run)
        self._project.forecast_history.add(self._forecast, persist=True)
        self.busy = True
        # in future we may run more than one scenario
        self._forecast_job = ForecastJob(self._settings)
        self._forecast_job.forecast_job_complete.connect(self.fc_job_complete)
        self._forecast_job.run(self._forecast)

    def fc_job_complete(self):
        self._forecast.result = self._forecast_job.result
        # update not add ?
        self._project.forecast_history.add(self._forecast, persist=True)

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

    def _create_forecast(self, forecast_time, flow_xt=None,
                         pr_xt=None, flow_dh=None, pr_dh=None):
        """ Returns a new Forecast instance """

        # rows
        forecast = Forecast()
        forecast_input = ForecastInput()
        scenario = Scenario()
        injection_plan = InjectionPlan()
        injection_sample = InjectionSample()

        # relations
        forecast.input = forecast_input
        forecast_input.scenarios = scenario
        scenario.injection_plans = injection_plan
        injection_plan.samples = injection_sample

        # forecast attributes
        forecast.forecast_time = forecast_time
        forecast.forecast_interval = self._settings.value('engine/fc_bin_size')
        forecast.mc = 0.9
        forecast.m_min = 0
        forecast.m_max = 6

        # injection_sample attributes
        injection_sample.date_time = forecast_time
        if flow_xt:
            injection_sample.flow_xt = flow_xt
        if pr_xt:
            injection_sample.pr_xt = pr_xt
        if flow_dh:
            injection_sample.flow_dh = flow_dh
        if pr_dh:
            injection_sample.pr_dh = pr_dh

        # add copy of seismic catalog
        forecast_input.input_catalog = self._project.seismic_catalog.copy()

        return forecast
