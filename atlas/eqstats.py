# ATLAS
# Copyright (C) 2013 Lukas Heiniger

import collections
import numpy as np
from math import log, log10, sqrt
import bisect

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
    mags = array(magnitudes)
    if mc is None:
        mc = mags.min()
    else:
        mags = mags[mags >= mc]
    n = mags.size
    m_mean = mags.mean()
    b = 1 / (log(10) * (m_mean - mc))
    a = log10(n) + b * mc
    std_b = 2.3 * sqrt(sum((mags - m_mean)**2) / (n * (n - 1))) * b**2
    return GrParams(a,b,std_b)


def compute_seismic_rates(magnitudes, t, t_range, m_range):
    """
    Computes the seismic rates from an event catalog.

    The rates are computed from the events given in *events* within
    the time range *t_range* and magnitude range *m_range*. Both t_range and
    m_range are lists containing the boundaries for the respective bins. Bins
    include the lower boundary but exclude the upper boundary, except for the
    last bin, where the upper boundary is included too. I.e. the m_range
    sequence 2,3,4,5 will result in the following bins

    [2,3[  [3,4[  [4,5]

    The function returns a len(t_range)*len(m_range) array with seismic rates in
    units of [1/h].

    :param magnitudes: list of events magnitudes
    :type magnitudes: list of floats
    :param t: times of occurrence for the events in *events*
    :type t: list of datetime objects
    :param t_range: time bin boundaries to compute rates for
    :type t_range: list of datetime objects
    :param m_range: magnitude bin boundaries to compute rates for
    :type m_range: list of floats

    :returns: 2D array of size len(t_range)*len(m_range) containing the rates
        in [1/h]

    """
    m_bins = np.array(m_range)

    rates = []
    for t_start, t_end in zip(t_range[:-1], t_range[1:]):
        dt = (t_end - t_start).total_seconds() / 3600
        idx_start = bisect.bisect_left(t, t_start)
        # include the upper boundary for the last bin
        if t_end == t_range[-1]:
            idx_end = bisect.bisect_right(t, t_end)
        else:
            idx_end = bisect.bisect_left(t, t_end)
        m = np.array(magnitudes[idx_start:idx_end])
        bin_rates = np.histogram(m, bins=m_bins)[0] / dt
        rates.append(bin_rates.tolist())

    return rates
