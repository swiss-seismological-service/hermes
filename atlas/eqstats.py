# -*- encoding: utf-8 -*-
"""
Provides a class to manage Atlas project data

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import collections
import numpy as np
from math import log, log10, sqrt, exp
from datetime import timedelta
import bisect
from PyQt4 import QtCore

GrParams = collections.namedtuple('GrParams', 'a b std_b')


def estimate_gr_params(magnitudes, mc=None):
    """
    Estimates the Gutenberg Richter parameters based on a list of magnitudes.
    The magnitudes list is expected to contain no values below mc

    :param mc: Magnitude of completeness. If not given, the smallest value in
        magnitudes is used as mc
    :param magnitudes: List of magnitudes
    :returns: Gutenberg Richter parameter estimates as named tuple

    """
    mags = np.array(magnitudes)
    if mc is None:
        mc = mags.min()
    else:
        mags = mags[mags >= mc]
    n = mags.size
    m_mean = mags.mean()
    b = 1 / (log(10) * (m_mean - mc))
    a = log10(n) + b * mc
    std_b = 2.3 * sqrt(sum((mags - m_mean)**2) / (n * (n - 1))) * b**2
    return GrParams(a, b, std_b)


class SeismicRate:
    def __init__(self, rate, p, t, dt):
        self.rate = rate
        self.p = p
        self.t = t
        self.dt = dt


class SeismicRateHistory(QtCore.QObject):
    """
    Manages a history of seismic rates and computes new rates on request.

    """

    history_changed = QtCore.pyqtSignal()

    def __init__(self):
        """
        Create a new seismic history with a default bin length of 6 hours

        """
        super(SeismicRateHistory, self).__init__()
        self.t_bin = timedelta(hours=6)
        self._rates = []
        self.times = []

    @property
    def rates(self):
        return self._rates

    @rates.setter
    def rates(self, value):
        self._rates = value
        self.times = [rate.t for rate in value]
        self.history_changed.emit()

    def lookup_rate(self, t):
        idx = self.times.index(t)
        if idx:
            return self._rates[idx]

    def clear(self):
        self._rates = []
        self.times = []
        self.history_changed.emit()

    def compute_and_add(self, m, t_m, t_rates):
        """
        Compute seismic rates for the events given in *t_m* (time) and *m*
        (magnitudes). The rates are computed for *t_bin* length bins (given
        at initialization time) backward from the times given in *t_rates*.
        Computed rates are automatically added to the history and returned to
        the caller.

        :param m: list of magnitudes (floats)
        :param t_m: list of time (datetime) at which m occurred

        """
        m_np = np.array(m)

        computed = []
        for t_end in t_rates:
            t_start = t_end - self.t_bin
            t_bin_h = self.t_bin.total_seconds() / 3600.0

            idx_t_start = bisect.bisect_left(t_m, t_start)
            # ...including the upper boundary for the last bin
            if t_end == t_rates[-1]:
                idx_t_end = bisect.bisect_right(t_m, t_end)
            else:
                idx_t_end = bisect.bisect_left(t_m, t_end)

            # Compute rates for all magnitude bins within this time bin
            m_in_bin = np.array(m_np[idx_t_start:idx_t_end])
            rate = len(m_in_bin) / t_bin_h
            p = 1 - exp(rate)
            computed.append(SeismicRate(rate, p, t_end, t_bin_h))

        self._rates += computed
        # Store the time and magnitude lower bin boundaries for reference
        self.times.append(t_rates)
        self.history_changed.emit()
        return computed

