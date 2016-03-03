# -*- encoding: utf-8 -*-
"""
This module defines the common interface for all ISHA models, that is the model
base class and classes used for data input and output.

* Class :class:`Model` is the abstract super class for all ISHA models and
  defines the minimal methods that each model must implement.
* Class :class:`ModelInput`. An instance of this class is passed to the model
  when the framework invokes :meth:`Model.prepare_run`. The ModelInput contains
  the input data for each model run.
* Class :class:`ModelOutput`. An object of this class must be returned by the
  models ``Model._do_run`` method. It contains information about the
  outcome of the model run. This doesn't have to be a result, it can also be
  an error message if the run was not successful. See the class definition for
  details.
* Class :class:`ModelResult` contains the result of the model run if it was
  successful, i.e. the actual computed forecast rates and probabilities.

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from PyQt4 import QtCore
from datetime import datetime
from datetime import timedelta
import logging

from data.hydraulicevent import HydraulicEvent
from data.seismicevent import SeismicEvent
from data.geometry import Point
from data.injectionwell import InjectionWell


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

    def __init__(self, t_run, project=None, bin_size=6.0, mc=None,
                 mag_range=None):
        """
        Create input for a model run.

        :param t_run: time of the run (serves as an identifier)
        :type t_run: datetime
        :param project: ramsis project containing the data
        :type project: Project
        :param bin_size: size of the forecast bin [hours]
        :type bin_size: float
        :param mc: magnitude of completeness
        :type mc: float
        :param mag_range: tuple of two specifying the forecast magnitude range
        :type mag_range: tuple

        """
        self.t_run = t_run
        self.forecast_mag_range = mag_range
        self.mc = mc
        # TODO: list is legacy (no more support for multiple fc times)
        self.forecast_times = [t_run]
        self.injection_well = None
        self.expected_flow = None
        self.t_bin = bin_size
        if project:
            self.hydraulic_events = \
                project.hydraulic_history.events_before(t_run)
            self.seismic_events = \
                project.seismic_history.events_before(t_run, mc=mc)
            self.injection_well = project.injection_well
        else:
            self.seismic_events = None
            self.hydraulic_events = None

    def estimate_expected_flow(self, t_run, project, bin_size=6.0):
        """
        Compute expected flow from (future) data.

        The expected flow during the forecast period is computed as the average
        from the flow samples for that period. If no data is available, zero
        flow is assumed.

        :param project: ramsis project containing the data
        :param t_run: time of the run
        :param bin_size: size of the forecast bin(s) [hours]

        """
        t_end = t_run + timedelta(hours=bin_size)
        events = project.hydraulic_history.events_between(t_run, t_end)
        if len(events) == 0:
            self.expected_flow = 0
        else:
            # TODO: we might have to estimate this from flow_dh. Also, the
            # current implementation does not handle irregularly spaced samples
            # correctly.
            self.expected_flow = sum([e.flow_xt for e in events]) / len(events)

    def primitive_rep(self):
        """
        Generator that unpacks input data into simple lists of primitive types.

        We do this since we can't pass python objects to external code such as
        Matlab. Lists are yielded as tuples (list_name, list) where list_name
        is the name of the corresponding member variable. Members of members
        will be returned with a combined name, E.g. all
        self.seismic_event.magnitude will be returned as a list named
        *seismic_event_magnitude*. datetime objects translated into unix time
        stamps.

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

    def serialize(self, datetime_format):
        data = {}
        for attr in self._data_attrs:
            data[attr] = getattr(self, attr)

        data["t_run"] = data["t_run"].strftime(datetime_format)
        data["mc"] = str(data["mc"])
        data["forecast_times"] = [
            data["forecast_times"][0].strftime(datetime_format)
        ]
        data["seismic_events"] = [{
            "date_time": e.date_time.strftime(datetime_format),
            "magnitude": e.magnitude,
            "location": (e.x, e.y, e.z)
        } for e in data["seismic_events"]]
        data["hydraulic_events"] = [{
            "date_time": e.date_time.strftime(datetime_format),
            "flow_dh": e.flow_dh,
            "flow_xt": e.flow_xt,
            "pr_dh": e.pr_dh,
            "pr_xt": e.pr_xt
        } for e in data["hydraulic_events"]]
        data["injection_well"] = (
            data["injection_well"].well_tip_x,
            data["injection_well"].well_tip_y,
            data["injection_well"].well_tip_z
        )

        return data

    def deserialize(self, data, datetime_format):
        data["t_run"] = datetime.strptime(data["t_run"], datetime_format)
        data["mc"] = float(data["mc"])
        data["forecast_times"] = [datetime.strptime(data["forecast_times"][0],
                                                    datetime_format)]
        data["seismic_events"] = [SeismicEvent(
            datetime.strptime(e["date_time"], datetime_format),
            e["magnitude"],
            Point(*e["location"])
        ) for e in data["seismic_events"]]
        data["hydraulic_events"] = [HydraulicEvent(
            datetime.strptime(e["date_time"], datetime_format),
            e["flow_dh"],
            e["flow_xt"],
            e["pr_dh"],
            e["pr_xt"]
        ) for e in data["hydraulic_events"]]
        data["injection_well"] = InjectionWell(*data["injection_well"])

        for attr in self._data_attrs:
            setattr(self, attr, data[attr])


