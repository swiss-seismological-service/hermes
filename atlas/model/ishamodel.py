# -*- encoding: utf-8 -*-
"""
Provides a controller to run ISHA models
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from PyQt4 import QtCore
from datetime import datetime, timedelta

class IshaModelParameters:
    """ Holds ISHA model inputs and parameters """
    def __init__(self):
        self.seismic_events = None
        self.hydraulic_events = None
        self.forecast_start = datetime.now()
        self.forecast_end = self.forecast_start + timedelta(hours=6)


class IshaModel(QtCore.QObject):
    """
    Abstract model class that provides the common functionality for ISHA
    forecast models

    """
    finished = QtCore.pyqtSignal()

    def run(self):
        """ Runs the model. Override this function in a subclass. """
        pass


class IshaModelController(QtCore.QObject):
    """
    The controller handles communication between a specific ISHA model and the
    forecast framework. It launches models in detached threads and communicates
    status updates back to the framework.

    """

    def __init__(self, isha_model):
        """
        Takes the ISHA model provided as a parameter and moves it to a
        separate thread for concurrent execution. The model is expected to
        have a run() method and to emit a *finished* signal when it's done.

        :param isha_model: ISHA model that the controller should manage
        :type isha_model: IshaModel

        """
        super(IshaModelController, self).__init__()
        self.model = isha_model
        self._qthread = QtCore.QThread()
        self.model.moveToThread(self._qthread)
        self._qthread.started.connect(self.model.run)
        self.model.finished.connect(self._on_model_finished)

    def start_forecast(self, model_parameters):
        """
        Starts a new forecast with the information given in forecast_info

        :param model_parameters: model inputs and parameters for this forecast
        :type model_parameters: IshaModelParameters

        """
        self._qthread.start()

    def _on_model_finished(self):
        """ The model is done so we can quit the thread """
        self._qthread.quit()