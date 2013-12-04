# -*- encoding: utf-8 -*-
"""
Reasenberg-Jones aftershock forecast model

Reasenberg P. and L. Jones (1989, 1994), "Earthquake hazard after a main shock
in California", Science 243, 1173-1176
    
"""

from common import Model
import numpy as np
import logging
from math import log, exp


class Rj(Model):
    """
    Reasenberg & Jones aftershock forecast model. The model predicts aftershocks
    using an empirical relation to the main shock.

    The result of the model run is a list of tuples containing for each forecast
    time interval the rate of events in the magnitude range *forecast_mag_range*
    and the probability of one or more events occurring as (rate, probability)

    :ivar a: RJ parameter a (not Gutenberg-Richter)
    :ivar b: Gutenberg-Richter b value
    :ivar p: Sequence specific empirical parameter for the Omori-Utsu (1961) law
    :ivar c: Sequence specific empirical parameter for the Omori-Utsu (1961) law
    :ivar m_max: Maximum magnitude, default 3.5
    :ivar m_c: Magnitude of completeness, default 0.9

    """

    def __init__(self, a, b, p, c):
        """Initializes the model parameters"""
        super(Rj, self).__init__()
        self.a = a
        self.b = b
        self.p = p
        self.c = c
        self._logger = logging.getLogger(__name__)

    def run(self):
        """
        Forecast aftershocks at the times given in run data

        Forecasts and the number of seismic events expected between times t
        given in the run data (see prepare_forecast) and *t + bin_size*.

        The forecast model predicts the rate lambda of events with magnitude M
        or larger at time t after a main shock of magnitude Mm as

        .. math:: \lambda(t, M) = 10^(a'+b(Mm-M)) / (t + c)^p

        where a', b, c and p are empirical constants and M > Mc (magnitude of
        completeness). Thus, by integrating over t, the number of events in the
        magnitude range [M1, M2] and time interval [T1, T2] after the main shock
        can be computed as

        .. math:: \frac{(T_2+c)^{1-p}-(T_1+c)^{1-p}}{1-p} * \
                  [10^{a+b(M_m-M_1)}-10^{a+b(M_m-M_2)}]

        with is what this model returns.

        Note that any events occurring after the start of each forecast window
        are ignored for the respective forecast.

        """
        self._logger.info('Model run initiated')

        # copy everything into local variables for better readability
        a = self.a
        b = self.b
        c = self.c
        p = self.p
        events = self._run_data.seismic_events
        forecast_times = self._run_data.forecast_times
        t_bin = self._run_data.t_bin
        m_min, m_max = self._run_data.forecast_mag_range
        num_t = len(forecast_times)

        # extract all main shock event magnitudes into a numpy array
        m_all = np.array([e.magnitude for e in events])

        # Compute rate for each forecast time interval
        forecast_rates = np.zeros(num_t)
        for t, i in zip(forecast_times, range(0, num_t)):
            # Convert event times to relative hours
            t_all = np.array([(t - e.date_time).total_seconds() / 3600.0
                             for e in events])

            # Filter out any events after the start of the forecast interval
            t1 = t_all[t_all >= 0]
            t2 = t1 + t_bin
            m = m_all[t_all >= 0]

            # Compute the integral of lambda(t, M) over the time bin interval
            # and subtract the upper magnitude limit from the lower limit to
            # get the appropriate range
            rate = ((t2+c)**(1-p) - (t1+c)**(1-p)) / (1-p) * \
                   ((10 ** (a+b*(m-m_min))) - (10 ** (a+b*(m-m_max))))

            # The implementation below is found in various SED codes. It's
            # based on a mistake in the original RJ '89 paper (see correction in
            # RJ '94). Do not use. It's just here for reference.
            # rate = ((t1+c)**(1-p) - (t2+c)**(1-p)) / ((1-p)*b*_logger(10)) * \
            #        ((10 ** (a+b*(m-m_max))) - (10 ** (a+b*(m-m_min))))

            # Sum up the contributions from each event
            forecast_rates[i] = rate.sum()

        # Compute the resulting probabilities of one or more events occurring
        probabilities = 1 - np.exp(-forecast_rates)

        # Finish up
        self.run_results = zip(forecast_rates.tolist(), probabilities.tolist())
        self._logger.info('Model run completed')
        self.finished.emit(self)
