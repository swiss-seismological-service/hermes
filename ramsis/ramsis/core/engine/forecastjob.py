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
import time
from core.tools.job import ParallelJob, SerialJob, WorkUnit
from ramsisdata.forecast import ForecastResult
from oqclient import OQClient
from modelclient import ModelClient

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
        self.forecast.forecast_set.project.save()
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
        self.forecast.results.append(ForecastResult())

    def post_process(self):
        self.forecast.forecast_set.project.save()
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
        self.client = ModelClient(model_id, model_config)
        self.client.finished.connect(self.on_client_finished)

    def run(self):
        log.info('Running forecast model {}'.format(self.client.model_id))
        project = self.scenario.forecast_input.forecast.forecast_set.project
        run_info = {
            'reference_point': project.reference_point,
            'injection_point': project.injection_well.injection_point
        }
        time.sleep(2)
        self.complete.emit(self)
        self.client.run(self.scenario, run_info)

    def on_client_finished(self, client):
        log.info('Forecast model {} complete'.format(self.client.model_id))
        self.scenario.forecast_result.model_results.append(client.model_result)
        self.complete.emit(self)


class HazardStage(WorkUnit):

    def __init__(self, scenario):
        super(HazardStage, self).__init__('psha_stage')
        self.scenario = scenario
        self.client = OQClient('http://127.0.0.1:8800')

    def run(self):
        log.info('Running psha stage on scenario: {}'\
                 .format(self.scenario.name))
        time.sleep(2)
        self.complete.emit(self)
        #self.client.run_hazard(self.scenario)


class RiskStage(WorkUnit):

    def __init__(self, scenario):
        super(RiskStage, self).__init__('risk_stage')
        self.scenario = scenario

    def run(self):
        log.info('Running risk stage on scenario: {}'\
                 .format(self.scenario.name))
        time.sleep(2)
        self.complete.emit(self)
