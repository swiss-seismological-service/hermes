# -*- encoding: utf-8 -*-
"""
RAMSIS client interface to openquake

We control openquake on a (potentially) remote machine using OQs REST API.
This module provides an interface to run the calculations we need in RAMSIS
and handles the communication with openquake.

Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED

"""
import logging
from urlparse import urljoin
import requests
from PyQt4.QtCore import QObject, pyqtSignal, QTimer
import oqutils

API_V = 'v1'

log = logging.getLogger(__name__)


class OQClient(QObject):
    """
    OQClient connects to the openquake instance and runs hazard and risk
    calculations for forecast scenarios.

    After starting an openquake calculation it will periodically check the
    status of the calculation and report the results back by firing the
    status_changed signal.

    """
    # Signal emitted when the calculation status changes (passes self)
    status_changed = pyqtSignal(object)

    POLL_INTERVAL = 3  # Poll interval for status polling

    def __init__(self, url):
        super(OQClient, self).__init__()
        self.url = url
        self.forecast = None
        self.scenario = None
        self.calc_id = None

    def run_hazard(self, scenario):
        """
        Runs a specific scenario from a specific forecast

        :param Scenario scenario: Specific scenario in forecast to run

        """
        self.forecast = scenario.forecast_input.forecast
        self.scenario = scenario
        # get the source parameters from the model results
        model_results = scenario.forecast_result.model_results
        weight = 1.0/len(model_results)
        params = {}
        for result in model_results:
            pred = result.rate_prediction
            params[result.model_name] = [pred.rate, pred.b_value, weight]
        # prepare source model logic tree and job config
        job_config = oqutils.hazard_job_ini()
        input_models = oqutils.hazard_input_models(params)
        # start hazard calculation
        r = self.post_job(job_config=job_config, input_models=input_models)
        QTimer.singleShot(OQClient.POLL_INTERVAL, self.poll_status())

    def poll_status(self):
        r = self.get_status()
        QTimer.singleShot(OQClient.POLL_INTERVAL, self.poll_status())

    # REST Client Methods

    def get_status(self):
        """ Get the calculation status from openquake """
        end_point = '{}/calc/{}/status'.format(API_V, self.calc_id)
        r = requests.get(urljoin(self.url, end_point))
        log.debug('status response: {}'.format(r))
        return r

    def get_result_list(self):
        end_point = '{}/calc/{}/results'.format(API_V, self.calc_id)
        r = requests.get(urljoin(self.url, end_point))
        log.debug('get result list response: {}'.format(r))
        return r

    def get_result(self, result_id):
        end_point = '{}/calc/result/{}'.format(API_V, result_id)
        r = requests.get(urljoin(self.url, end_point))
        log.debug('get result response: {}'.format(r))
        return r

    def post_job(self, job_config, input_models):
        end_point = '{}/calc/run'
        files = {'job_config': job_config}
        for i, model in enumerate(input_models):
            files['input_model_{}'.format(i)] = model
        r = requests.post(urljoin(self.url, end_point), files=files)
        log.debug('post job response: {}'.format(r))
        return r

