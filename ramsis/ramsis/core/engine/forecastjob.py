# -*- coding: utf-8 -*-
"""
Classes to execute a forecast

A forecast is a complex sequence of serial and parallel stages:

ForecastJob                Runs one or more scenarios, executing serially
    ScenarioJob            Runs the stages of a scenario, serial
        ForecastStage      Runs the induced seismicity models, parallel
            SeismicityForecast  Runs a single induced seismicity model
            SeismicityForecast
            ...
        HazardStage        Runs the hazard stage of a forecast
        RiskStage          Runs the risk stage of a forecast
    Scenario Job
    ...

The forecast (data model object) will be passed to the forecast job on init.

Copyright (c) 2017, Swiss Seismological Service, ETH Zurich

"""

import logging
import io
from zipfile import ZipFile
from core.tools.job import ParallelJob, SerialJob, WorkUnit, JobStatus
from ramsisdata.forecast import ForecastResult, HazardResult, RiskResult, \
    ModelResult, Scenario, Forecast
from ramsisdata.calculationstatus import CalculationStatus
from oqclient import OQClient
from core.tools.notifications import ClientNotification
import oqutils
from modelclient import ModelClient

from PyQt4.QtGui import QApplication

log = logging.getLogger(__name__)


class ForecastJob(SerialJob):
    """
    Serial execution of scenarios

    :param Forecast forecast: Forecast to execute

    """

    def __init__(self, forecast):
        super(ForecastJob, self).__init__('forecast_job')
        self.forecast = forecast
        # our work units are scenario jobs
        self.work_units = [ScenarioJob(s) for s in forecast.input.scenarios]

    def pre_process(self):
        log.info('Starting forecast job at {} scenarios: {}'
                 .format(self.forecast.forecast_time,
                         [s.name for s in self.forecast.input.scenarios]))

    def post_process(self):
        self.forecast.project.save()
        log.info('Forecast {} completed'.format(self.forecast.forecast_time))


class ScenarioJob(SerialJob):
    """
    Runs forecast, hazard and risk calculation for a scenario

    :param Scenario scenario: Scenario for this job

    """

    def __init__(self, scenario):
        super(ScenarioJob, self).__init__(scenario.name)
        self.scenario = scenario
        self.forecast = scenario.forecast_input.forecast
        cfg = self.scenario.config
        stages = []
        if cfg['run_is_forecast']:
            stages.append(ForecastStage(self.scenario))
        if cfg['run_hazard']:
            stages.append(HazardStage(self.scenario))
        if cfg['run_risk']:
            stages.append(RiskStage(self.scenario))
        self.work_units = stages

    def pre_process(self):
        log.info('Calculating scenario: {}'.format(self.scenario.name))
        result = ForecastResult()
        self.forecast.results.append(result)
        self.scenario.forecast_result = result
        self.scenario.project.save()

    def post_process(self):
        self.scenario.project.save()
        log.info('Scenario {} complete'.format(self.scenario.name))


class ForecastStage(ParallelJob):
    """
    Executes all forecast models for a scenario

    :param Scenario scenario: scenario for which to execute model forecasts

    """

    def __init__(self, scenario):
        super(ForecastStage, self).__init__('forecast_model_job')
        self.scenario = scenario
        self.forecast = scenario.forecast_input.forecast

        cfg = self.forecast.forecast_set.project.settings['forecast_models']
        work_units = []
        for model_id, config in cfg.items():
            if config['enabled']:
                wu = SeismicityForecast(self.scenario, model_id, config)
                work_units.append(wu)
        self.work_units = work_units

    def pre_process(self):
        log.info('Starting forecast stage for scenario {} with models {}'
                 .format(self.scenario.name,
                         [wu.client.model_id for wu in self.work_units]))

    def post_process(self):
        log.info('All models complete for scenario: {}'
                 .format(self.scenario.name))


class SeismicityForecast(WorkUnit):

    def __init__(self, scenario, model_id, model_config):
        super(SeismicityForecast, self).__init__(model_id)
        self.scenario = scenario
        self.model_result = None
        self.client = ModelClient(model_id, model_config)
        self.client.client_notification.connect(self.on_client_notification)

    def run(self):
        log.info('Running forecast model {}'.format(self.client.model_id))
        project = self.scenario.forecast_input.forecast.forecast_set.project
        self.model_result = ModelResult(self.job_id)
        forecast_result = self.scenario.forecast_result
        forecast_result.model_results[self.job_id] = self.model_result
        run_info = {
            'reference_point': project.reference_point,
            'injection_point': project.injection_well.injection_point
        }
        self.client.run(self.scenario, run_info)

    def on_client_notification(self, notification):
        # convert the client status into a calculation status and attach
        # it to the model object
        calc_status = create_calculation_status(notification)
        self.model_result.status = calc_status
        self.scenario.project.save()
        # set the job status and forward it up the job chain
        job_status = JobStatus(self, finished=calc_status.finished,
                               info=calc_status)
        self.status_changed.emit(job_status)


