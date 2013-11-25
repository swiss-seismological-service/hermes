# -*- encoding: utf-8 -*-
"""
Reasenberg-Jones aftershock forecast model

Reasenberg P. and L. Jones (1989), "Earthquake hazard after a main shock in
California", Science 243, 1173-1176
    
"""

from common import Model
import numpy as np
from math import log


class Rj(Model):
    """
    Reasenberg & Jones aftershock forecast model. The model predicts aftershocks
    using an empirical relation to the main shock.

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

    def run(self):
        """
        Forecast aftershocks at the times given in run data

        Forecasts and the number of seismic events expected between times t
        given in the run data (see prepare_forecast) and *t + bin_size*.

        The forecast model predicts the rate lambda of events with magnitude M
        at time t after a main shock of magnitude Mm as

        .. math:: \lambda(t, M) = 10^(a'+b(Mm-M)) / (t + c)^p

        where a', b, c and p are empirical constants and M > Mc (magnitude of
        completeness). Integrated over the entire magnitude range and over the
        length of the forecast time bin, we arrive at the number of events
        with Mc < M < Mmax which is what this function returns.

        """

        # copy everything into local variables for better readability
        a = self.a
        b = self.b
        c = self.c
        p = self.p
        events = self._run_data.seismic_events
        forecast_times = self._run_data.forecast_times
        t_bin = self._run_data.t_bin
        m_min, m_max = self._run_data.magnitude_range

        # extract main shock event magnitudes and (relative) times of occurrence
        # into numpy arrays
        m = np.array([e.magnitude for e in events])

        forecast_rates = []
        for t in forecast_times:
            # Convert event times to relative hours
            t1 = np.array([(t - e.date_time).total_seconds() / 3600.0
                           for e in events])
            t2 = t1 + t_bin

            # Compute the integral of lambda(t, M) over the magnitude range and
            # time bin length
            rate = ((t1+c)**(1-p) - (t2+c)**(1-p)) / ((1-p)*b*log(10)) * \
                   ((10 ** (a+b*(m-m_max))) - (10 ** (a+b*(m-m_min))))

            forecast_rates = rate.tolist()

        self.run_results = forecast_rates
        self.finished.emit()