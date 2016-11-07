# -*- encoding: utf-8 -*-
# Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED
"""
Defines the components of a forecast job.

A forecast job consists of three `Stages <Stage>`:

1. Forecasting of induced seismicity (computed by the `ISForecastStage`)
2. Computation of the probabilistic seismic hazard (`PshaStage`)
3. Computation of the probability to exceed certain losses (`RiskPoeStage`)

The three stages are invoked in succession by `ForecastJob`.

"""

import logging

from PyQt4 import QtCore

from job import Job, Stage

from ismodels.common import ModelInput
from isforecaster import ISForecaster
from oq.controller import controller as oq

from core.data.forecast import ForecastResult


class ISForecastStage(Stage):
    """
    Uses an `ISForecaster` to compute induced seismicity forecasts from a
    seismic and hydraulic history.

    The `ISForecastStage` expects as input a dictionary containing at least:

    - ``t_run``: the project time at which the forecast starts (`datetime`)
    - ``dt_h``: the forecast bin duration in hours (`float`)
    - ``project``: a reference to the `Project`

    """
    stage_id = 'is_forecast_stage'

    def __init__(self, callback):
        super(ISForecastStage, self).__init__(callback)
        self.is_forecaster = None

    def stage_fun(self):
        t_run = self.inputs['t_run']
        dt_h = self.inputs['dt_h']
        project = self.inputs['project']

        self._logger.info('Invoking IS forecast stage at t={}.'.format(t_run))

        # FIXME: do not hard code mc, mag_range
        model_input = ModelInput(t_run, project, bin_size=dt_h, mc=0.9,
                                 mag_range=(0, 6))
        model_input.estimate_expected_flow(t_run, project, dt_h)
        # TODO: Allow estimated flow to be user defined (#18)
        self.is_forecaster = ISForecaster(self.fc_complete)
        self.is_forecaster.run(model_input)

    def fc_complete(self, result):
        self.results = result
        self.stage_complete()


class PshaStage(Stage):
    """
    Invokes the classical PSHA calculator of OpenQuake to compute hazard
    curves from one or more frequency-magnitude relationships.

    """
    stage_id = 'psha_stage'

    def stage_fun(self):
        self._logger.info('Invoking PSHA stage.')
        source_params = {}
        model_results = self.inputs.model_results.items()
        for i, (model_name, result) in enumerate(model_results, start=1):
            a = result.cum_result.rate
            b = result.cum_result.b_val
            # FIXME: use the scores from the latest IS model assessment
            # make sure the sum of all weights is exactly 1.0 (this is an
            # openquake requirement)
            if i < len(model_results):
                w = round(1.0 / len(model_results), 2)
            else:
                w = 1.0 - sum(p[2] for p in source_params.values())
            source_params[model_name] = [a, b, w]
        oq.run_hazard(source_params, callback=self.psha_complete)

    def psha_complete(self, results):
        self.results = results
        self.stage_complete()


class RiskPoeStage(Stage):
    """
    Invokes the classical probabilistic risk calculator of OpenQuake to compute
    the probability of exceedance for specified loss values.

    """
    stage_id = 'risk_poe_stage'

    def stage_fun(self):
        self._logger.info('Invoking risk PoE stage.')

        psha_job_id = self.inputs['job_id']
        oq.run_risk_poe(psha_job_id, callback=self.risk_poe_complete)

    def risk_poe_complete(self, results):
        self.results = results
        self.stage_complete()


class ForecastJob(Job):
    """
    Defines the job of computing forecasts with its three stages

    """
    job_id = 'fc_job'  #: Job ID for ForecastJob
    stages = [ISForecastStage, PshaStage, RiskPoeStage]  #: ForecastJob stages

    # Signals
    forecast_complete = QtCore.pyqtSignal()

    def __init__(self, settings):
        super(ForecastJob, self).__init__()
        self._settings = settings
        self._project = None
        self._forecast_task = None
        self.busy = False
        self._current_fc_result = None
        self._logger = logging.getLogger(__name__)

    @property
    def t_next_forecast(self):
        return self._forecast_task.run_time

    def run_forecast(self, task_run_info):
        """
        Run a new forecast.

        The parameter `task_run_info` contains all the information the job
        needs to start a forecast, particularly the forecast time. Upon
        invocation `run_forecast` assembles the input data for the job. It then
        calls :meth:`core.forecastjob.ForecastJob.run` to set the job in
        motion.

        :param TaskRunInfo task_run_info: Forecast info such as the forecast
           time.

        """
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

        job_input = {
            't_run': t_run,
            'dt_h': self._settings.value('engine/fc_bin_size'),
            'project': self._project
        }
        self.stage_completed.connect(self.fc_stage_complete)
        self._current_fc_result = ForecastResult()
        persist = self._settings.value('engine/persist_results')
        self._project.forecast_history.add(self._current_fc_result, persist)
        self.busy = True
        self.run(job_input)

    def fc_stage_complete(self, stage):
        if stage.stage_id == 'is_forecast_stage':
            self._logger.info('IS forecast stage completed')
            self._current_fc_result.is_forecast_result = stage.results
        elif stage.stage_id == 'psha_stage':
            self._logger.info('PSHA stage completed')
            self._current_fc_result.hazard_oq_calc_id = stage.results['job_id']
        elif stage.stage_id == 'risk_poe_stage':
            self._logger.info('Risk PoE stage completed')
            self._current_fc_result.risk_oq_calc_id = stage.results['job_id']
        else:
            raise ValueError('Unexpected stage id: {}'.format(stage.stage_id))

        if stage == self.stage_objects[-1]:
            self.busy = False
            self.forecast_complete.emit()

        self._current_fc_result.commit_changes()

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
