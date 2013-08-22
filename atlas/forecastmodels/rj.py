# -*- encoding: utf-8 -*-
"""
Reasenberg-Jones aftershock forecast model
    
"""

from collections import namedtuple
import numpy as np
from math import log


Forecast = namedtuple('Forecast', ['rate', 'prob'])
""" Forecast return type

The tuple returned by forecast(...) contains the following fields
'rate': the forecasted rate
'prob': ...

"""


class RJModel(object):
    """Reasenberg & Jones (1989, 1990, 1994) forecast model

    :ivar a: RJ parameter a (not Gutenberg-Richter)
    :ivar b: Gutenberg-Richter b value
    :ivar p: Sequence specific empirical parameter for the Omori-Utsu (1961) law
    :ivar c: Sequence specific empirical parameter for the Omori-Utsu (1961) law
    :ivar t_bin: Time bin for the forecast, default 0.25d = 6h
    :ivar m_max: Maximum magnitude, default 3.5
    :ivar m_c: Magnitude of completeness, default 0.9

    """


    def __init__(self, a, b, p, c):
        """Initializes the model parameters"""
        self.a = a
        self.b = b
        self.p = p
        self.c = c
        self.t_bin = 0.25
        self.m_max = 3.5
        self.m_c = 0.9

    def forecast(self, events, times):
        """Forecast aftershocks at times *times*

        Forecast and return the number of seismic events expected between times
        *times* and *times + t_bin* using the events passed in events.

        The forecast model predicts the rate lambda of events with magnitude M
        at time t after a main shock of magnitude Mm as

        .. math:: \lambda(t, M) = 10^(a'+b(Mm-M)) / (t + c)^p

        where a', b, c and p are empirical constants and M > Mc (magnitude of
        completeness). Integrated over the entire magnitude range and over the
        length of the forecast time bin, we arrive at the number of events
        with Mc < M < Mmax which is what this function returns.

        :param events: list of main shock events used for the forecast
        :type events: list of events
        :param time: list of times for which to forecast the seismic rate
        :type time: datetime

        :rtype: Forecast

        """
        # extract main shock event magnitudes and (relative) times of occurrence
        # into numpy arrays
        m = np.array([e.magnitude for e in events])

        rates = []
        for t in times:
            t1 = np.array([t - e.date_time for e in events])
            t2 = t1 + self.t_bin

            # compute the integral of lambda(t, M) over the magnitude range and
            # time bin length
            rate = ((t1+self.c)**(1-self.p) - (t2+self.c)**(1-self.p)) / \
                   (1-self.p)*self.b*log(10) * \
                   ( (10 ** (self.a+self.b(m-self.m_max))) -
                     (10 ** (self.a+self.b(m-self.m_c))) )

            rates.append(rate)