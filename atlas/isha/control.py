# -*- encoding: utf-8 -*-
"""
Provides a controller to run ISHA models
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from common import Model
from PyQt4 import QtCore


class ModelController(QtCore.QObject):
    """
    The controller handles communication between a specific ISHA model and the
    forecast framework. It launches models in detached threads and communicates
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
        super(ModelController, self).__init__()
        self.model = model
        self._qthread = QtCore.QThread()
        self.model.moveToThread(self._qthread)
        self._qthread.started.connect(self.model.run)
        self.model.finished.connect(self._on_model_finished)

    def __del__(self):
        # Make sure the thread ends before we destroy it
        self._qthread.wait()

    def start_forecast(self, run_data):
        """
        Starts a new forecast with the information given in run_data

        :param run_data: model inputs and parameters for this forecast
        :type run_data: RunData

        """
        self.model.prepare_run(run_data)
        self._qthread.start()

    def _on_model_finished(self):
        """ The model is done so we can quit the thread """
        self._qthread.quit()