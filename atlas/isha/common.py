# -*- encoding: utf-8 -*-
"""
Common stuff for all ISHA models such as the parent class and the data
structures that are required to interact with the model.
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from PyQt4 import QtCore

class RunInput:
    """
    Holds ISHA model inputs and parameters for the next run. Not all models may
    require all of the inputs.

    :ivar forecast_mag_range: Tuple that specifies Mmin, Mmax for the forecast
    :type forecast_mag_range: Tuple with two floats
    :ivar seismic_events: List of recorded seismic events
    :type seismic_events: List of SeismicEvent objects
    :ivar forecast_times: List of times (datetime) at which to forecast
    :type forecast_times: List of datetime objects
    :ivar t_bin: Forecast bin size in hours. The default is 6h)
    :type t_bin: float

    """

    def __init__(self, t_run):
        """
        Create input for a model run. The parameter t_run serves as an
        identifier for the run.

        """
        self.t_run = t_run
        self.forecast_mag_range = None
        self.seismic_events = None
        self.forecast_times = None
        self.t_bin = 6


class RunResults:
    """
    Models store their run results into this simple container structure

    """
    def __init__(self, t_run, model):
        self.t_run = t_run
        self.model = model
        self.t_results = None
        self.rates = None
        self.probabilities = None


class Model(QtCore.QObject):
    """
    Abstract model class that provides the common functionality for ISHA
    forecast models

    .. pyqt4:signal:finished: emitted when the model has finished its run.
    Carries the run results as payload.

    :ivar run_results: results of the last run
    :ivar title: display title of the model

    """

    finished = QtCore.pyqtSignal(object)

    def __init__(self):
        """ Initializes the model """
        super(Model, self).__init__()
        self._run_input = None
        self.run_results = None
        self.title = 'Model'

    @property
    def run_input(self):
        return self._run_input

    def prepare_run(self, run_input):
        """
        Prepares the model for the next run. The data that is required for the
        run is supplied in *run_data*

        :param run_input: data for the next run
        :type run_data: RunInput

        """
        self._run_input = run_input

    def run(self):
        """
        Invoked when the model should perform a run. The default implementation
        just checks if the run data has been provided.

        You should Override this function in a subclass. Make sure you emit the
        :pyqt4:signal:finished signal at the end of your implementation.

        """
        assert(self._run_input is not None)