# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from job import Job, Stage

from ismodels.common import ModelInput
from isforecaster import ISForecaster
from data.isforecastresult import ISResult
from oq import controller as oq


class ISForecastStage(Stage):
    """
    Uses an ISForecaster to compute induced seismicity forecasts from a
    seismic and hydraulic history.

    The ISForecastStage expects as input a dictionary containing
      - 't_run' the project time at which the forecast starts (datetime)
      - 'dt_h' the forecast bin duration in hours (float)
      - 'project' a reference to the project (Project)

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
    curves from one or more Gutenberg Richter relationships.

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

    def psha_complete(self, job_id, success):
        self.results = None
        self.stage_complete()


class RiskPoeStage(Stage):
    """
    Invokes the classical probabilistic risk calculator of OpenQuake to compute
    the probability of exceedance for specified loss values

    """
    stage_id = 'risk_poe_stage'

    def stage_fun(self):
        self._logger.info('Invoking risk PoE stage.')
        self.results = None
        self.stage_complete()


class ForecastJob(Job):
    job_id = 'fc_job'
    stages = [ISForecastStage, PshaStage, RiskPoeStage]

