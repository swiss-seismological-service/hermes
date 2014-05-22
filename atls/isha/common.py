# -*- encoding: utf-8 -*-
"""
Common stuff for all ISHA models such as the parent class and the data
structures that are required to interact with the model.
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from PyQt4 import QtCore
from datetime import datetime


class ModelInput(object):
    """
    Holds ISHA model inputs and parameters for the next run. Not all models may
    require all of the inputs.

    :ivar forecast_mag_range: Tuple that specifies Mmin, Mmax for the forecast
    :type forecast_mag_range: Tuple with two floats
    :ivar seismic_events: List of recorded seismic events
    :type seismic_events: List of SeismicEvent objects
    :ivar forecast_times: List of times (datetime) at which to forecast
    :type forecast_times: List of datetime objects
    :ivar t_bin: Forecast bin size in hours. The default is 6h.
    :type t_bin: float

    """
    _data_attrs = ['t_run', 'forecast_mag_range', 'seismic_events',
                   'hydraulic_events', 'forecast_times', 't_bin']

    def __init__(self, t_run):
        """
        Create input for a model run. The parameter t_run serves as an
        identifier for the run.

        """
        self.t_run = t_run
        self.forecast_mag_range = None
        self.seismic_events = None
        self.hydraulic_events = None
        self.forecast_times = None
        self.t_bin = 6

    def primitive_rep(self):
        """
        Generator that unpacks input data into simple lists of primitive types.

        We do this since we can't pass python objects to external code such as
        Matlab. Lists are yielded as tuples (list_name, list) where list_name is
        the name of the corresponding member variable. Members of members will
        be returned with a combined name, E.g. all self.seismic_event.magnitude
        will be returned as a list named *seismic_event_magnitude*. datetime
        objects translated into unix time stamps

        """
        for base_name in ModelInput._data_attrs:
            attr = getattr(self, base_name)
            try:
                # If attr is a list of DataModel objects (which all provide
                # data_attrs), we extract each data_attr into a separate list
                for attr_name in attr[0].data_attrs:
                    combined_name = base_name + '_' + attr_name
                    data = [getattr(obj, attr_name) for obj in attr]
                    yield combined_name, _primitive(data)
            except (TypeError, IndexError, AttributeError):
                # Otherwise we yield the attr as is
                yield base_name, _primitive(attr)


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
        :type run_input: ModelInput

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

    # Some helper functions

    def flow_rate_in_interval(self, t_min, t_max):
        """
        Returns the flow rate from run input that is representative for the
        interval t_min, t_max.

        The function returns the maximum flow rate in the time interval
        [t_min, t_max]. If no flow rate data is available in this interval, it
        returns the last flow rate it finds.

        If no flow rates are present at all the function returns 0

        """
        if self._run_input.hydraulic_events is None:
            return 0

        rates = [h.flow_dh for h in self._run_input.hydraulic_events
                 if t_min <= h.date_time < t_max]

        if len(rates) == 0:
            last_flow = self._run_input.hydraulic_events[-1]
            flow = last_flow.flow_dh
        else:
            flow = max(rates)

        return flow


def _primitive(attr):
        """ Converts any datetime object to unix time stamp """
        epoch = datetime(1970, 1, 1)
        if isinstance(attr, list) and len(attr) > 0 \
                and isinstance(attr[0], datetime):
            return [(dt - epoch).total_seconds() for dt in attr]
        elif isinstance(attr, datetime):
            return (attr - epoch).total_seconds()
        else:
            return attr