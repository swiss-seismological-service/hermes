# -*- encoding: utf-8 -*-
"""
Tests for the evaluation of seismicity forecasts
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from numpy import log
from scipy.misc import factorial


def log_likelihood(forecast, observation):
    """
    Compute the log likelihood of an observed rate given a forecast

    The forecast value is interpreted as expected value of a poisson
    distribution. The function expects scalars or numpy arrays as input. In the
    latter case it computes the LL for each element.

    :param forecast: forecast rate
    :param observations: observed rate
    :return: log likelihood for each element of the input

    """
    LL = -forecast + observation * log(forecast) - log(factorial(observation))
    return LL

