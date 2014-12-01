# -*- encoding: utf-8 -*-
"""
ATLS interface to openquake

This module replicates minor parts of openquakes engine.py

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""
import os
import sys
import logging
import tempfile
import shutil
import utils

from multiprocessing import Process, Queue
from PyQt4 import QtCore

from process import run_job

# Debug settings
ATLS_LOG_LEVEL = logging.DEBUG
KEEP_INPUTS = False

# ATLS constants
atls_path = os.path.dirname(os.path.realpath(sys.argv[0]))
_OQ_RESOURCE_PATH = os.path.join(atls_path, 'resources', 'oq')
_HAZ_RESOURCES = {
    'job_def':   'job.ini',
    'gmpe_lt':   'gmpe_logic_tree.xml',
    'source':    'point_source_model.xml',
    'source_lt': 'source_model_logic_tree.xml'
}
_RISK_POE_RESOURCES = {
    'job_def':    'job.ini',
    'exp_model':  'exposure_model.xml',
    'vuln_model': 'struct_vul_model.xml'
}


class _OqRunner(QtCore.QObject):
    """
    Runs OQ jobs on a separate process

    Before running a new job the relevant inputs must be set on the class
    member vars. At the moment only one job can run at the time.
    The singleton OqRunner object itself lives on a secondary thread where
    it listens to messages from the OQ process and forwards them to the main
    thread via signals.

    :ivar job_input: dict with input parameters for the next job of the form
        job_input = {
            'job_def': '/path/to/job/file'
            'hazard_calculation_id': None,
            'hazard_output_id': None,
            'oq_log_file': None,
            'oq_exports': (),
            'oq_log_level': 'progress'
        }
        Only job_def is mandatory, all other parameters take the default values
        that are shown above when omitted.

    """

    job_complete = QtCore.pyqtSignal(object)

    def __init__(self):
        super(_OqRunner, self).__init__()
        # input
        self.job_input = None
        # other stuff
        self.busy = False
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(ATLS_LOG_LEVEL)

    def run(self):
        assert self.job_input is not None, 'No job input provided'
        queue = Queue()
        p = Process(target=run_job, args=(queue, self.job_input))
        p.start()
        finished = False
        while not finished:
            print('Waiting for msg on {} thread.'
                  .format(QtCore.QThread.currentThread().objectName()))
            msg = queue.get()
            if isinstance(msg, str):
                self._logger.info('OQ Process: ' + msg)
            else:
                finished = True
                self.job_input = None
                self.job_complete.emit(msg)


class _OqController(QtCore.QObject):

    def __init__(self):
        super(_OqController, self).__init__()
        # Setup the OQ listener thread and move the OQ runner object to it
        self._oq_thread = QtCore.QThread()
        self._oq_thread.setObjectName('OQ')
        self._oq_runner = _OqRunner()
        self._oq_runner.moveToThread(self._oq_thread)
        self._oq_thread.started.connect(self._oq_runner.run)
        self._oq_runner.job_complete.connect(self._job_complete)

        # internal vars
        self.busy = False
        self.callback = None
        self.job_dir = None
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(ATLS_LOG_LEVEL)

    def run_hazard(self, source_params, callback):
        """
        Run a OQ hazard job

        OQ hazard jobs run asynchronously and invoke *callback* on completion.
        The result of the run is simply a job id that can be used to fetch the
        actual results from the OQ database.

        :param source_params: dictionary Gutenberg-Richter a,b values and
            weights per IS forecast model, i.e.
            source_params = {'ETAS': [a, b, w], ...}.
            Note that the sum of all weights must be 1.0
        :param callback: callback method which will be invoked when the job
            finishes. The callback takes two arguments: job_id (int) and
            success (bool).

        """
        if self.busy:
            raise RuntimeError('OQ jobs cannot run concurrently')
        # prepare hazard input
        self.job_dir = tempfile.mkdtemp(prefix='atls-')
        self._logger.debug('Running OQ hazard job from {}'
                           .format(self.job_dir))
        for f in _HAZ_RESOURCES.values():
            shutil.copy(os.path.join(_OQ_RESOURCE_PATH, 'psha', f),
                        self.job_dir)
        source_lt_path = os.path.join(self.job_dir,
                                      _HAZ_RESOURCES['source_lt'])
        utils.inject_src_params(source_params, source_lt_path)
        # run job
        job_input = {'job_def': os.path.join(self.job_dir,
                                             _HAZ_RESOURCES['job_def'])}
        self._oq_runner.job_input = job_input
        self.callback = callback
        self.busy = True
        self._oq_thread.start()

    def run_risk_poe(self, psha_job_id, callback):
        """
        Runs an OQ risk job that computes probabilities of exceedance for
        a preconfigured loss range based on the hazard output from a run_hazard
        calculation.

        :param psha_job_id: job id of the run_hazard calculation
        :type psha_job_id: int
        :param callback: callback method which will be invoked when the job
            finishes. The callback takes two arguments: job_id (int) and
            success (bool).

        """
        if self.busy:
            raise RuntimeError('OQ jobs cannot run concurrently')
        # prepare risk input
        self.job_dir = tempfile.mkdtemp(prefix='atls-')
        self._logger.debug('Running OQ risk PoE job from {}'
                           .format(self.job_dir))
        for f in _RISK_POE_RESOURCES.values():
            shutil.copy(os.path.join(_OQ_RESOURCE_PATH, 'risk_poe', f),
                        self.job_dir)
        # run job
        job_input = {'job_def': os.path.join(self.job_dir,
                                             _RISK_POE_RESOURCES['job_def']),
                     'hazard_calculation_id': psha_job_id}
        self._oq_runner.job_input = job_input
        self.callback = callback
        self.busy = True
        self._oq_thread.start()

    def _job_complete(self, result):
        self.busy = False
        self._logger.debug('Job #{} {}. Calling back.'
                           .format(result['job_id'],
                           'succeeded' if result['success'] else 'failed'))
        if not KEEP_INPUTS:
            shutil.rmtree(self.job_dir)
        self._oq_thread.quit()
        self._oq_thread.wait()
        self.callback(result)

controller = _OqController()
