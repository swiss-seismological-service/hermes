# -*- encoding: utf-8 -*-
"""
Provides Atls specific control functions for ISHA models. The load_models()
function is the central place where models are loaded to be used in ATLS. I.e.
this is also the place where you add new models to the system.

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import logging

from PyQt4 import QtCore

from ismodels.common import Model
from ismodels.rj import Rj
from ismodels.etas import Etas
from ismodels.shapiro import Shapiro

active_models = []
_detached_runners = []


def load_models(model_ids):
    """
    Load ISHA models. Register new models here.

    To add a new model, simply instantiate it, give it a display title
    and add it to the list of models.

    """
    global _detached_runners
    load_all = True if 'all' in model_ids else False

    # Reasenberg Jones
    if load_all or 'rj' in model_ids:
        rj_model = Rj(a=-1.6, b=1.58, p=1.2, c=0.05)
        rj_model.title = 'Reasenberg-Jones'
        active_models.append(rj_model)

    # ETAS
    if load_all or 'etas' in model_ids:
        etas_model = Etas(alpha=0.8, k=8.66, p=1.2, c=0.01, mu=12.7, cf=1.98)
        etas_model.title = 'ETAS'
        active_models.append(etas_model)

    # Shapiro
    if load_all or 'shapiro' in model_ids:
        shapiro_model = Shapiro()
        shapiro_model.title = 'Shapiro (Spatial)'
        active_models.append(shapiro_model)

    # This moves the models to their own thread. Do not access model
    # members directly after this line
    _detached_runners = [DetachedRunner(m) for m in active_models]

    titles = [m.title for m in active_models]
    logging.getLogger(__name__).info('Loaded models: ' + ', '.join(titles))


def run_active_models(model_input):
    for runner in _detached_runners:
        runner.run_model(model_input)


class DetachedRunner(QtCore.QObject):
    """
    The ISModelRunner manages the actual IS models which live on a separate
    thread each. It communicates data back and forth in a thread safe manner
    and replicates some of the models basic properties (name etc.) to make
    it available on the main thread.

    """

    # This is for debugging since breakpoints don't work with threads
    DEBUG = False

    def __init__(self, model):
        """
        Takes the ISHA model provided as a parameter and moves it to a
        separate thread for concurrent execution. The model is expected to
        have a run() method and to emit a *finished* signal when it's done.

        :param model: ISHA model that the controller should manage
        :type model: Model

        """
        super(DetachedRunner, self).__init__()
        # the reference to the actual model is private since it must not be
        # accessed from the main thread directly.
        self._logger = logging.getLogger(__name__)
        self.model = model
        if not DetachedRunner.DEBUG:
            self._qthread = QtCore.QThread()
            self._qthread.setObjectName(model.title)
            self.model.moveToThread(self._qthread)
            self._qthread.started.connect(self.model.run)
        else:
            self._logger.warning('DEBUG mode, {} will run in main thread'
                .format(model.title))

        self.model.finished.connect(self._on_model_finished)
        self._logger = logging.getLogger(__name__)

    def __del__(self):
        # Make sure the thread ends before we destroy it
        if not DetachedRunner.DEBUG:
            self._qthread.wait()

    def run_model(self, run_data):
        """
        Starts a new forecast with the information given in run_data

        :param run_data: model inputs and parameters for this forecast
        :type run_data: ModelInput

        """
        self._logger.debug('preparing %s', self.model.title)
        self.model.prepare_run(run_data)
        self._logger.debug('starting worker thread for {}'
                           .format(self.model.title))
        if not DetachedRunner.DEBUG:
            self._qthread.start()
        else:
            self.model.run()

    def _on_model_finished(self):
        """ The model is done so we can quit the thread """
        if DetachedRunner.DEBUG:
            return
        self._qthread.quit()
        self._qthread.wait()