class ModelResult(object):
    """ Result container for a single forecast """
    def __init__(self, rate, b_val, prob):
        """
        :param rate: forecast rate
        :param b_val: gutenberg-richter b value
        :param prob: forecast probability of one or more events occurring

        """
        # TODO: add region (voxel boundaries) (#15)
        self.rate = rate
        self.b_val = b_val
        self.prob = prob


class ModelOutput:
    """
    Models store their output into this container structure.

    This is just a dumb container. The models can fill whichever variables are
    applicable to them. That is, a model can have volumetric results,
    cumulative results, both or none of them (if it failed).

    :ivar vol_results: a list containing the forecast results
        for each voxel in a spatial model.
    :type vol_results: list[ModelResult]
    :ivar cum_result: cumulative result for the entire forecast region
    :type cum_result: ModelResult
    :ivar model: a reference to the model that created the forecast
    :ivar t_run: time of the forecast
    :type t_run: datetime
    :ivar dt: forecast period duration [hours]
    :type dt: timedelta
    :ivar failed: true if the model did not produce any results
    :ivar failure_reason: a reason given by the model for not producing any
        results.

    """
    def __init__(self, t_run, dt, model):
        self.failed = False
        self.failure_reason = 'Unknown'
        self.t_run = t_run
        self.dt = dt
        self.model = model
        self.cum_result = None
        self.vol_results = None


class Model(QtCore.QObject):
    """
    Abstract model class that provides the common functionality for ISHA
    forecast models

    .. pyqt4:signal:finished: emitted when the model has finished its run
       successfully and has new run results. Carries the model as payload.

    :ivar ModelOutput output: output of the last run
    :ivar title: display title of the model

    """

    # If set to true, any model errors will raise an exception
    RAISE_ON_ERRORS = True

    finished = QtCore.pyqtSignal(object)
    """ Signal emitted when the model run has completed """

    def __init__(self):
        """ Initializes the model """
        super(Model, self).__init__()
        self._model_input = None
        self.output = None
        self.title = 'Model'
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def model_input(self):
        return self._model_input

    def prepare_run(self, model_input):
        """
        Prepares the model for the next run. The data that is required for the
        run is supplied in *model_input*

        :param model_input: data for the next run
        :type model_input: ModelInput

        """
        self._model_input = model_input

    def run(self):
        """
        Wraps _do_run which is implemented by concrete subclasses

        The wrapper takes care of state changes and emitting signals as
        required.

        """
        self._logger.info('<{}> {} model run initiated'
                          .format(self.thread().objectName(), self.title))
        self.output = self._do_run()
        self._logger.info('<{}> {} model run completed'
                          .format(self.thread().objectName(), self.title))
        self.finished.emit(self)

    def _do_run(self):
        """
        Does the actual work. Must be implemented by children.

        """
        raise NotImplementedError('Children must provide _do_run')

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
        if self._model_input.hydraulic_events is None:
            return 0
        rates = [h.flow_dh for h in self._model_input.hydraulic_events
                 if t_min <= h.date_time < t_max]
        if len(rates) == 0:
            last_flow = self._model_input.hydraulic_events[-1]
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
