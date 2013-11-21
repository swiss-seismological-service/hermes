# -*- encoding: utf-8 -*-
"""
Common stuff for all ISHA models such as the parent class and the data
structures that are required to interact with the model.
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from PyQt4 import QtCore
from datetime import datetime, timedelta


class RunData:
    """ Holds ISHA model inputs and parameters """
    def __init__(self):
        self.seismic_events = None
        self.hydraulic_events = None
        self.forecast_start = datetime.now()
        self.forecast_end = self.forecast_start + timedelta(hours=6)


class Model(QtCore.QObject):
    """
    Abstract model class that provides the common functionality for ISHA
    forecast models

    """
    finished = QtCore.pyqtSignal()

    def __init__(self):
        """ Initializes the model """
        super(Model, self).__init__()
        self._run_data = None

    def prepare_run(self, run_data):
        """
        Prepares the model for the next run. The data that is required for the
        run is supplied in *run_data*

        :param run_data: data for the next run
        :type run_data: RunData

        """
        self._run_data = run_data

    def run(self):
        """ Runs the model. Override this function in a subclass. """
        pass