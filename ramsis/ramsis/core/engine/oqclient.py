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
import json
import requests
from PyQt4.QtCore import QObject, pyqtSignal, QTimer
from core.tools.notifications import RunningNotification, ErrorNotification, \
    CompleteNotification, OtherNotification

API_V = 'v1'

log = logging.getLogger(__name__)


class OQClient(QObject):
    """
    OQClient connects to the openquake instance and runs hazard and risk
    calculations for forecast scenarios.

    After starting an openquake calculation it will periodically check the
    status of the calculation and report the results back by firing the
    status_changed signal
    
    :ivar calc_id: OQ id of current calculation
    
    """
    # Signal emitted when the calculation status changes
    client_notification = pyqtSignal(object)

    POLL_INTERVAL = 3000  # Poll interval for status polling [ms]

    def __init__(self, url):
        super(OQClient, self).__init__()
        self.url = url
        self.calc_id = None

    def run_hazard(self, files):
        """
        Starts a classical psha calculation with the input files passed in
        files.

        :param list files: Input files for hazard calculation
        :return: response

        """
        if self.calc_id:
            raise RuntimeError('Cannot run more than one job at a time')
        # start hazard calculation
        r = self.post_job(files=files)
        if r.status_code == 200:
            content = json.loads(r.content)
            self.calc_id = content['job_id']
            notification = RunningNotification(self.calc_id, response=r)
            QTimer.singleShot(OQClient.POLL_INTERVAL, self.poll_status)
            log.info('Hazard job with id {} started'.format(self.calc_id))
        else:
            notification = ErrorNotification(response=r)
            log.error('Failed to start hazard stage: [{}] {}'
                      .format(r.status_code, r.content).strip('\n'))
        self.client_notification.emit(notification)

    def poll_status(self):
        r = self.get_status()
        if r.status_code == 200:
            content = json.loads(r.content)
            if content['status'] == 'executing':
                QTimer.singleShot(OQClient.POLL_INTERVAL, self.poll_status)
                return
            elif content['status'] == 'failed':
                log.error('Calculation failed: [{}] {}'
                          .format(r.status_code, r.content).strip('\n'))
                notification = ErrorNotification(self.calc_id, response=r)
                self.calc_id = None
            elif content['status'] == 'complete':
                log.info('Hazard calculation {} complete'.format(self.calc_id))
                notification = CompleteNotification(self.calc_id, response=r)
                self.calc_id = None
        elif r.status_code == 500:
            log.error('Calculation failed: [{}] {}'
                      .format(r.status_code, r.content).strip('\n'))
            notification = ErrorNotification(self.calc_id, response=r)
            self.calc_id = None
        else:  # other (e.g. not reachable), we keep polling
            log.warn('Unexpected OQ response: [{}] {}'
                     .format(r.status_code, r.content).strip('\n'))
            notification = OtherNotification(self.calc_id, response=r)
            # TODO: define timeout?
            QTimer.singleShot(OQClient.POLL_INTERVAL, self.poll_status)
        self.client_notification.emit(notification)

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

    def post_job(self, files):
        end_point = '{}/calc/run'.format(API_V)
        r = requests.post(urljoin(self.url, end_point), files=files)
        log.debug('post job response: {}'.format(r))
        return r

