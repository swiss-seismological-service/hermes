# ATLAS
# Copyright (C) 2013 Lukas Heiniger

import collections
from numpy import array, sum
from math import log, log10, sqrt

GrParams = collections.namedtuple('GrParams', 'a b std_b')


def estimate_gr_params(magnitudes, mc=None):
    """
    Estimates the Gutenberg Richter parameters based on a list of magnitudes.
    The magnitudes list is expected to contain no values below
    :param mc: Magnitude of completeness. If not given, the smallest value in
        magnitudes is used as mc
    :param magnitudes: List of magnitudes
    :returns Gutenberg Richter parameter estimates as named tuple

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