class HazardStage(WorkUnit):

    def __init__(self, scenario):
        super(HazardStage, self).__init__('psha_stage')
        # shortcuts
        self.scenario = scenario
        self.hazard_result = None
        # client reference
        self.client = OQClient('http://127.0.0.1:8800')
        self.client.client_notification.connect(self._on_client_notification)

    def run(self):
        log.info('Running psha stage on scenario: {}'\
                 .format(self.scenario.name))
        # create the result object
        self.hazard_result = HazardResult()
        self.scenario.forecast_result.hazard_result = self.hazard_result
        # get the source parameters from the model results
        #model_results = self.scenario.forecast_result.model_results
        #weights = len(model_results) * [round(1.0/len(model_results), 2)]
        #weights[-1] = 1.0 - sum(weights[:-1])  # make sure sum is exactly 1.0
        #params = {}
        #for i, result in enumerate(model_results):
        #    pred = result.rate_prediction
        #    params[result.model_name] = [pred.rate, pred.b_value, weights[i]]
        # FIXME: take params from previous stage
        params = {
            'etas': [4, 1.5, 0.3],
            'shapiro': [8, 1.6, 0.3],
            'ollinger': [9, 1.3, 0.4]
        }
        # prepare source model logic tree and job config
        files = oqutils.hazard_input_files(params)
        self.client.run_job(files)

    def _on_client_notification(self, notification):
        calc_status = create_calculation_status(notification)
        self.hazard_result.status = calc_status
        if calc_status.state == CalculationStatus.RUNNING:
            self.hazard_result.calc_id = calc_status.calc_id
        elif calc_status.state == CalculationStatus.COMPLETE:
            content, id = self.client.get_hazard_curves(calc_status.calc_id)
            if content is None:
                log.error('Failed to retrieve hazard curves for calc {}'
                          .format(calc_status.calc_id))
            else:
                f = io.BytesIO(content)
                h_curves = oqutils.extract_hazard_curves(f)
                h_curves['result_id'] = id
                self.hazard_result.h_curves = h_curves
        self.scenario.project.save()
        # set the job status and forward it up the job chain
        job_status = JobStatus(self, finished=calc_status.finished,
                               info=calc_status)
        self.status_changed.emit(job_status)


class RiskStage(WorkUnit):

    def __init__(self, scenario):
        super(RiskStage, self).__init__('risk_stage')
        self.scenario = scenario
        self.risk_result = None
        # client reference
        self.client = OQClient('http://127.0.0.1:8800')
        self.client.client_notification.connect(self._on_client_notification)

    def run(self):
        log.info('Running risk stage on scenario: {}'\
                 .format(self.scenario.name))
        self.risk_result = RiskResult()
        self.scenario.forecast_result.risk_result = self.risk_result
        files = oqutils.risk_input_files()
        #haz_id = self.scenario.forecast_result.hazard_result.calc_id
        self.client.run_job(files, {'hazard_job_id': 44})

    def _on_client_notification(self, notification):
        calc_status = create_calculation_status(notification)
        self.risk_result.status = calc_status
        self.scenario.project.save()
        # set the job status and forward it up the job chain
        job_status = JobStatus(self, finished=calc_status.finished,
                               info=calc_status)
        self.status_changed.emit(job_status)


# Helper Methods

def _fake_status(unit, result, finished):
    state = CalculationStatus.COMPLETE if finished \
        else CalculationStatus.RUNNING
    calc_status = CalculationStatus(0, state, None)
    result.status = calc_status
    unit.scenario.project.save()
    job_status = JobStatus(unit, finished=finished, info=calc_status)
    unit.status_changed.emit(job_status)
    QApplication.processEvents()


def create_calculation_status(notification):
    """ Create a CalculationStatus from a client notification """
    state_map = {
        ClientNotification.RUNNING: CalculationStatus.RUNNING,
        ClientNotification.COMPLETE: CalculationStatus.COMPLETE,
        ClientNotification.ERROR: CalculationStatus.ERROR,
    }
    calc_id = notification.calc_id
    state = state_map.get(notification.state)
    if notification.response:
        response = {'code': notification.response.status_code,
                    'text': notification.response.text}
    else:
        response = None
    info = {'last_response': response}
    calc_status = CalculationStatus(calc_id, state, info)
    return calc_status
