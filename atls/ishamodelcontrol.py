# -*- encoding: utf-8 -*-
"""
Provides Atls specific control functions for ISHA models. The load_models()
function is the central place where models are loaded to be used in ATLS. I.e.
this is also the place where you add new models to the system.

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from PyQt4 import QtCore

from isha.common import Model
from isha.rj import Rj
from isha.etas import Etas
from isha.shapiro import Shapiro
import logging

active_models = []

def load_models(model_ids):
    """
    Load ISHA models. Register new models here.

    To add a new model, simply instantiate it, give it a display title
    and add it to the list of models.

    """
    load_all = 'all' in model_ids

    logging.getLogger(__name__).info('Active models: ' + ', '.join(model_ids))

    # Reasenberg Jones
    if load_all or 'rj' in model_ids:
        rj_model = Rj(a=-1.6, b=1.0, p=1.2, c=0.05)
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


class DetachedRunner(QtCore.QObject):
    """
    The controller launches models in detached threads and communicates
    status updates back to the framework.

    """

    def __init__(self, model):
        """
        Takes the ISHA model provided as a parameter and moves it to a
        separate thread for concurrent execution. The model is expected to
        have a run() method and to emit a *finished* signal when it's done.

        :param model: ISHA model that the controller should manage
        :type model: Model

        """
        super(DetachedRunner, self).__init__()
        self.model = model
        self._qthread = QtCore.QThread()
        self.model.moveToThread(self._qthread)
        self._qthread.started.connect(self.model.run)
        self.model.finished.connect(self._on_model_finished)
        self._logger = logging.getLogger(__name__)

    def __del__(self):
        # Make sure the thread ends before we destroy it
        self._qthread.wait()

    def run_model(self, run_data):
        """
        Starts a new forecast with the information given in run_data

        :param run_data: model inputs and parameters for this forecast
        :type run_data: ModelInput

        """
        self._logger.debug('preparing %s', self.model.title)
        self.model.prepare_run(run_data)
        self._logger.debug('detaching %s to worker thread', self.model.title)
        self._qthread.start()

    def _on_model_finished(self):
        """ The model is done so we can quit the thread """
        self._qthread.quit()
