# -*- encoding: utf-8 -*-
"""
Common stuff for all ISHA models such as the parent class and the data
structures that are required to interact with the model.
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from PyQt4 import QtCore
from datetime import datetime
from datetime import timedelta
import logging

class ModelInput(object):
    """
    Holds ISHA model inputs and parameters for the next run. Not all models may
    require all of the inputs.

    :ivar forecast_mag_range: Tuple that specifies Mmin, Mmax for the forecast
    :type forecast_mag_range: Tuple with two floats
    :ivar seismic_events: List of recorded seismic events
    :type seismic_events: List of SeismicEvent objects
    :ivar hydraulic_events: List of recorded hydraulic events
    :type hydraulic_events: List of HydraulicEvent objects
    :ivar forecast_times: List of times (datetime) at which to forecast
    :type forecast_times: List of datetime objects
    :ivar t_bin: Forecast bin size in hours. The default is 6h.
    :type t_bin: float
    :ivar expected_flow: Expected flow rate during forecast [l/min]
    :type expected_flow: float
    :ivar mc: Magnitude of completeness
    :type mc: float

    """
    _data_attrs = ['t_run', 'forecast_mag_range', 'seismic_events',
                   'hydraulic_events', 'forecast_times', 't_bin',
                   'injection_well', 'expected_flow', 'mc']

    def __init__(self, t_run, project=None, bin_size=6.0, num_bins=1,
                 mc=None, mag_range=None):
        """
        Create input for a model run.

        :param t_run: time of the run (serves as an identifier)
        :type t_run: datetime
        :param project: atls project containing the data
        :type project: AtlsProject
        :param bin_size: size of the forecast bin [hours]
        :type bin_size: float
        :param num_bins: number of forecasts to make (usually 1)
        :type num_bins: int
        :param mc: magnitude of completeness
        :type mc: float
        :param mag_range: tuple of two specifying the forecast magnitude range
        :type num_bins: tuple


        """
        dt = timedelta(hours=bin_size)
        self.t_run = t_run
        # FIXME: the range should not be hardcoded
        self.forecast_mag_range = mag_range
        self.mc = mc
        self.seismic_events = None
        self.hydraulic_events = None
        self.forecast_times = [t_run + i * dt for i in range(num_bins)]
        self.injection_well = None
        self.expected_flow = None
        self.t_bin = bin_size
        if project:
            self.hydraulic_events = \
                project.hydraulic_history.events_before(t_run)
            self.seismic_events = \
                project.seismic_history.events_before(t_run)
            self.injection_well = project.injection_well

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
            # make everything into a sequence type first
            if attr is None:
                attr = []
            elif not hasattr(attr, '__iter__'):
                attr = [attr]
            if len(attr) > 0 and hasattr(attr[0], 'data_attrs'):
                for attr_name in attr[0].data_attrs:
                    combined_name = base_name + '_' + attr_name
                    data = [getattr(obj, attr_name) for obj in attr]
                    yield combined_name, _primitive(data)
            else:
                yield base_name, _primitive(attr)


class RunResults:
    """
    Models store their run results into this simple container structure.

    """
    def __init__(self, t_run, model):
        self.has_results = True
        self.no_result_reason = 'Unknown'
        self.t_run = t_run
        self.model = model
        self.t_results = None
        self.rates = None
        self.probabilities = None


class ModelState:
    IDLE = 0
    RUNNING = 1


class Model(QtCore.QObject):
    """
    Abstract model class that provides the common functionality for ISHA
    forecast models

    .. pyqt4:signal:finished: emitted when the model has finished its run
    successfully and has new run results. Carries the run results as payload.
    .. pyqt4:signal:state_changed: emitted when the model changes its state
    from running to idle or vice ver

    :ivar run_results: results of the last run
    :ivar title: display title of the model

    """

    # If set to true, any model errors will raise an exception
    RAISE_ON_ERRORS = True

    finished = QtCore.pyqtSignal(object)
    state_changed = QtCore.pyqtSignal(object)

    def __init__(self):
        """ Initializes the model """
        super(Model, self).__init__()
        self._run_input = None
        self.run_results = None
        self.title = 'Model'
        self._state = ModelState.IDLE
        self._logger = logging.getLogger(self.__class__.__name__)

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
        Invoked when the model should perform a run. This method takes care of
        state changes and emitting signals as required. The actual model code
        is run from _do_run.

        """
        self._logger.info(self.title + ' model run initiated')
        self.state = ModelState.RUNNING
        results = self._do_run()
        if results:
            self.run_results = results
        else:
            # Store an empty result if the model code doesn't return anything
            self.run_results = RunResults(self.run_input.t_run, self)
        self.finished.emit(self.run_results)
        self._logger.info(self.title + ' model run completed')
        self.state = ModelState.IDLE

    def _do_run(self):
        """
        Contains the actual model code.

        You should Override this function in a subclass and return the results
        for the run if successful. The default implementation just checks if the
        run data has been provided.

        """
        assert(self._run_input is not None)
        return None

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state
        self.state_changed.emit(state)

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
        if len(attr) > 0 and isinstance(attr[0], datetime):
            return [(dt - epoch).total_seconds() for dt in attr]
        else:
            return attr